# backend/agent.py
from typing import List, Dict
from typing_extensions import TypedDict
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
import inspect

# Updated import for newer LangChain versions
try:
    # Try the new import path first (LangChain >= 0.1.0)
    from langchain.agents import create_react_agent, AgentExecutor
    create_react_agent_available = True
    print("agent: using langchain.agents import path")
except ImportError:
    try:
        # Try the old import path
        from langchain.agents.react.agent import create_react_agent, AgentExecutor
        create_react_agent_available = True
        print("agent: using langchain.agents.react.agent import path")
    except ImportError as e:
        create_react_agent = None
        AgentExecutor = None
        create_react_agent_available = False
        _LANGCHAIN_AGENT_IMPORT_ERROR = e
        print(f"agent: ReAct agent not available: {e}")

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

            if create_react_agent_available:
                print("agent: creating ReAct agent with tools")
                
                # Create a proper prompt for ReAct agent
                from langchain import hub
                try:
                    # Try to pull the default ReAct prompt
                    prompt = hub.pull("hwchase17/react")
                except Exception as e:
                    print(f"agent: couldn't pull prompt from hub: {e}, using custom prompt")
                    # Create a simple custom prompt if hub pull fails
                    from langchain.prompts import PromptTemplate
                    template = """Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}"""
                    
                    prompt = PromptTemplate(
                        template=template,
                        input_variables=["input", "agent_scratchpad"],
                        partial_variables={
                            "tools": "\n".join([f"{tool.name}: {tool.description}" for tool in self.tools]),
                            "tool_names": ", ".join([tool.name for tool in self.tools])
                        }
                    )
                
                self.react_agent = create_react_agent(
                    llm=self.llm,
                    tools=self.tools,
                    prompt=prompt
                )
                self.agent_executor = AgentExecutor(
                    agent=self.react_agent, 
                    tools=self.tools, 
                    verbose=True,
                    handle_parsing_errors=True,
                    max_iterations=5
                )
            else:
                print("agent: WARNING - ReAct agent not available, using direct tool-calling fallback")
                # Enhanced fallback that actually uses tools
                class _ToolCallingExecutor:
                    def __init__(self, llm, tools):
                        self.llm = llm
                        self.tools = tools
                        self.tool_map = {tool.name: tool for tool in tools}
                        
                    def invoke(self, args):
                        user_input = args.get("input", "")
                        print(f"agent: fallback tool-calling executor for: {user_input[:120]}")
                        
                        # Create a prompt that encourages tool use
                        tool_descriptions = "\n".join([
                            f"- {tool.name}: {tool.description}" 
                            for tool in self.tools
                        ])
                        
                        system_msg = f"""You are a helpful assistant with access to these tools:

{tool_descriptions}

To use a tool, respond EXACTLY in this format:
TOOL: tool_name
INPUT: tool input here

Otherwise, respond normally to the user."""
                        
                        messages = [
                            SystemMessage(content=system_msg),
                            HumanMessage(content=user_input)
                        ]
                        
                        try:
                            response = self.llm.invoke(messages)
                            content = response.content if hasattr(response, 'content') else str(response)
                            print(f"agent: LLM response: {content[:200]}")
                            
                            # Check if LLM wants to use a tool
                            if "TOOL:" in content and "INPUT:" in content:
                                lines = content.split('\n')
                                tool_name = None
                                tool_input = None
                                
                                for i, line in enumerate(lines):
                                    if line.strip().startswith("TOOL:"):
                                        tool_name = line.split("TOOL:")[1].strip()
                                    elif line.strip().startswith("INPUT:"):
                                        tool_input = line.split("INPUT:")[1].strip()
                                        # Get remaining lines as input too
                                        if i + 1 < len(lines):
                                            tool_input += " " + " ".join(lines[i+1:])
                                        break
                                
                                if tool_name and tool_input and tool_name in self.tool_map:
                                    print(f"agent: executing tool {tool_name} with input: {tool_input[:100]}")
                                    try:
                                        tool_result = self.tool_map[tool_name].run(tool_input)
                                        return {"output": str(tool_result)}
                                    except Exception as e:
                                        return {"output": f"Tool execution failed: {e}"}
                            
                            return {"output": content}
                            
                        except Exception as e:
                            print(f"agent: error in fallback executor: {e}")
                            return {"output": f"❌ Error: {e}"}

                self.agent_executor = _ToolCallingExecutor(self.llm, self.tools)

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