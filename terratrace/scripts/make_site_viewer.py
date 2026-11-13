#!/usr/bin/env python3
"""Wrap the engine's generated study viewer as the site's ``/viewer`` page.

``terratrace/viewer/index.html`` is the engine's own output (``python -m terratrace.build_viewer``)
and is kept byte-faithful. ``site/viewer/index.html`` is that document plus a small labelled header
bar, so a reader arriving from the site can tell what they are looking at and get back — the raw
output carries no links of its own, and it is an *archived* real run whose result (a TIE) is not the
project's current headline.

Only three things are added, and this script is the only place they are defined:
  * the ``<title>``, so the browser tab does not read as an old engine version;
  * a ``.sitebar`` stylesheet block, inserted just before ``</style>``;
  * a ``.sitebar`` element and favicon, inserted just after ``<body>``.

Run:  python scripts/make_site_viewer.py
"""
from __future__ import annotations

import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent                      # .../terratrace
REPO = ROOT.parent

SRC = ROOT / "viewer" / "index.html"
OUT = REPO / "site" / "viewer" / "index.html"

OLD_TITLE = "<title>TerraTrace v0.1 - study viewer</title>"
NEW_TITLE = "<title>Raw study output — TerraTrace</title>"

FAVICON = ('<link rel="icon" href="data:image/svg+xml,'
           "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
           "%3Ccircle cx='16' cy='16' r='14' fill='%23C6613A'/%3E"
           "%3Cpath d='M4 13c4 2 8-2 12 0s8 3 12 1' stroke='%23060910' stroke-width='2' "
           "fill='none' opacity='.55'/%3E%3C/svg%3E\">")

CSS = """
/* site wrapper — added by scripts/make_site_viewer.py, NOT part of the engine's output */
.sitebar{position:sticky;top:0;z-index:99;background:#0A1118;border-bottom:1px solid #2b3c44;
 font-family:'Segoe UI',Helvetica,Arial,sans-serif;font-size:13px;color:#B7C5C8}
.sitebar .in{max-width:1040px;margin:0 auto;padding:10px 28px;display:flex;gap:12px;
 align-items:center;flex-wrap:wrap}
.sitebar a{color:#9BE4E9;text-decoration:none}
.sitebar a:hover{text-decoration:underline}
.sitebar .tag{font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:#D6A33A;
 border:1px solid #4a3a1d;padding:3px 8px;border-radius:4px;white-space:nowrap}
.sitebar .sp{flex:1}
.sitebar .d{color:#8FA0A5}
.sitebar .d b{color:#CBD6D9}
"""

BAR = """
<div class="sitebar"><div class="in">
  <a href="/">&#8592; TerraTrace</a>
  <span class="tag">archived run</span>
  <span class="d">v0.1.0-real &middot; 1000&nbsp;m &middot; result <b>TIE</b></span>
  <span class="sp"></span>
  <a href="/study">Current result: protocol v3 &#8594;</a>
  <a href="https://github.com/pal-123456789/terratrace">Repository</a>
</div></div>
"""


def build(html: str) -> str:
    if OLD_TITLE in html:
        html = html.replace(OLD_TITLE, NEW_TITLE, 1)
    if "</style></head>" in html:
        html = html.replace("</style></head>", CSS + "</style>" + FAVICON + "</head>", 1)
    anchor = '<body><main class="wrap">'
    if anchor in html:
        html = html.replace(anchor, "<body>" + BAR + '<main class="wrap">', 1)
    return html


def main():
    if not SRC.exists():
        raise SystemExit(f"missing {SRC} — run `python -m terratrace.build_viewer` first")
    html = build(SRC.read_text(encoding="utf-8"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO)} ({len(html)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
