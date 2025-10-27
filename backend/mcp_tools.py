"""
Universal MCP Tool - Using persistent requests.Session for proper state management
"""

import requests
import json
import os
import re
from typing import Dict, Any, Tuple, Optional
from langchain.tools import tool

# Import config
from backend.config import MCP_SERVER_HOST, GITHUB_TOKEN, MCP_AUTH_TOKEN

# Cache for initialized servers with persistent sessions
_initialized_servers = {}


def _parse_json_flexible(json_str: str) -> dict:
    """Parse JSON with flexible handling of single/double quotes"""
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        fixed = json_str.replace("'", '"')
        try:
            return json.loads(fixed)
        except json.JSONDecodeError as e:
            raise ValueError(f"Could not parse JSON: {e}\nOriginal: {json_str}")


def _get_or_create_session(url: str, headers: Dict[str, str], timeout: int = 30) -> Tuple[bool, Any]:
    """
    Get or create a persistent requests.Session for the MCP server.
    This maintains cookies, connection pooling, and state across requests.
    """
    cache_key = f"{url}_{str(sorted(headers.items()))}"
    
    if cache_key in _initialized_servers:
        session_info = _initialized_servers[cache_key]
        print(f"mcp: Using cached session for {url}")
        return True, session_info
    
    try:
        url = url.rstrip('",;!? ')
        
        # Create a persistent session
        session = requests.Session()
        session.headers.update(headers)
        
        print(f"mcp: Creating new session for {url}")
        
        # Send initialize request
        init_body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {"listChanged": True},
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "langchain-agent",
                    "version": "1.0.0"
                }
            }
        }
        
        print(f"mcp: Sending initialize")
        resp = session.post(url, json=init_body, timeout=timeout)
        
        if resp.status_code != 200:
            session.close()
            return False, f"HTTP {resp.status_code}: {resp.text[:500]}"
        
        try:
            init_response = resp.json()
            print(f"mcp: Initialize response: {json.dumps(init_response, indent=2)[:500]}")
        except Exception as e:
            session.close()
            return False, f"Invalid JSON response: {e}"
        
        if "error" in init_response:
            session.close()
            return False, f"Initialize error: {init_response['error']}"
        
        result = init_response.get("result", {})
        
        # Try to get session ID from various places
        session_id = (
            result.get("sessionId") or 
            result.get("session_id") or
            resp.headers.get("X-Session-Id") or
            resp.headers.get("Session-Id")
        )
        
        # Check if session has cookies (another way servers track state)
        has_cookies = len(session.cookies) > 0
        print(f"mcp: Session cookies: {dict(session.cookies) if has_cookies else 'None'}")
        
        # Send initialized notification (optional, ignore errors)
        try:
            initialized_body = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {}
            }
            notify_resp = session.post(url, json=initialized_body, timeout=5)
            print(f"mcp: Initialized notification sent (status: {notify_resp.status_code})")
        except Exception as e:
            print(f"mcp: Initialized notification skipped: {e}")
        
        # Store session info
        session_info = {
            "initialized": True,
            "session": session,  # Store the actual session object!
            "sessionId": session_id,
            "serverInfo": result.get("serverInfo", {}),
            "capabilities": result.get("capabilities", {}),
            "url": url,
            "request_counter": 2
        }
        _initialized_servers[cache_key] = session_info
        
        print(f"mcp: ✅ Session initialized (sessionId: {session_id}, cookies: {has_cookies})")
        return True, session_info
        
    except requests.exceptions.Timeout:
        return False, "Connection timeout"
    except requests.exceptions.ConnectionError:
        return False, "Connection failed"
    except Exception as e:
        import traceback
        print(f"mcp: Exception:\n{traceback.format_exc()}")
        return False, f"Initialization failed: {str(e)}"


