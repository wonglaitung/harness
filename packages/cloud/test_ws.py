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
        print("Usage: python test_ws.py <session_id> [options]")
        print("")
        print("Options:")
        print("  --api-key KEY         API key (required)")
        print("  --provider PROVIDER   Provider: anthropic or openai (default: anthropic)")
        print("  --base-url URL        Custom API base URL (for OpenAI-compatible APIs)")
        print("  --model MODEL         Model name (default: claude-sonnet-4-6)")
        print("")
        print("Examples:")
        print("  python test_ws.py abc123 --api-key sk-ant-xxx --provider anthropic")
        print("  python test_ws.py abc123 --api-key sk-xxx --provider openai --model gpt-4o")
        print("  python test_ws.py abc123 --api-key your-key --provider openai --base-url https://your-api.com/v1 --model your-model")
        sys.exit(1)

    session_id = sys.argv[1]

    # Parse arguments
    api_key = None
    provider = "anthropic"
    base_url = None
    model = "claude-sonnet-4-6"

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--api-key" and i + 1 < len(sys.argv):
            api_key = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--provider" and i + 1 < len(sys.argv):
            provider = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--base-url" and i + 1 < len(sys.argv):
            base_url = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--model" and i + 1 < len(sys.argv):
            model = sys.argv[i + 1]
            i += 2
        else:
            print(f"Unknown option: {sys.argv[i]}")
            sys.exit(1)

    if not api_key:
        print("Error: --api-key is required")
        sys.exit(1)

    url = f"ws://localhost:8080/ws/session/{session_id}"
    print(f"Connecting to {url}")
    print(f"Provider: {provider}, Model: {model}")
    if base_url:
        print(f"Base URL: {base_url}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(url) as ws:
                print("Connected! Sending Gateway auth...")

                # Send Gateway auth
                await ws.send_json({"type": "auth", "token": "test-token"})
                await asyncio.sleep(0.5)  # Wait for tunnel

                # Send Agent auth
                print("Sending Agent auth...")
                auth_payload = {
                    "api_key": api_key,
                    "provider": provider,
                    "model": model
                }
                if base_url:
                    auth_payload["base_url"] = base_url

                await ws.send_json({
                    "type": "auth",
                    "payload": auth_payload
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
