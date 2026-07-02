"""Generate docs/api.md from the running FastAPI app's OpenAPI schema.

Usage: python3 scripts/gen_api_docs.py [base_url]

Default base_url is http://localhost:8765.
"""
import sys
import json
import urllib.request

base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765"

with urllib.request.urlopen(f"{base}/openapi.json") as r:
    spec = json.load(r)

lines = [f"# {spec['info']['title']} — API Reference", ""]
lines.append(f"**Version:** {spec['info']['version']}")
lines.append("")
if spec["info"].get("description"):
    lines.append(spec["info"]["description"])
lines.append("")
lines.append(f"_Auto-generated from `/openapi.json` — regenerate with `python3 scripts/gen_api_docs.py`._")
lines.append("")
lines.append("## Endpoints")
lines.append("")

# Group by tag
by_tag = {}
for path, methods in spec["paths"].items():
    for method, op in methods.items():
        tag = (op.get("tags") or ["default"])[0]
        by_tag.setdefault(tag, []).append((method, path, op))

for tag, entries in by_tag.items():
    lines.append(f"### `{tag}`")
    lines.append("")
    for method, path, op in entries:
        lines.append(f"#### `{method.upper()} {path}`")
        lines.append("")
        if op.get("summary"):
            lines.append(f"_{op['summary']}_")
            lines.append("")
        if op.get("description"):
            lines.append(op["description"])
            lines.append("")
        # Parameters
        for param in op.get("parameters", []):
            req = "required" if param.get("required") else "optional"
            schema = param.get("schema", {})
            t = schema.get("type", "any")
            lines.append(f"- `{param['name']}` ({t}, {req}) — {param.get('description', '')}")
        # Request body
        rb = op.get("requestBody")
        if rb:
            content = rb.get("content", {}).get("application/json", {})
            ref = content.get("schema", {}).get("$ref", "")
            if ref:
                model = ref.split("/")[-1]
                lines.append(f"- **Body** (application/json): `{model}` schema")
            else:
                lines.append("- **Body** (application/json)")
        lines.append("")

# Schemas
if spec.get("components", {}).get("schemas"):
    lines.append("## Schemas")
    lines.append("")
    for name, schema in spec["components"]["schemas"].items():
        lines.append(f"### `{name}`")
        lines.append("")
        for field, info in schema.get("properties", {}).items():
            t = info.get("type", "")
            if "$ref" in info:
                t = info["$ref"].split("/")[-1]
            desc = info.get("description", "")
            req = field in schema.get("required", [])
            lines.append(f"- `{field}` ({t}{', required' if req else ''}) — {desc}")
        lines.append("")

with open("docs/api.md", "w") as f:
    f.write("\n".join(lines))
print("wrote docs/api.md")
