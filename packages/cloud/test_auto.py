#!/usr/bin/env python3
"""
Fully automated test for Harness Cloud.
Creates session, connects, authenticates, and sends a test prompt.
"""

import asyncio
import json
import sys
import aiohttp
import httpx


async def main():
    if len(sys.argv) < 2:
        print("Usage: python test_auto.py <api_key> [options]")
        print("")
        print("Options:")
        print("  --provider PROVIDER   Provider: anthropic or openai (default: anthropic)")
        print("  --base-url URL        Custom API base URL (for OpenAI-compatible APIs)")
        print("  --model MODEL         Model name (default: claude-sonnet-4-6)")
        print("  --prompt PROMPT       Test prompt (default: 'Hello, what can you do?')")
        print("")
        print("Examples:")
        print("  python test_auto.py sk-ant-xxx")
        print("  python test_auto.py sk-xxx --provider openai --model gpt-4o")
        print("  python test_auto.py your-key --provider openai --base-url https://api.example.com/v1 --model gpt-4o-mini")
        sys.exit(1)

    # Parse arguments
    api_key = sys.argv[1]
    provider = "anthropic"
    base_url = None
    model = "claude-sonnet-4-6"
    test_prompt = "Hello, what can you do?"

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--provider" and i + 1 < len(sys.argv):
            provider = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--base-url" and i + 1 < len(sys.argv):
            base_url = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--model" and i + 1 < len(sys.argv):
            model = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--prompt" and i + 1 < len(sys.argv):
            test_prompt = sys.argv[i + 1]
            i += 2
        else:
            print(f"Unknown option: {sys.argv[i]}")
            sys.exit(1)

    print("=== Harness Cloud Automated Test ===\n")

    # Step 1: Create session
    print("Step 1: Creating session...")
    async with httpx.AsyncClient() as client:
        response = await client.post("http://localhost:8080/api/sessions")
        if response.status_code != 200:
            print(f"Error creating session: {response.status_code}")
            sys.exit(1)
        session_data = response.json()
        session_id = session_data["session_id"]
        print(f"Session created: {session_id}")

    # Step 2: Connect and authenticate
    print(f"\nStep 2: Connecting to WebSocket...")
    print(f"Provider: {provider}, Model: {model}")
    if base_url:
        print(f"Base URL: {base_url}")

    url = f"ws://localhost:8080/ws/session/{session_id}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(url) as ws:
                print("Connected! Authenticating...")

                # Gateway auth
                await ws.send_json({"type": "auth", "token": "test-token"})
                await asyncio.sleep(0.5)

                # Agent auth
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

                # Step 3: Send test prompt and receive response
                print(f"\nStep 3: Sending test prompt: '{test_prompt}'\n")
                print("-" * 40)

                authenticated = False
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        msg_type = data.get("type")

                        if msg_type == "auth_success":
                            authenticated = True
                            # Send test prompt
                            await ws.send_json({
                                "type": "run_request",
                                "payload": {"prompt": test_prompt}
                            })
                        elif msg_type == "auth_failed":
                            print(f"Authentication failed: {data}")
                            break
                        elif msg_type == "stream_chunk":
                            content = data.get("payload", {}).get("content", "")
                            print(content, end="", flush=True)
                        elif msg_type == "run_result":
                            print("\n" + "-" * 40)
                            print("\nTest completed successfully!")
                            break
                        elif msg_type == "error":
                            print(f"\nError: {data}")
                            break

                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        print(f"WebSocket error: {ws.exception()}")
                        break

    except aiohttp.ClientError as e:
        print(f"Connection error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
