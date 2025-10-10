import os
import sys
# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agent import ChatbotAgent

def test_agent():
    """Simple test to verify that the agent works"""
    print("Initializing chatbot agent...")
    agent = ChatbotAgent()
    
    # Test with a simple message
    user_input = "Hello, how are you?"
    chat_history = []
    
    print(f"User: {user_input}")
    response = agent.process_message(user_input, chat_history)
    print(f"Agent: {response}")
    
    # Test with a follow-up message
    chat_history = [
        {"role": "user", "content": user_input},
        {"role": "assistant", "content": response}
    ]
    
    user_input = "What can you help me with?"
    print(f"\nUser: {user_input}")
    response = agent.process_message(user_input, chat_history)
    print(f"Agent: {response}")
    
    print("\nTest completed successfully!")

if __name__ == "__main__":
    test_agent()
