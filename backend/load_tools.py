# backend/load_tools.py
import importlib
import inspect
import json
import requests
from typing import List, Dict, Any
from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field
from backend.config import TOOL_MODULES
from backend.utils import load_mcp_servers_from_json
import urllib.parse

# existing load_all_tools should remain; we add a wrapper helper and debug prints
def _wrap_callable_with_exec_debug(fn, name):
    # avoid double-wrapping
    if getattr(fn, "_exec_debug_wrapped", False):
        return fn
    def _wrapped(*args, **kwargs):
        try:
            print(f"tool: executing the {name}... tool")
        except Exception:
            pass
        return fn(*args, **kwargs)
    try:
        _wrapped.__name__ = getattr(fn, "__name__", name)
    except Exception:
        pass
    setattr(_wrapped, "_exec_debug_wrapped", True)
    return _wrapped

def _instrument_tools_module(module_name="backend.tools"):
    try:
        mod = importlib.import_module(module_name)
    except Exception as e:
        print(f"load_tools: could not import {module_name}: {e}")
        return
    changed = []
    for attr_name in dir(mod):
        if attr_name.startswith("_"):
            continue
        try:
            attr = getattr(mod, attr_name)
        except Exception:
            continue
        if inspect.isfunction(attr) and not getattr(attr, "_exec_debug_wrapped", False):
            wrapped = _wrap_callable_with_exec_debug(attr, attr_name)
            setattr(mod, attr_name, wrapped)
            changed.append(attr_name)
    if changed:
        print(f"load_tools: instrumented tool functions in {module_name}: {changed}")
    else:
        print(f"load_tools: no tool functions instrumented in {module_name}")

# call instrumentation early so tools are auto-wrapped before loading
_instrument_tools_module()


def fetch_mcp_tools_from_server(base_url: str, timeout: int = 10) -> List[Dict[str, Any]]:
    """Fetches the list of tools from a single MCP server."""
    try:
        # Try the REST-style endpoint first (GET /tools)
        response = requests.get(
            f"{base_url}/tools",
            headers={"Content-Type": "application/json"},
            timeout=timeout
        )
        response.raise_for_status()
        data = response.json()
        print(f"\nFetched tools from {base_url}: {data}\n")
        
        # Handle different response formats
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return data.get("tools", [])
        else:
            print(f"⚠️ Unexpected response format from {base_url}: {type(data)}")
            return []
            
    except Exception as e:
        print(f"⚠️ Failed to fetch tools from {base_url}: {e}")
        return []


