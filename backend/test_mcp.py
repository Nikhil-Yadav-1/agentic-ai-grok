#!/usr/bin/env python3
"""
Test script to verify MCP tool integration
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.load_tools import load_all_tools

def test_tool_loading():
    """Test that tools are loaded correctly"""
    print("=" * 80)
    print("Testing Tool Loading")
    print("=" * 80)
    
    tools = load_all_tools()
    
    print(f"\n✅ Successfully loaded {len(tools)} tools\n")
    
    for i, tool in enumerate(tools, 1):
        print(f"{i}. {tool.name}")
        print(f"   Description: {tool.description[:100]}...")
        print()
    
    # Check if universal_mcp_tool is loaded
    mcp_tool = next((t for t in tools if "mcp" in t.name.lower()), None)
    
    if mcp_tool:
        print("✅ Universal MCP tool found!")
        print(f"   Name: {mcp_tool.name}")
        print(f"   Description: {mcp_tool.description[:200]}...")
    else:
        print("❌ Universal MCP tool NOT found!")
        print("   Make sure TOOL_MODULES includes 'backend.mcp_tools' in your .env")
    
    return tools


def test_mcp_tool():
    """Test the MCP tool directly"""
    print("\n" + "=" * 80)
    print("Testing MCP Tool Directly")
    print("=" * 80)
    
    try:
        from backend.mcp_tools import universal_mcp_tool
        
        # Test with a simple query
        print("\nTest: List tools from default server")
        print("-" * 80)
        
        result = universal_mcp_tool.run("list_tools from https://api.githubcopilot.com/mcp/")
        print(result)
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing MCP tool: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                   MCP Tool Integration Test Suite                           ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Test 1: Tool loading
    tools = test_tool_loading()
    
    # Test 2: Direct MCP tool test
    if any("mcp" in t.name.lower() for t in tools):
        test_mcp_tool()
    
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    print(f"Total tools loaded: {len(tools)}")
    print("Tool names:", [t.name for t in tools])
    
    # Check if setup is complete
    required_tools = ["universal_mcp_tool"]
    loaded_tool_names = [t.name for t in tools]
    
    all_found = all(any(req in name.lower() for name in loaded_tool_names) for req in required_tools)
    
    if all_found:
        print("\n✅ All required tools found! Setup is complete.")
        print("\nYour agent can now:")
        print("  1. Discover tools from any MCP server")
        print("  2. Call tools dynamically without hardcoding")
        print("  3. Work with ANY MCP-compliant server")
    else:
        print("\n⚠️  Some tools are missing. Check your configuration.")
        print("\nMake sure your .env has:")
        print("  TOOL_MODULES=backend.tools,backend.mcp_tools")


if __name__ == "__main__":
    main()