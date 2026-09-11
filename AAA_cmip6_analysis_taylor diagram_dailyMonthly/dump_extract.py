import json
import sys
from pathlib import Path


data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(data["file"])
print(f"paragraphs={data['paragraphs']} tables={data['tables']} images={data['images']}")
for block in data["blocks"]:
    if block["type"] == "p":
        print(f"P{block['n']:03d} [{block.get('style','')}] {block['text']}")
    else:
        print(f"TABLE {block['n']} rows={len(block['rows'])} cols={len(block['rows'][0]) if block['rows'] else 0}")
        for row in block["rows"]:
            print(" | ".join(row))
