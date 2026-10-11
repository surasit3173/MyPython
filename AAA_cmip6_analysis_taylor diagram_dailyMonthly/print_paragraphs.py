import json
import sys
from pathlib import Path


data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
wanted = {int(x) for x in sys.argv[2:]}
for block in data["blocks"]:
    if block["type"] == "p" and block["n"] in wanted:
        print(f"P{block['n']:03d}: {block['text']}")
