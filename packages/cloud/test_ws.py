#!/usr/bin/env python3
"""
Test script for Harness Cloud WebSocket connection.
Automatically sends Gateway auth, then allows interactive chat.
"""

import asyncio
import json
import sys
import aiohttp


async def main():
    if len(sys.argv) < 2:
        print("Usage: python test_ws.py <session_id> [api_key] [provider]")
        print("Example: python test_ws.py abc123 sk-ant-xxx anthropic")
        sys.exit(1)

    session_id = sys.argv[1]
    api_key = sys.argv[2] if len(sys.argv) > 2 else "test-api-key"
    provider = sys.argv[3] if len(sys.argv) > 3 else "anthropic"

    url = f"ws://localhost:8080/ws/session/{session_id}"
    print(f"Connecting to {url}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(url) as ws:
                print("Connected! Sending Gateway auth...")

                # Send Gateway auth
                await ws.send_json({"type": "auth", "token": "test-token"})
                await asyncio.sleep(0.5)  # Wait for tunnel

                # Send Agent auth
                print("Sending Agent auth...")
                await ws.send_json({
                    "type": "auth",
                    "payload": {
                        "api_key": api_key,
                        "provider": provider
                    }
                })

                # Wait for auth_success
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        print(f"< {json.dumps(data)}")

                        if data.get("type") == "auth_success":
                            print("\nAuthenticated! Enter prompts (Ctrl+C to exit):")

                            # Start interactive loop
                            async def send_prompts():
                                loop = asyncio.get_event_loop()
                                while True:
                                    prompt = await loop.run_in_executor(None, input, "> ")
                                    if prompt:
                                        await ws.send_json({
                                            "type": "run_request",
                                            "payload": {"prompt": prompt}
                                        })

                            async def receive_messages():
                                async for msg in ws:
                                    if msg.type == aiohttp.WSMsgType.TEXT:
                                        data = json.loads(msg.data)
                                        if data.get("type") == "stream_chunk":
                                            print(data.get("payload", {}).get("content", ""), end="", flush=True)
                                        elif data.get("type") == "run_result":
                                            print()  # New line after response

                            # Run both tasks
                            await asyncio.gather(send_prompts(), receive_messages())

                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        print(f"WebSocket error: {ws.exception()}")
                        break

    except aiohttp.ClientError as e:
        print(f"Connection error: {e}")
    except KeyboardInterrupt:
        print("\nDisconnected.")


if __name__ == "__main__":
    asyncio.run(main())
