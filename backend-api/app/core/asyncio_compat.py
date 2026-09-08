"""Windows compatibility shim.

psycopg3's async mode refuses to run under asyncio's default Windows loop
(`ProactorEventLoop`) -- it requires a selector-based loop. Call
`apply_windows_event_loop_policy()` as early as possible (before any event
loop is created) in every process entrypoint: app/main.py and tests/conftest.py.
No-op on non-Windows platforms.

Caveat: this only helps entrypoints that create their event loop *after*
importing this module (pytest does; a custom `python run.py`-style script
would too). It does NOT help `uv run uvicorn app.main:app` with no
`--reload` on Windows -- uvicorn's `asyncio.run()` creates its loop before
importing the ASGI app string, so the policy is set too late. Always keep
`--reload` for a plain `uvicorn` run on Windows (see README) -- uvicorn
spawns a reloader subprocess in that mode and picks a selector-based loop
for it automatically. Docker (Linux) is unaffected either way.
"""

import asyncio
import sys


def apply_windows_event_loop_policy() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
