#!/usr/bin/env python3
"""Inject the shared instructions template and options into the onboarding page."""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
src = (ROOT / "page/src.html").read_text(encoding="utf-8")
tpl = (ROOT / "templates/instructions.md").read_text(encoding="utf-8")
opts = json.loads((ROOT / "templates/options.json").read_text(encoding="utf-8"))
out = src.replace("__TEMPLATE_JSON__", json.dumps(tpl)).replace("__OPTIONS_JSON__", json.dumps(opts))
assert "__TEMPLATE_JSON__" not in out and "__OPTIONS_JSON__" not in out
(ROOT / "page/decision-council.html").write_text(out, encoding="utf-8")
print("page/decision-council.html", len(out), "bytes")
# local preview copy with the skeleton the artifact host adds (not published)
(ROOT / "page/_preview.html").write_text('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"></head><body style="margin:0">' + out + "</body></html>", encoding="utf-8")
