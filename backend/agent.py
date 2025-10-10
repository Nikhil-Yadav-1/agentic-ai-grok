from typing import List, Dict, Any, Annotated
from typing_extensions import TypedDict
from langchain.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langchain.schema import SystemMessage, HumanMessage, AIMessage

from backend.config import LLM_API_KEY, CONTEXT_WINDOW_SIZE, MODEL_NAME

class ChatState(TypedDict):
    chat_history: List[Dict[str, str]]
    user_input: str
    response: str

class ChatbotAgent:
    def __init__(self):
        if LLM_API_KEY:
            masked_key = LLM_API_KEY[:8] + "*" * (len(LLM_API_KEY) - 12) + LLM_API_KEY[-4:]
            print(f"Using API key: {masked_key}")
        else:
            print("Warning: No API key provided")
            
        self.llm = ChatGroq(
            groq_api_key=LLM_API_KEY,
            temperature=0.7,
            model_name=MODEL_NAME
        )
        
        self.system_prompt = """
        You are a helpful and friendly AI assistant. Your goal is to provide accurate, 
        helpful, and engaging responses to the user's questions. Be concise but thorough.
        
        If you don't know the answer to a question, be honest about it rather than making up information.
        """
        
        self.setup_graph()
    
    def generate_response(self, state: ChatState) -> ChatState:
        messages = [SystemMessage(content=self.system_prompt)]
        for message in state["chat_history"]:
            if message["role"] == "user":
                messages.append(HumanMessage(content=message["content"]))
            else:
                messages.append(AIMessage(content=message["content"]))
        messages.append(HumanMessage(content=state["user_input"]))
        response = self.llm.invoke(messages)
        state["response"] = response.content
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
