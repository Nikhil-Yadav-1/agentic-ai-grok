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
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
TOOL_MODULES = os.getenv("TOOL_MODULES", "backend.tools").split(",")
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
SERPAPI_API_KEY = SERPAPI_KEY  # for langchain_community compatibility
MCP_SERVER_HOST = os.getenv("MCP_SERVER_HOST", "https://api.githubcopilot.com/mcp/")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "your_github_token_here_if_using_github_mcp")
MCP_AUTH_TOKEN = os.getenv("MCP_AUTH_TOKEN", "your_mcp_auth_token_here_if_required")