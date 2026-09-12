import asyncio
import websockets

async def test():
    uri = "ws://127.0.0.1:8000/ws/live/all"

    print("Connecting to:", uri)

    async with websockets.connect(uri) as ws:
        print("CONNECTED")
        print("Waiting for live data...")

        for i in range(5):
            message = await ws.recv()
            print(f"\n--- MESSAGE {i + 1} ---")
            print(message)

asyncio.run(test())