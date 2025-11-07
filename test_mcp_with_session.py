#!/usr/bin/env python3
"""
Test MCP server with proper session management.
This script handles the MCP protocol correctly by establishing a session first.
"""

import asyncio
import aiohttp
import json
import re
from typing import Dict, Any, Optional


async def test_mcp_with_proper_session():
    """Test MCP server with proper session handling."""
    print("🔗 Testing Archon MCP Server with Session Management")
    print("="*70)
    
    mcp_url = "http://localhost:8051/mcp"
    session_id: Optional[str] = None
    tools_list = []
    
    async with aiohttp.ClientSession() as session:
        
        # Step 1: Establish a session with the MCP server
        print("\n1️⃣  Establishing MCP Session...")
        try:
            # Make a session-establishing request
            session_request = {
                "jsonrpc": "2.0",
                "id": "session_init",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "test-client",
                        "version": "1.0.0"
                    }
                }
            }
            
            async with session.post(
                mcp_url,
                json=session_request,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"
                },
                timeout=10
            ) as response:
                if response.status == 200:
                    init_response = await response.json()
                    print("✅ MCP Session Established Successfully")
                    
                    # Extract session info if available
                    if "result" in init_response:
                        result = init_response["result"]
                        if "sessionId" in result:
                            session_id = result["sessionId"]
                            print(f"   🆔 Session ID: {session_id}")
                        
                        # Check for any available tools from initialization
                        if "capabilities" in result and "tools" in result["capabilities"]:
                            tools_list = result["capabilities"]["tools"].get("listChanged", [])
                            print(f"   🔧 Tools from initialization: {len(tools_list)}")
                    
                    if "error" in init_response:
                        print(f"   ❌ Session Error: {init_response['error']}")
                else:
                    error_text = await response.text()
                    print(f"❌ Session Establishment Failed: HTTP {response.status}")
                    print(f"   Response: {error_text}")
                    
        except Exception as e:
            print(f"❌ Session Establishment Exception: {e}")
        
        # Step 2: Get tools list using proper MCP protocol
        print("\n2️⃣  Retrieving Tools List...")
        try:
            tools_request = {
                "jsonrpc": "2.0",
                "id": "tools_list",
                "method": "tools/list",
                "params": {}
            }
            
            # Add session ID if we have one
            if session_id:
                tools_request["params"]["sessionId"] = session_id
            
            async with session.post(
                mcp_url,
                json=tools_request,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"
                },
                timeout=10
            ) as response:
                if response.status == 200:
                    tools_response = await response.json()
                    
                    if "result" in tools_response and "tools" in tools_response["result"]:
                        tools = tools_response["result"]["tools"]
                        print(f"✅ Tools Retrieved Successfully!")
                        print(f"   📊 Tool Count: {len(tools)}")
                        tools_list = tools
                    elif "error" in tools_response:
                        error_msg = tools_response["error"].get("message", "Unknown error")
                        print(f"❌ Tools List Error: {error_msg}")
                    else:
                        print(f"❌ Unexpected Tools Response: {tools_response}")
                else:
                    error_text = await response.text()
                    print(f"❌ Tools Request Failed: HTTP {response.status}")
                    print(f"   Response: {error_text}")
                    
        except Exception as e:
            print(f"❌ Tools Request Exception: {e}")
        
        # Step 3: Test a specific tool if we have tools
        if tools_list:
            print(f"\n3️⃣  Testing MCP Tools...")
            print(f"   📋 Available Tools:")
            
            for i, tool in enumerate(tools_list, 1):
                name = tool.get('name', 'Unknown')
                desc = tool.get('description', 'No description')
                print(f"      {i}. **{name}** - {desc}")
                
                # Try to call the health_check tool as a test
                if name == "health_check":
                    try:
                        call_request = {
                            "jsonrpc": "2.0",
                            "id": f"call_{name}",
                            "method": "tools/call",
                            "params": {
                                "name": name,
                                "arguments": {}
                            }
                        }
                        
                        if session_id:
                            call_request["params"]["sessionId"] = session_id
                        
                        async with session.post(
                            mcp_url,
                            json=call_request,
                            headers={
                                "Content-Type": "application/json",
                                "Accept": "application/json, text/event-stream"
                            },
                            timeout=10
                        ) as response:
                            if response.status == 200:
                                call_response = await response.json()
                                if "result" in call_response:
                                    result = call_response["result"]
                                    print(f"         ✅ Tool Call Successful!")
                                    print(f"         🏥 Result: {result}")
                                elif "error" in call_response:
                                    print(f"         ❌ Tool Call Error: {call_response['error']}")
                            else:
                                error_text = await response.text()
                                print(f"         ❌ Tool Call Failed: {error_text}")
                                
                    except Exception as e:
                        print(f"         ❌ Tool Call Exception: {e}")
        else:
            print("\n3️⃣  No Tools Available to Test")
        
        # Step 4: Alternative session establishment via health check
        print(f"\n4️⃣  Trying Health Check Session Method...")
        try:
            health_request = {
                "jsonrpc": "2.0",
                "id": "health_session",
                "method": "tools/call",
                "params": {
                    "name": "health_check",
                    "arguments": {}
                }
            }
            
            async with session.post(
                mcp_url,
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
                        result = health_response["result"]
                        print("✅ Health Check Successful!")
                        print(f"   🏥 Health: {result}")
                        
                        # Try to parse if it's JSON string
                        if isinstance(result, str):
                            try:
                                result_data = json.loads(result)
                                print(f"   📊 Parsed Health Data:")
                                for key, value in result_data.items():
                                    print(f"      {key}: {value}")
                            except:
                                pass
                    else:
                        print(f"❌ Health Check Failed: {health_response}")
                else:
                    error_text = await response.text()
                    print(f"❌ Health Check Failed: HTTP {response.status}")
                    print(f"   Response: {error_text}")
                    
        except Exception as e:
            print(f"❌ Health Check Exception: {e}")


async def test_api_endpoint_after_session():
    """Test the API endpoint after establishing MCP session."""
    print(f"\n5️⃣  Testing API Endpoint...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8181/api/mcp/tools", timeout=10) as response:
                if response.status == 200:
                    api_data = await response.json()
                    tools = api_data.get('tools', [])
                    count = api_data.get('count', 0)
                    source = api_data.get('source', 'unknown')
                    message = api_data.get('message', '')
                    
                    print(f"✅ API Endpoint Response:")
                    print(f"   📊 Tool Count: {count}")
                    print(f"   🔍 Source: {source}")
                    print(f"   📝 Message: {message}")
                    
                    if tools:
                        print(f"   📋 Tools from API:")
                        for i, tool in enumerate(tools, 1):
                            name = tool.get('name', 'Unknown')
                            desc = tool.get('description', 'No description')
                            print(f"      {i}. **{name}** - {desc}")
                    else:
                        print(f"   ❌ No tools from API endpoint")
                else:
                    error_text = await response.text()
                    print(f"❌ API Endpoint Failed: HTTP {response.status}")
                    print(f"   Response: {error_text}")
                    
    except Exception as e:
        print(f"❌ API Endpoint Exception: {e}")


async def main():
    """Main test function."""
    await test_mcp_with_proper_session()
    await test_api_endpoint_after_session()
    
    print("\n" + "="*70)
    print("🏁 Session-based Test Complete")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())