"""
Worker autonome pour dourbia — lancé en subprocess.
Lit un JSON sur stdin, écrit un JSON sur stdout.
"""

import asyncio, json, sys, os

DOURBIA = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "dourbia_v10_final")
)
sys.path.insert(0, DOURBIA)
os.chdir(DOURBIA)

from agents.agent import run_agent


async def main():
    data = json.loads(sys.stdin.readline())
    reply, tokens = await run_agent(data["message"], data["session_id"])
    print(json.dumps({"reply": reply, "tokens": tokens}))


asyncio.run(main())