def create_mcp_tool_wrapper(server_name: str, base_url: str, tool_info: Dict[str, Any]) -> BaseTool:
    """
    Creates a LangChain StructuredTool that wraps an MCP tool.
    
    Args:
        server_name: Name of the MCP server
        base_url: Base URL of the MCP server
        tool_info: Tool information from the MCP server's list_tools response
    
    Returns:
        A LangChain BaseTool that can call the MCP tool
    """
    # Normalize server name: remove spaces, convert to lowercase, replace special chars
    normalized_server = server_name.lower().replace(" ", "_").replace("-", "_")
    normalized_server = "".join(c for c in normalized_server if c.isalnum() or c == "_")
    
    tool_name = tool_info.get("name", "unknown_tool")
    tool_description = tool_info.get("description", "No description available")
    input_schema = tool_info.get("inputSchema", {})
    
    # Extract properties and required fields from the input schema
    properties = input_schema.get("properties", {})
    required_fields = input_schema.get("required", [])
    
    # Create a dynamic Pydantic model for the input
    field_definitions = {}
    for prop_name, prop_info in properties.items():
        prop_type = prop_info.get("type", "string")
        prop_desc = prop_info.get("description", "")
        is_required = prop_name in required_fields
        
        # Map JSON schema types to Python types
        type_mapping = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "object": dict,
            "array": list
        }
        python_type = type_mapping.get(prop_type, str)
        
        if is_required:
            field_definitions[prop_name] = (python_type, Field(..., description=prop_desc))
        else:
            field_definitions[prop_name] = (python_type, Field(None, description=prop_desc))
    
    # Create the input model dynamically
    InputModel = type(f"{tool_name}_Input", (BaseModel,), field_definitions)
    
    def mcp_tool_func(**kwargs) -> str:
        """Executes the MCP tool via HTTP POST."""
        print(f"tool: executing MCP tool {tool_name} on server {server_name}...")
        try:
            # Use the REST-style endpoint: POST /tools/{name}
            response = requests.post(
                f"{base_url}/tools/{tool_name}",
                json=kwargs,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            # Handle different response formats
            if isinstance(result, dict):
                # Check for content array (standard MCP format)
                content = result.get("content", [])
                if content and isinstance(content, list) and len(content) > 0:
                    if isinstance(content[0], dict):
                        return content[0].get("text", str(result))
                    return str(content[0])
                
                # Check for direct result field
                if "result" in result:
                    return str(result["result"])
                
                # Check for data field
                if "data" in result:
                    return json.dumps(result["data"], indent=2)
            
            # Return the whole result as formatted JSON
            return json.dumps(result, indent=2)
            
        except requests.exceptions.HTTPError as e:
            return f"Error calling MCP tool {tool_name}: HTTP {e.response.status_code} - {e.response.text}"
        except Exception as e:
            return f"Error calling MCP tool {tool_name}: {str(e)}"
    
    # Create the structured tool
    return StructuredTool(
        name=f"mcp_{normalized_server}_{tool_name}",
        description=f"[MCP:{server_name}] {tool_description}",
        func=mcp_tool_func,
        args_schema=InputModel if field_definitions else None
    )


def load_mcp_tools(json_path: str = "/home/auriga/Desktop/agentic-ai-grok/backend/mcp_servers.json") -> List[BaseTool]:
    """
    Loads all MCP tools from configured servers and converts them to LangChain tools.
    
    Args:
        json_path: Path to the MCP servers configuration JSON
    
    Returns:
        List of LangChain BaseTool objects
    """
    print("load_tools: discovering MCP tools...")
    mcp_tools = []
    
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        # Normalize several possible config shapes:
        # - {"mcp_servers": [...]}
        # - {"servers": [...]}
        # - [{"name":..., "base_url":...}, "http://host:port", ...]
        # - a single string "http://host:port"
        if isinstance(data, dict):
            servers = data.get("mcp_servers") or data.get("servers") or data.get("mcpServers") or []
            # If dict itself looks like a single server entry, use it
            if not servers and ("base_url" in data or "url" in data):
                servers = [data]
        elif isinstance(data, list):
            servers = data
        elif isinstance(data, str):
            servers = [data]
        else:
            servers = []
        
        for server in servers:
            # server may be a dict or a string; normalize to (server_name, base_url)
            if isinstance(server, str):
                base_url = server
                parsed = urllib.parse.urlparse(base_url)
                server_name = parsed.hostname or base_url
            elif isinstance(server, dict):
                server_name = server.get("name") or server.get("hostname") or server.get("host") or "unknown"
                base_url = server.get("base_url") or server.get("url") or server.get("baseUrl") or ""
            else:
                print(f"⚠️ Skipping invalid server entry: {server}")
                continue
            
            if not base_url:
                print(f"⚠️ Skipping MCP server {server_name}: no base_url")
                continue
            
            print(f"📡 Fetching tools from MCP server: {server_name} ({base_url})")
            tools_list = fetch_mcp_tools_from_server(base_url)
            
            if not isinstance(tools_list, list):
                print(f"⚠️ Unexpected tools list from {base_url}: {type(tools_list)}")
                continue
            
            for tool_info in tools_list:
                try:
                    tool = create_mcp_tool_wrapper(server_name, base_url, tool_info)
                    mcp_tools.append(tool)
                    print(f"  ✅ Loaded MCP tool: {tool.name}")
                except Exception as e:
                    tool_name = tool_info.get("name", "unknown") if isinstance(tool_info, dict) else str(tool_info)
                    print(f"  ⚠️ Failed to create wrapper for {tool_name}: {e}")
        
        print(f"✅ Loaded {len(mcp_tools)} MCP tools total")
        
    except FileNotFoundError:
        print(f"⚠️ MCP config file not found: {json_path}")
    except Exception as e:
        print(f"⚠️ Error loading MCP tools: {e}")
    
    return mcp_tools


def load_all_tools(include_mcp: bool = True) -> List[BaseTool]:
    """
    Loads all tools: both LangChain tools from modules and MCP tools from servers.
    
    Args:
        include_mcp: Whether to include MCP tools (default: True)
    
    Returns:
        Combined list of all available tools
    """
    print("load_tools: load_all_tools called")
    all_tools = []

    # Load LangChain tools from modules
    for module_name in TOOL_MODULES:
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError as e:
            print(f"⚠️ Could not import module '{module_name}': {e}")
            continue

        for name, obj in inspect.getmembers(module):
            # LangChain @tool decorator converts functions into BaseTool subclasses
            if isinstance(obj, BaseTool):
                all_tools.append(obj)

    print(f"✅ Loaded {len(all_tools)} LangChain tools from {TOOL_MODULES}: {[t.name for t in all_tools]}")
    
    # Load MCP tools if requested
    if include_mcp:
        mcp_tools = load_mcp_tools()
        all_tools.extend(mcp_tools)
        print(f"✅ Total tools (LangChain + MCP): {len(all_tools)}")
    
    return all_tools


if __name__ == "__main__":
    # Test tool loading
    tools = load_all_tools()
    print("\n=== All Loaded Tools ===")
    for tool in tools:
        print(f"- {tool.name}: {tool.description}")