from typing import List, Dict
from typing_extensions import TypedDict
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
import inspect
import json
from backend.config import LLM_API_KEY, CONTEXT_WINDOW_SIZE, MODEL_NAME
from backend.load_tools import load_all_tools
from backend.utils import build_system_prompt

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
            
            # Load all tools (now includes both LangChain and MCP tools)
            self.tools = load_all_tools(include_mcp=True)
            names = [_tool_name(t) for t in self.tools]
            
            # Separate MCP and native tools for logging
            mcp_tools = [t for t in self.tools if t.name.startswith('mcp_')]
            native_tools = [t for t in self.tools if not t.name.startswith('mcp_')]
            
            print(f"agent: loaded {len(self.tools)} total tools:")
            print(f"  - Native tools ({len(native_tools)}): {[_tool_name(t) for t in native_tools]}")
            print(f"  - MCP tools ({len(mcp_tools)}): {[_tool_name(t) for t in mcp_tools]}")

            # Bind tools to LLM
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

                # def invoke(self, args):
                #     user_input = args.get("input", "")
                #     print(f"agent: processing request: {user_input[:120]}")

                #     system_msg = build_system_prompt()

                #     messages = [
                #         SystemMessage(content=system_msg),
                #         HumanMessage(content=user_input)
                #     ]

                #     try:
                #         # Invoke the LLM with bound tools
                #         response = self.llm_with_tools.invoke(messages)

                #         # Check for tool calls
                #         if hasattr(response, 'tool_calls') and response.tool_calls:
                #             tool_call = response.tool_calls[0]
                #             tool_name = tool_call.get('name')
                #             tool_input = tool_call.get('args', {})

                #             if tool_name in self.tool_map:
                #                 print(f"agent: executing tool '{tool_name}'")
                #                 print(f"agent: tool input: {json.dumps(tool_input, indent=2)}")
                                
                #                 try:
                #                     tool = self.tool_map[tool_name]
                                    
                #                     # Execute the tool using its invoke method
                #                     # All tools (native and MCP) now have consistent interfaces
                #                     tool_result = tool.invoke(tool_input)
                                    
                #                     print(f"agent: ✅ tool '{tool_name}' executed successfully")
                #                     print(f"agent: result preview: {str(tool_result)[:200]}")
                                    
                #                     return {"output": f"**Results:**\n\n{tool_result}"}

                #                 except Exception as e:
                #                     print(f"agent: ❌ tool execution error: {e}")
                #                     import traceback
                #                     traceback.print_exc()
                #                     return {
                #                         "output": f"❌ Error executing {tool_name}: {e}"
                #                     }
                #             else:
                #                 print(f"agent: ⚠️ tool '{tool_name}' not found in tool map")
                #                 available = list(self.tool_map.keys())
                #                 return {
                #                     "output": f"❌ Tool '{tool_name}' not available. Available tools: {', '.join(available[:10])}"
                #                 }
                        
                #         # No tool calls, just return LLM content
                #         content = getattr(response, 'content', str(response))
                #         print(f"agent: direct response: {content[:200]}")
                #         return {"output": content}

                #     except Exception as e:
                #         print(f"agent: error in executor: {e}")
                #         import traceback
                #         traceback.print_exc()
                #         return {"output": f"❌ I encountered an error: {e}"}


                def invoke(self, args):
                    user_input = args.get("input", "")
                    chat_history = args.get("chat_history", [])  # ✅ Get history
                    print(f"agent: processing request: {user_input[:120]}")

                    system_msg = build_system_prompt()

                    # ✅ Build messages from history
                    messages = [SystemMessage(content=system_msg)]
                    
                    # Add chat history
                    for msg in chat_history:
                        if msg.get("role") == "user":
                            messages.append(HumanMessage(content=msg.get("content", "")))
                        elif msg.get("role") == "assistant":
                            messages.append(AIMessage(content=msg.get("content", "")))
                    
                    # Add current user input
                    messages.append(HumanMessage(content=user_input))
                    
                    print(f"agent: total messages in context: {len(messages)} (system + {len(chat_history)} history + 1 current)")

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
                                print(f"agent: tool input: {json.dumps(tool_input, indent=2)}")
                                
                                try:
                                    tool = self.tool_map[tool_name]
                                    
                                    # Execute the tool using its invoke method
                                    # All tools (native and MCP) now have consistent interfaces
                                    tool_result = tool.invoke(tool_input)
                                    
                                    print(f"agent: ✅ tool '{tool_name}' executed successfully")
                                    print(f"agent: result preview: {str(tool_result)[:200]}")
                                    
                                    return {"output": f"**Results:**\n\n{tool_result}"}

                                except Exception as e:
                                    print(f"agent: ❌ tool execution error: {e}")
                                    import traceback
                                    traceback.print_exc()
                                    return {
                                        "output": f"❌ Error executing {tool_name}: {e}"
                                    }
                            else:
                                print(f"agent: ⚠️ tool '{tool_name}' not found in tool map")
                                available = list(self.tool_map.keys())
                                return {
                                    "output": f"❌ Tool '{tool_name}' not available. Available tools: {', '.join(available[:10])}"
                                }
                        
                        # No tool calls, just return LLM content
                        content = getattr(response, 'content', str(response))
                        print(f"agent: direct response: {content[:200]}")
                        return {"output": content}

                    except Exception as e:
                        print(f"agent: error in executor: {e}")
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

    # def generate_response(self, state: ChatState) -> ChatState:
    #     user_input = state["user_input"]
    #     chat_history = state["chat_history"]

    #     try:
    #         print(f"agent: invoking executor for input={user_input[:120]}")
    #         result = self.agent_executor.invoke({"input": user_input})
    #         response = result.get("output", "")
    #         print(f"agent: executor returned response len={len(str(response))}")
    #     except Exception as e:
    #         response = f"❌ Error during execution: {str(e)}"
    #         print(f"agent: execution error: {e}")
    #         import traceback
    #         traceback.print_exc()

    #     state["response"] = response
    #     return state

    def generate_response(self, state: ChatState) -> ChatState:
        user_input = state["user_input"]
        chat_history = state["chat_history"]  # ✅ Get history

        try:
            result = self.agent_executor.invoke({
                "input": user_input,
                "chat_history": chat_history  # ✅ Pass it along
            })
            response = result.get("output", "")
        except Exception as e:
            response = f"❌ Error during execution: {str(e)}"
        
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