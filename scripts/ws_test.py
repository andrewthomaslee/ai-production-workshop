"""Manual WebSocket streaming test: connects, sends a task, prints the stream."""
import asyncio
import json
import sys

import websockets


async def main(port: int) -> None:
    async with websockets.connect(f"ws://127.0.0.1:{port}/ws") as ws:
        await ws.send(json.dumps({
            "user_id": "carol", "role": "analyst",
            "message": "Use run_python to compute 12 factorial, then tell me just the number.",
        }))
        steps = []
        while True:
            msg = json.loads(await ws.recv())
            t = msg["type"]
            if t == "tool":
                name = msg["name"]
                inp = json.dumps(msg["input"])[:50]
                print(f"  STREAM tool   -> {name}({inp})")
                steps.append("tool")
            elif t == "result":
                print("  STREAM result -> " + msg["output"][:60])
                steps.append("result")
            elif t == "thinking":
                print("  STREAM think  -> " + msg["text"][:60])
            elif t == "done":
                print("  STREAM done   -> " + msg["answer"][:80])
                break
        assert "tool" in steps and "result" in steps, "expected streamed tool+result events"
        print("WS STREAMING OK:", steps)


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 8055))
