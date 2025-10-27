from typing import List, Dict
from typing_extensions import TypedDict
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
import inspect
import json
from backend.config import LLM_API_KEY, CONTEXT_WINDOW_SIZE, MODEL_NAME
from backend.load_tools import load_all_tools


class ChatState(TypedDict):
    chat_history: List[Dict[str, str]]
    user_input: str
    response: str


def _mask_key(k: str) -> str:
    if not k:
        return "<no-key>"
    if len(k) > 12:
        return k[:8] + "*" * (len(k) - 12) + k[-4:]
    if len(k) > 2:
        return k[0] + "*" * (len(k) - 2) + k[-1]
    return "*" * len(k)


def _tool_name(t):
    try:
        if hasattr(t, "name"):
            return getattr(t, "name")
        if inspect.isfunction(t) or inspect.ismethod(t):
            return t.__name__
        if hasattr(t, "__class__"):
            return t.__class__.__name__
    except Exception:
        pass
    return str(t)


class ChatbotAgent:
    _instance = None
    _is_initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ChatbotAgent, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not ChatbotAgent._is_initialized:
            print("agent: initializing ChatbotAgent")
            print(f"agent: model={MODEL_NAME} api_key={_mask_key(LLM_API_KEY)}")
            
            self.llm = ChatGroq(api_key=LLM_API_KEY, model=MODEL_NAME)
            self.tools = load_all_tools()
            names = [_tool_name(t) for t in self.tools]
            print(f"agent: loaded {len(self.tools)} tools: {names}")

            # Simplified: use tool binding approach
            print("agent: using tool binding executor")
            
            try:
                self.llm_with_tools = self.llm.bind_tools(self.tools)
                print("agent: ✅ tools bound to LLM")
            except Exception as e:
                print(f"agent: ⚠️ couldn't bind tools: {e}, using basic fallback")
                self.llm_with_tools = self.llm
            
            class _ToolCallingExecutor:
                def __init__(self, llm, llm_with_tools, tools):
                    self.llm = llm
                    self.llm_with_tools = llm_with_tools
                    self.tools = tools
                    self.tool_map = {tool.name: tool for tool in tools}

                def invoke(self, args):
                    user_input = args.get("input", "")
                    print(f"agent: fallback executor for: {user_input[:120]}")

                    tool_descriptions = "\n".join([
                        f"- {tool.name}: {tool.description}" 
                        for tool in self.tools
                    ])

                    system_msg = f"""You are a helpful AI assistant with access to tools.

Available tools:
{tool_descriptions}

CRITICAL JSON FORMATTING RULES:
1. When calling MCP tools, ALWAYS use proper JSON with DOUBLE QUOTES
2. Example: {{"owner":"username"}} NOT {{'owner':'username'}}
3. Tool arguments MUST be valid JSON strings

For GitHub MCP interactions:
- Use: call_tool list_repositories with arguments {{"owner":"username"}}
- NOT: call_tool list_repositories with arguments {{'owner':'username'}}

Always format your tool calls with proper JSON syntax."""

                    messages = [
                        SystemMessage(content=system_msg),
                        HumanMessage(content=user_input)
                    ]

                    try:
                        # Invoke the LLM with bound tools
                        response = self.llm_with_tools.invoke(messages)

                        # Check for tool calls
                        if hasattr(response, 'tool_calls') and response.tool_calls:
                            tool_call = response.tool_calls[0]
                            tool_name = tool_call.get('name')
                            tool_input = tool_call.get('args', {})

                            if tool_name in self.tool_map:
                                print(f"agent: executing tool '{tool_name}'")
                                try:
                                    # Build proper query string
                                    if tool_name == "universal_mcp_tool":
                                        # Extract query from tool_input
                                        if isinstance(tool_input, dict):
                                            query = tool_input.get('query', '')
                                            
                                            # If query is still a dict, convert to proper format
                                            if isinstance(query, dict):
                                                # Build proper MCP query
                                                action = query.get('action', 'call_tool')
                                                tool_to_call = query.get('tool', '')
                                                arguments = query.get('arguments', {})
                                                url = query.get('url', 'https://api.githubcopilot.com/mcp/')
                                                
                                                # Format with proper JSON (double quotes)
                                                args_json = json.dumps(arguments, ensure_ascii=False)
                                                query = f"{action} {tool_to_call} with arguments {args_json} on {url}"
                                            
                                            tool_input_str = query
                                        else:
                                            tool_input_str = str(tool_input)
                                    else:
                                        # For other tools, convert to JSON string
                                        tool_input_str = json.dumps(tool_input, ensure_ascii=False)
                                    
                                    print(f"agent: calling {tool_name} with: {tool_input_str[:200]}")
                                    
                                    # Run tool
                                    tool_result = self.tool_map[tool_name].run(tool_input_str)
                                    print(f"agent: tool returned: {str(tool_result)[:200]}")

                                    return {"output": f"**Results:**\n\n{tool_result}"}

                                except Exception as e:
                                    print(f"agent: tool execution error: {e}")
                                    import traceback
                                    traceback.print_exc()
                                    return {
                                        "output": f"❌ Error executing {tool_name}: {e}\n\nTip: Make sure to use proper JSON format with double quotes."
                                    }
                        
                        # No tool calls, just return LLM content
                        content = getattr(response, 'content', str(response))
                        print(f"agent: direct response: {content[:200]}")
                        return {"output": content}

                    except Exception as e:
                        print(f"agent: error in fallback executor: {e}")
                        import traceback
                        traceback.print_exc()
                        return {"output": f"❌ I encountered an error: {e}"}

            self.agent_executor = _ToolCallingExecutor(
                self.llm, 
                self.llm_with_tools, 
                self.tools
            )

            self.setup_graph()
            ChatbotAgent._is_initialized = True

    def generate_response(self, state: ChatState) -> ChatState:
        user_input = state["user_input"]
        chat_history = state["chat_history"]

        try:
            print(f"agent: invoking executor for input={user_input[:120]}")
            result = self.agent_executor.invoke({"input": user_input})
            response = result.get("output", "")
            print(f"agent: executor returned response len={len(str(response))}")
        except Exception as e:
            response = f"❌ Error during execution: {str(e)}"
            print(f"agent: execution error: {e}")
            import traceback
            traceback.print_exc()

        state["response"] = response
        return state

    def setup_graph(self):
        workflow = StateGraph(ChatState)
        workflow.add_node("generate_response", self.generate_response)
        workflow.set_entry_point("generate_response")
        workflow.add_edge("generate_response", END)
        self.graph = workflow.compile()

    def process_message(self, user_input: str, chat_history: List[Dict[str, str]]) -> str:
        if len(chat_history) > CONTEXT_WINDOW_SIZE * 2:
            chat_history = chat_history[-CONTEXT_WINDOW_SIZE * 2:]
        state = {
            "chat_history": chat_history,
            "user_input": user_input,
            "response": ""
        }
        result = self.graph.invoke(state)
        return result["response"]