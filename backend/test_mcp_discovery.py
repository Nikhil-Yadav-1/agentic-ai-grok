import httpx
import json
import uuid
import asyncio
import os 
from backend.config import MCP_AUTH_TOKEN

MCP_URL = "https://api.githubcopilot.com/mcp/"
AUTH_TOKEN = MCP_AUTH_TOKEN
MCP_PROTOCOL_VERSION = "2024-11-05"


class MCPClient:
    def __init__(self, url, auth_token):
        self.url = url
        self.auth_token = auth_token
        self.session_id = str(uuid.uuid4())
        self.client = None
        
        print(f"🆔 Session ID: {self.session_id}\n")
    
    def _get_headers(self):
        """Build common headers."""
        return {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "mcp-session-id": self.session_id,
            "mcp-protocol-version": MCP_PROTOCOL_VERSION,
        }
    
    async def __aenter__(self):
        """Create persistent HTTP/2 connection."""
        self.client = httpx.AsyncClient(
            http2=True,
            timeout=httpx.Timeout(30.0, connect=10.0)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close connection."""
        if self.client:
            await self.client.aclose()
    
    async def send_request(self, payload):
        """Send a JSON-RPC request."""
        method_name = payload.get("method", "unknown")
        print(f"📤 Sending: {method_name}")
        print(f"   Payload: {json.dumps(payload, indent=6)}")
        
        try:
            response = await self.client.post(
                self.url,
                headers=self._get_headers(),
                json=payload
            )
            
            print(f"   ✅ HTTP {response.status_code}")
            
            if response.status_code != 200:
                print(f"   ❌ Error: {response.text}\n")
                return None
            
            # Try to parse JSON response
            try:
                result = response.json()
                print(f"   📥 Response:")
                print(f"      {json.dumps(result, indent=6)}\n")
                return result
            except json.JSONDecodeError:
                # For notifications, empty response is OK
                if "id" not in payload:
                    print(f"   ✅ Notification acknowledged\n")
                    return {"status": "ok"}
                else:
                    print(f"   ⚠️ Non-JSON response: {response.text}\n")
                    return None
                    
        except httpx.HTTPError as e:
            print(f"   ❌ HTTP Error: {e}\n")
            return None


async def main():
    print("=" * 70)
    print("🚀 MCP CLIENT - GITHUB COPILOT")
    print("=" * 70 + "\n")
    
    async with MCPClient(MCP_URL, AUTH_TOKEN) as client:
        
        # Step 1: Initialize
        print("🔧 STEP 1: Initialize Connection")
        print("-" * 70)
        
        init_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {
                    "roots": {"listChanged": True},
                },
                "clientInfo": {
                    "name": "python-mcp-client",
                    "version": "1.0.0"
                },
            },
        }
        
        init_response = await client.send_request(init_payload)
        
        if not init_response or "error" in init_response:
            print("❌ Initialization failed! Stopping.\n")
            return
        
        if "result" in init_response:
            server_info = init_response["result"].get("serverInfo", {})
            print(f"✅ Connected to: {server_info.get('name', 'Unknown')}")
            print(f"   Version: {server_info.get('version', 'Unknown')}")
            print(f"   Protocol: {init_response['result'].get('protocolVersion', 'Unknown')}\n")
        
        # Step 2: Send initialized notification
        print("🔧 STEP 2: Send Initialized Notification")
        print("-" * 70)
        
        initialized_payload = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        }
        
        await client.send_request(initialized_payload)
        
        # Give server a moment to process
        await asyncio.sleep(0.5)
        
        # Step 3: List tools
        print("🔧 STEP 3: List Available Tools")
        print("-" * 70)
        
        list_tools_payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
        }
        
        tools_response = await client.send_request(list_tools_payload)
        
        if tools_response and "result" in tools_response:
            tools = tools_response["result"].get("tools", [])
            
            print(f"{'=' * 70}")
            print(f"📋 AVAILABLE TOOLS: {len(tools)} total")
            print(f"{'=' * 70}\n")
            
            for i, tool in enumerate(tools, 1):
                name = tool.get("name", "Unknown")
                desc = tool.get("description", "No description")
                
                print(f"{i}. {name}")
                print(f"   {desc[:100]}{'...' if len(desc) > 100 else ''}")
                
                # Show input schema briefly
                input_schema = tool.get("inputSchema", {})
                props = input_schema.get("properties", {})
                if props:
                    required = input_schema.get("required", [])
                    params = [f"{k}{'*' if k in required else ''}" for k in list(props.keys())[:3]]
                    print(f"   Parameters: {', '.join(params)}")
                    if len(props) > 3:
                        print(f"   ... and {len(props) - 3} more")
                print()
            
        else:
            print("❌ Failed to retrieve tools\n")
        
        # Step 4: List prompts
        print("🔧 STEP 4: List Available Prompts")
        print("-" * 70)
        
        list_prompts_payload = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "prompts/list",
        }
        
        prompts_response = await client.send_request(list_prompts_payload)
        
        if prompts_response and "result" in prompts_response:
            prompts = prompts_response["result"].get("prompts", [])
            print(f"\n✅ Found {len(prompts)} prompts")
            for prompt in prompts[:5]:
                print(f"   • {prompt.get('name', 'Unknown')}")


if __name__ == "__main__":
    asyncio.run(main())