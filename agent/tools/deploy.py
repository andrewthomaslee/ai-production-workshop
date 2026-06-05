"""Deploy tool for the Website Shipping Agent (P4): brief -> live URL.

Self-contained: it does NOT call an external host. It copies a site directory
from the user's workspace into a global deploy root and serves it over a tiny
built-in static HTTP server, returning a REAL, working localhost URL. From a live
demo's perspective this is the full loop: the agent writes index.html, calls
deploy_site, and you click a link that opens the running page.

The static server is a module-level singleton started on first use, so it works
identically from the CLI and from the API. In production, `deploy_site` would
push to S3/Netlify/Vercel and return that URL; the tool's contract (a directory
in, a URL out) stays the same.
"""

from __future__ import annotations

import shutil
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .base import Tool

# Where deployed sites live, and the static server that serves them.
_DEPLOY_ROOT = Path(__file__).resolve().parents[2] / "deploys"
_HOST, _PORT = "127.0.0.1", 8787
_server_started = False
_lock = threading.Lock()


def _ensure_server() -> None:
    global _server_started
    with _lock:
        if _server_started:
            return
        _DEPLOY_ROOT.mkdir(parents=True, exist_ok=True)
        handler = partial(SimpleHTTPRequestHandler, directory=str(_DEPLOY_ROOT))
        httpd = ThreadingHTTPServer((_HOST, _PORT), handler)
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        _server_started = True


class DeploySite(Tool):
    name = "deploy_site"
    description = (
        "Deploy a website to a live URL. Provide the name of a directory in your "
        "workspace that contains an index.html (and any assets). Returns a working "
        "URL you can open. Build the site files first with write_file."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "site_dir": {"type": "string", "description": "Workspace directory holding index.html (e.g. 'site')."},
            "slug": {"type": "string", "description": "URL slug for the deployment (e.g. 'acme-landing')."},
        },
        "required": ["site_dir", "slug"],
    }

    def __init__(self, workspace: Path):
        self.workspace = Path(workspace).resolve()

    def run(self, site_dir: str, slug: str) -> str:
        src = (self.workspace / site_dir).resolve()
        if not src.is_relative_to(self.workspace):
            return f"Error: '{site_dir}' escapes the workspace"
        if not src.is_dir():
            return f"Error: '{site_dir}' is not a directory in the workspace"
        if not (src / "index.html").exists():
            return f"Error: '{site_dir}/index.html' not found. Create it first with write_file"

        safe_slug = "".join(c if c.isalnum() or c in "-_" else "-" for c in slug).strip("-") or "site"
        dest = _DEPLOY_ROOT / safe_slug
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)

        _ensure_server()
        url = f"http://{_HOST}:{_PORT}/{safe_slug}/"
        return f"Deployed '{site_dir}' to {url}\nThe site is live now. Open the URL to view it."
