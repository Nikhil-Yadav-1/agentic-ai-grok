import os
import sys
from dotenv import load_dotenv

# Get the absolute path to the .env file
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')

# Load environment variables from .env file with override
load_dotenv(dotenv_path, override=True)

# Print debug info
print(f"Loading environment variables from: {dotenv_path}")

# Database configuration
# Default to SQLite if no DATABASE_URL is provided
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./chatbot.db")

# LLM configuration
# This would typically be your API key for the language model service
LLM_API_KEY = os.getenv("LLM_API_KEY", "")

# Number of previous conversations to include as context
CONTEXT_WINDOW_SIZE = int(os.getenv("CONTEXT_WINDOW_SIZE", "5"))

# API configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
MODEL_NAME = os.getenv("MODEL_NAME", "llama-3.1-8b-instant")
