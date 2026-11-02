"""
visualization/build_project_screen.py

Embeds results/dashboard_data.json (real experiment output) into
visualization/project_screen.html and writes:

  results/origen_project_screen.html  fragment form (used for the Claude artifact)
  docs/index.html                     standalone page for GitHub Pages (full HTML skeleton)

    python3 visualization/build_project_screen.py
"""
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
tpl = open(os.path.join(ROOT, "visualization", "project_screen.html"), encoding="utf-8").read()
data = open(os.path.join(ROOT, "results", "dashboard_data.json"), encoding="utf-8").read()
assert "__DATA__" in tpl
json.loads(data.replace("NaN", "null"))  # sanity: the data parses
fragment = tpl.replace("__DATA__", data)

out = os.path.join(ROOT, "results", "origen_project_screen.html")
open(out, "w", encoding="utf-8").write(fragment)
print("wrote", out, f"({len(fragment)/1024:.0f} KB)")

# Standalone page: everything before the first layout element goes in <head>.
split = fragment.index('<div class="wrap">')
head, body = fragment[:split], fragment[split:]
standalone = (
    "<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
    "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
    "<meta name=\"description\" content=\"ORIGEN: topology-constrained search for inverse origami crease patterns. Research prototype.\">\n"
    + head +
    "<style>html{-webkit-text-size-adjust:100%}body{margin:0}[hidden]{display:none!important}</style>\n"
    "</head>\n<body>\n" + body + "\n</body>\n</html>\n"
)
docs = os.path.join(ROOT, "docs")
os.makedirs(docs, exist_ok=True)
path = os.path.join(docs, "index.html")
open(path, "w", encoding="utf-8").write(standalone)
open(os.path.join(docs, ".nojekyll"), "w").close()
print("wrote", path, f"({len(standalone)/1024:.0f} KB)")
