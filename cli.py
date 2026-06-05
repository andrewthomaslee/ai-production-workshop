"""CLI entry point: an interactive REPL over a single local session.

The CLI is just *one user* of the same engine the server serves. It builds a
`Session` (user "local", role "admin", no remote auth) and drives it. That's the
whole point: code-first (this CLI) and no-code (the web client) are two surfaces
on one engine; there is no separate "CLI agent." Run:

    python cli.py                       # subprocess sandbox (default)
    python cli.py --sandbox docker      # Docker sandbox
    python cli.py --model gpt-5.5        # frontier model
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from agent.core.session import Session
from agent.skills import SkillLibrary

load_dotenv()  # read key/config from a local .env file if present

ROOT = Path(__file__).parent
# Latest small/fast model (as of June 2026). Frontier: gpt-5.5. Cheapest: gpt-5.4-nano.
DEFAULT_MODEL = "gpt-5.4-mini"

# --- terminal colors, so the loop's steps are easy to follow ----------------
DIM, CYAN, GREEN, YELLOW, RESET = "\033[2m", "\033[36m", "\033[32m", "\033[33m", "\033[0m"


def make_printer():
    def on_event(kind: str, data: dict) -> None:
        if kind == "thinking" and data["text"]:
            print(f"\n{GREEN}{data['text']}{RESET}")
        elif kind == "tool":
            print(f"{CYAN}→ {data['name']}({_brief(data['input'])}){RESET}")
        elif kind == "result":
            print(f"{DIM}  {_brief(data['output'], 200)}{RESET}")
    return on_event


def _brief(value, limit: int = 120) -> str:
    text = str(value).replace("\n", " ")
    return text if len(text) <= limit else text[:limit] + "…"


def build_session(model: str, sandbox: str) -> Session:
    skills = SkillLibrary(ROOT / "agent" / "skills")
    client = OpenAI()  # reads OPENAI_API_KEY from the environment
    # No policy / no audit for the local CLI: a single trusted admin user.
    return Session(
        user_id="local", role="admin", model=model, sandbox_kind=sandbox,
        root=ROOT, skills=skills, client=client, policy=None, audit=None,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="A small, didactic agent.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--sandbox", default="subprocess", choices=["subprocess", "docker"])
    args = parser.parse_args()

    if not os.environ.get("OPENAI_API_KEY", "").startswith("sk-") or os.environ.get("OPENAI_API_KEY") == "sk-...":
        raise SystemExit("Set OPENAI_API_KEY in your .env file (see .env.example).")

    session = build_session(args.model, args.sandbox)
    printer = make_printer()

    print(f"{YELLOW}Agent ready.{RESET} model={args.model} sandbox={args.sandbox}")
    print(f"{DIM}Type a task. Ctrl-C or 'exit' to quit.{RESET}")
    while True:
        try:
            user = input(f"\n{YELLOW}you ›{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            break
        if user.lower() in {"exit", "quit"}:
            break
        if not user:
            continue
        answer = session.agent.run(user, on_event=printer)
        print(f"\n{YELLOW}agent ›{RESET} {answer}")


if __name__ == "__main__":
    main()
