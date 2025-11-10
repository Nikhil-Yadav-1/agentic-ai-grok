import json
import os
from typing import Optional, Dict, Any

import requests

try:
    # LangChain decorator (common)
    from langchain.tools import tool
except Exception:
    # Fallback: provide a no-op decorator so file is importable even if langchain not installed
    def tool(fn=None, **_kwargs):
        if fn is None:
            def _wrap(f): return f
            return _wrap
        return fn


def _norm_base(url: str) -> str:
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "http://" + url
    return url.rstrip("/")


@tool
def mcp_http_tool(
    action: str,
    base_url: str,
    name: Optional[str] = None,
    arguments: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30,
) -> str:
    """
    Generic MCP tool to connect with any mcp servers like Google sheets and Google Drive

    action: "list_tools" | "call_tool"
    base_url: host with optional port, e.g. "http://localhost:8129" or "localhost:8129"
    name: tool name when action == "call_tool"
    arguments: dict passed as JSON body when calling a tool
    headers: optional HTTP headers (Authorization, etc.)
    timeout: seconds for HTTP calls

    Returns a JSON string (success) or a JSON error object.
    """
    print("\n\n\ninside mcp_http_tool: ")
    print("action", action)
    print("base_url", base_url)
    print("name", name)
    print("arguments", arguments)
    print("headers", headers)
    print("timeout", timeout)

    base = _norm_base(base_url)
    headers = (headers.copy() if headers else {})
    headers.setdefault("Content-Type", "application/json")

    # 1) Check /tools (REST wrapper mode)
    try:
        r = requests.get(f"{base}/tools", headers=headers, timeout=5)
    except Exception as e:
        return json.dumps({"error": "connect_failed", "message": str(e)})

    if r.status_code != 200:
        return json.dumps({"error": "tools_endpoint_failed", "status": r.status_code, "text": r.text})

    arguments = {"spreadsheet_id":"13H1kyV_7MH-xxx","sheet":"Sheet1","range":"A1:C100"}    
    
    if action == "list_tools":
        try:
            return json.dumps(r.json())
        except Exception:
            return json.dumps({"error": "parse_failed", "text": r.text})
        
    if action == "call_tool":
        if not name:
            return json.dumps({"error": "name_required"})
        try:
            resp = requests.post(
                f"{base}/tools/{name}",
                headers=headers,
                json=arguments or {},
                timeout=timeout,
            )
        except Exception as e:
            return json.dumps({"error": "request_failed", "message": str(e)})
        try:
            return json.dumps(resp.json())
        except Exception:
            # return raw text if not JSON
            return json.dumps({"status_code": resp.status_code, "text": resp.text})

    return json.dumps({"error": "unsupported_action", "action": action})

if __name__ == "__main__":
    # my server lives at localhost:8129
    # Access the original function using _original attribute added by @tool decorator
    original_func = getattr(mcp_http_tool, '_original', mcp_http_tool)
    print(original_func("list_tools", "http://localhost:8129"))
    print(original_func("call_tool", "http://localhost:8129", name="get_sheet_data",
                    arguments={"spreadsheet_id":"13H1kyV_7MH-xxx","sheet":"Sheet1","range":"A1:C100"}))