@tool()
def universal_mcp_tool(query: str) -> str:
    """
    Universal MCP tool for dynamic interaction with ANY MCP-compliant server.
    Uses persistent sessions to maintain state (cookies, session IDs, etc.).
    
    Query Format Examples:
    - "list_tools from https://api.githubcopilot.com/mcp/"
    - "call_tool list_repositories with arguments {\"owner\":\"username\"} on https://api.githubcopilot.com/mcp/"
    """
    
    print(f"mcp: Processing query: {query[:200]}")
    
    query_lower = query.lower()
    
    # Extract action
    action = None
    if "list_tools" in query_lower or "list tools" in query_lower:
        action = "list_tools"
    elif "call_tool" in query_lower or "call tool" in query_lower:
        action = "call_tool"
    else:
        return "❌ Specify: list_tools or call_tool"
    
    # Extract URL
    url = MCP_SERVER_HOST
    url_pattern = r'(?:from|on|at|server)\s+(https?://[^\s]+)'
    url_match = re.search(url_pattern, query)
    if url_match:
        url = url_match.group(1).rstrip('.,;!?"')
    
    print(f"mcp: Action={action}, URL={url}")
    
    # Setup headers
    headers = {"Content-Type": "application/json"}
    
    if GITHUB_TOKEN and ("github" in url.lower() or "copilot" in url.lower()):
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
        print("mcp: Added GitHub token authentication")
    elif MCP_AUTH_TOKEN:
        headers["Authorization"] = MCP_AUTH_TOKEN
    
    timeout = 30
    
    # Get or create persistent session
    success, session_info = _get_or_create_session(url, headers, timeout)
    if not success:
        return f"""❌ Failed to connect to MCP server at {url}

Error: {session_info}

Troubleshooting:
- Verify URL is correct
- Check GITHUB_TOKEN in .env (for GitHub MCP)
- Ensure token has repo, read:user permissions
"""
    
    # Use the persistent session
    session = session_info.get("session")
    url = session_info.get("url")
    
    # Get request ID
    request_id = session_info.get("request_counter", 2)
    session_info["request_counter"] = request_id + 1
    
    # Build request body
    if action == "list_tools":
        body = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/list",
            "params": {}
        }
        
    elif action == "call_tool":
        # Extract tool name
        tool_name = None
        name_pattern = r'(?:call_tool|call tool)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        match = re.search(name_pattern, query_lower)
        if match:
            tool_name = match.group(1)
        
        if not tool_name:
            return "❌ Tool name not found"
        
        # Extract arguments
        arguments = {}
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        json_match = re.search(json_pattern, query)
        
        if json_match:
            json_str = json_match.group(0)
            try:
                arguments = _parse_json_flexible(json_str)
                print(f"mcp: Parsed arguments: {arguments}")
            except ValueError as e:
                return f"❌ {e}"
        
        body = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        print(f"mcp: Calling '{tool_name}' with: {json.dumps(arguments)}")
    
    # Make request using persistent session
    try:
        print(f"mcp: Sending {body['method']} (id={request_id})")
        
        # Use the persistent session - this maintains cookies and state!
        resp = session.post(url, json=body, timeout=timeout)
        
        print(f"mcp: Response status: {resp.status_code}")
        
        # Handle errors
        if resp.status_code == 401:
            return "❌ Authentication failed - check GITHUB_TOKEN"
        
        if resp.status_code == 403:
            return "❌ Access forbidden - token lacks permissions"
        
        if resp.status_code != 200:
            try:
                error_detail = resp.json()
                error_msg = error_detail.get("error", {}).get("message", resp.text[:300])
                
                if "session" in error_msg.lower():
                    # Clear cache and suggest retry
                    print("mcp: Session error, clearing cache")
                    clear_mcp_cache()
                    return f"❌ {error_msg}\n\nSession cleared. Try again."
                
                return f"❌ Error: {error_msg}"
            except:
                return f"❌ HTTP {resp.status_code}: {resp.text[:300]}"
        
        # Parse response
        try:
            resp_json = resp.json()
            print(f"mcp: Response: {json.dumps(resp_json, indent=2)[:500]}")
        except Exception as e:
            return f"❌ Invalid JSON: {resp.text[:300]}"
        
        # Check for JSON-RPC error
        if "error" in resp_json:
            error = resp_json["error"]
            error_msg = error.get("message", str(error))
            error_code = error.get("code", "unknown")
            return f"❌ MCP Error [{error_code}]: {error_msg}"
        
        # Format response
        result = resp_json.get("result", {})
        
        if action == "list_tools":
            tools = result.get("tools", [])
            if not tools:
                return "📋 No tools available"
            
            output = f"🔧 **{len(tools)} Available Tools:**\n\n"
            for i, tool in enumerate(tools[:20], 1):  # Limit to first 20
                output += f"{i}. **{tool.get('name')}**\n"
                desc = tool.get('description', 'No description')
                output += f"   {desc[:100]}\n"
                
                schema = tool.get('inputSchema', {})
                if schema.get('properties'):
                    params = list(schema['properties'].keys())
                    output += f"   📥 {', '.join(params[:5])}\n"
                output += "\n"
            
            if len(tools) > 20:
                output += f"... and {len(tools) - 20} more tools\n"
            
            return output
        
        elif action == "call_tool":
            content = result.get("content", [])
            if not content:
                return "✅ Success (no output)"
            
            output = "✅ **Result:**\n\n"
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        text = item.get("text", "")
                        # Limit very long outputs
                        if len(text) > 2000:
                            output += text[:2000] + "\n\n... (truncated)"
                        else:
                            output += text
                    elif item.get("type") == "image":
                        output += f"🖼️ [Image: {item.get('mimeType')}]"
                    else:
                        output += str(item)[:500]
                else:
                    output += str(item)[:500]
                output += "\n"
            
            return output
        
        return f"```json\n{json.dumps(resp_json, indent=2)[:1000]}\n```"
        
    except requests.exceptions.Timeout:
        return f"❌ Timeout after {timeout}s"
    except Exception as e:
        import traceback
        print(f"mcp: Exception:\n{traceback.format_exc()}")
        return f"❌ Failed: {str(e)}"


def clear_mcp_cache():
    """Clear cached sessions and close connections"""
    global _initialized_servers
    
    # Close all session objects
    for session_info in _initialized_servers.values():
        session = session_info.get("session")
        if session:
            try:
                session.close()
            except:
                pass
    
    _initialized_servers = {}
    print("mcp: All sessions closed and cache cleared")