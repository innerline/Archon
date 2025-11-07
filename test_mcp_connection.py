#!/usr/bin/env python3
"""
Test MCP server connection and tool retrieval.
This script will start the MCP server if needed and retrieve available tools.
"""

import asyncio
import aiohttp
import json
import sys
import time
from typing import Dict, Any, List


async def test_mcp_server_connection():
    """Test MCP server connection and retrieve tools."""
    print("🚀 Testing Archon MCP Server Connection")
    print("="*60)
    
    # Configuration
    api_base_url = "http://localhost:8181"
    mcp_direct_url = "http://localhost:8051/mcp"
    
    async with aiohttp.ClientSession() as session:
        
        # Test 1: Check if API server is running
        print("\n1️⃣  Checking API Server Status...")
        try:
            async with session.get(f"{api_base_url}/api/mcp/status", timeout=5) as response:
                if response.status == 200:
                    status_data = await response.json()
                    print(f"✅ API Server Status: {status_data.get('status', 'unknown')}")
                    server_running = status_data.get('status') == 'running'
                else:
                    print(f"❌ API Server Error: HTTP {response.status}")
                    server_running = False
        except Exception as e:
            print(f"❌ API Server Connection Failed: {e}")
            print("💡 Make sure Archon server is running: docker-compose up -d")
            server_running = False
        
        # Test 2: Try to start MCP server if API is available
        if server_running:
            print("\n2️⃣  Starting MCP Server...")
            try:
                async with session.post(f"{api_base_url}/api/mcp/start", timeout=30) as response:
                    if response.status == 200:
                        start_data = await response.json()
                        if start_data.get('success'):
                            print("✅ MCP Server Started Successfully")
                            await asyncio.sleep(3)  # Wait for server to fully start
                        else:
                            print(f"⚠️  MCP Server Start Failed: {start_data.get('message', 'Unknown error')}")
                    else:
                        error_text = await response.text()
                        print(f"❌ MCP Server Start Error: HTTP {response.status} - {error_text}")
            except Exception as e:
                print(f"❌ MCP Server Start Failed: {e}")
        
        # Test 3: Get tools via API endpoint
        print("\n3️⃣  Retrieving Tools via API Endpoint...")
        try:
            async with session.get(f"{api_base_url}/api/mcp/tools", timeout=10) as response:
                if response.status == 200:
                    api_tools_data = await response.json()
                    tools = api_tools_data.get('tools', [])
                    count = api_tools_data.get('count', 0)
                    source = api_tools_data.get('source', 'unknown')
                    message = api_tools_data.get('message', '')
                    
                    print(f"✅ API Tools Response:")
                    print(f"   📊 Tool Count: {count}")
                    print(f"   🔍 Source: {source}")
                    print(f"   📝 Message: {message}")
                    
                    if tools:
                        print(f"\n   📋 Available Tools:")
                        for i, tool in enumerate(tools, 1):
                            name = tool.get('name', 'Unknown')
                            desc = tool.get('description', 'No description')
                            params = tool.get('parameters', [])
                            print(f"      {i}. **{name}**")
                            if desc and desc != 'No description':
                                print(f"         📝 {desc}")
                            if params:
                                print(f"         ⚙️  Parameters: {len(params)}")
                                for param in params[:3]:  # Show first 3 params
                                    param_name = param.get('name', 'Unknown')
                                    param_type = param.get('type', 'any')
                                    param_required = "🔴" if param.get('required') else "⚪"
                                    print(f"           - {param_name} ({param_type}) {param_required}")
                                if len(params) > 3:
                                    print(f"           ... and {len(params) - 3} more parameters")
                            print()
                    else:
                        print("   ❌ No tools found")
                else:
                    error_text = await response.text()
                    print(f"❌ API Tools Error: HTTP {response.status} - {error_text}")
        except Exception as e:
            print(f"❌ API Tools Request Failed: {e}")
        
        # Test 4: Direct MCP server communication
        print("\n4️⃣  Direct MCP Server Communication...")
        mcp_request = {
            "jsonrpc": "2.0",
            "id": "test_connection",
            "method": "tools/list"
        }
        
        try:
            async with session.post(
                mcp_direct_url,
                json=mcp_request,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"
                },
                timeout=10
            ) as response:
                if response.status == 200:
                    mcp_response = await response.json()
                    
                    if "result" in mcp_response and "tools" in mcp_response["result"]:
                        tools = mcp_response["result"]["tools"]
                        print(f"✅ Direct MCP Communication Success")
                        print(f"   📊 Raw Tools Count: {len(tools)}")
                        print(f"   🔧 Raw Tool Details:")
                        for i, tool in enumerate(tools, 1):
                            name = tool.get('name', 'Unknown')
                            desc = tool.get('description', 'No description')
                            print(f"      {i}. **{name}** - {desc}")
                    elif "error" in mcp_response:
                        error_msg = mcp_response["error"].get("message", "Unknown MCP error")
                        print(f"❌ MCP Server Error: {error_msg}")
                    else:
                        print(f"❌ Unexpected MCP Response: {mcp_response}")
                else:
                    error_text = await response.text()
                    print(f"❌ Direct MCP Error: HTTP {response.status} - {error_text}")
        except Exception as e:
            print(f"❌ Direct MCP Connection Failed: {e}")
        
        # Test 5: Test specific MCP tools if available
        print("\n5️⃣  Testing MCP Tools (if available)...")
        try:
            # Try to call the health_check tool as a test
            health_request = {
                "jsonrpc": "2.0",
                "id": "health_test",
                "method": "tools/call",
                "params": {
                    "name": "health_check",
                    "arguments": {}
                }
            }
            
            async with session.post(
                mcp_direct_url,
                json=health_request,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"
                },
                timeout=10
            ) as response:
                if response.status == 200:
                    health_response = await response.json()
                    if "result" in health_response:
                        print("✅ MCP Tool Call Test Successful")
                        result = health_response["result"]
                        if isinstance(result, str):
                            # Try to parse JSON string
                            try:
                                result_data = json.loads(result)
                                print(f"   🏥 Health Check Result: {json.dumps(result_data, indent=2)}")
                            except:
                                print(f"   🏥 Health Check Result: {result}")
                        else:
                            print(f"   🏥 Health Check Result: {result}")
                    else:
                        print("❌ MCP Tool Call Failed")
                else:
                    error_text = await response.text()
                    print(f"❌ MCP Tool Call HTTP Error: {error_text}")
        except Exception as e:
            print(f"❌ MCP Tool Call Test Failed: {e}")


async def main():
    """Main test function."""
    await test_mcp_server_connection()
    
    print("\n" + "="*60)
    print("🏁 Test Complete")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())