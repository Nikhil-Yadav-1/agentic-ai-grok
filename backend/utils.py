import json

def load_mcp_servers_from_json(file_path: str):
    """Reads an MCP servers JSON file and formats their details into descriptive strings."""
    with open(file_path, 'r') as f:
        data = json.load(f)

    servers = data.get("mcp_servers", [])
    formatted_list = []

    for srv in servers:
        text = (
            f"Name of the server: {srv.get('name', 'N/A')}, "
            f"base_url: {srv.get('base_url', 'N/A')}, "
            f"description: {srv.get('description', 'N/A')}, "
        )
        formatted_list.append(text)

    return formatted_list


def build_system_prompt(json_path: str = "/home/auriga/Desktop/agentic-ai-grok/backend/mcp_servers.json") -> str:
    """Builds the system prompt text including MCP server info and usage instructions."""
    mcp_list = load_mcp_servers_from_json(json_path)
    mcp_info = "\n".join(f"- {entry}" for entry in mcp_list)

    system_prompt = f"""
        You are an intelligent assistant who helps users achieve their goals efficiently and clearly.
        You have two main capabilities:
        1. You can use **LangGraph tools** already wired into your environment.
        2. You can interact with **remote Model Context Protocol (MCP) servers** via a universal tool called `mcp_http_tool`.

        ### How to use normal LangGraph tools
        - You can directly call these when you detect that a task matches their functionality.
        - Always provide arguments as structured JSON (dict-like).
        - Return only summarized, user-friendly explanations — not raw data.

        ### How to use MCP servers
        dealing with mcp servers is a process where you will have to call the mcp_http_tool.
        You have access to the tool `mcp_http_tool(action, base_url, name, arguments, headers, timeout)` which lets you explore and invoke any MCP-compatible HTTP server.
        
        **Call a specific tool** from that list:
        mcp_http_tool(
        action="call_tool",
        base_url="http://localhost:8129",
        name="tool_name",
        arguments={{"param": "value"}}
        )

        Important Guidelines:
        - Always use the tool `mcp_http_tool` when you detect that a task matches its functionality.
        - Decide logically whether an MCP or LangGraph tool best fits the user’s query.
        - Use the server descriptions below to choose relevant ones.
        - Never expose raw JSON or API internals to users; summarize clearly instead.
        - Be patient — remote MCP calls may take time.

        some tools from the google sheets mcp server:
            'create_spreadsheet',
            'get_sheet_data',
            'update_cells',

        Let's begin.
        """
    return system_prompt.strip()


if __name__ == "__main__":
    # Path to your mcp_servers.json file
    prompt = build_system_prompt()
    print(prompt)
