import asyncio
import websockets


async def test():
    try:
        async with websockets.connect(
            "ws://127.0.0.1:8000/ws/live/all"
        ) as ws:
            print("CONNECTED")
            message = await ws.recv()
            print("RECEIVED:")
            print(message)

    except Exception as exc:
        print("FAILED:")
        print(type(exc).__name__, str(exc))


asyncio.run(test())