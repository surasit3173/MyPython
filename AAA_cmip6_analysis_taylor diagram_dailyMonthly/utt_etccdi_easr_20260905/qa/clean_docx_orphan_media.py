"""Remove image parts and relationships that no Word XML part references."""
from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"
RID_RE = re.compile(rb"\br:(?:embed|link|id)=['\"](rId\d+)['\"]")


def source_part(rel_part: str) -> str:
    # word/_rels/document.xml.rels -> word/document.xml
    directory, filename = rel_part.rsplit("/", 1)
    return directory.rsplit("/_rels", 1)[0] + "/" + filename[:-5]


def main(path_arg: str) -> None:
    path = Path(path_arg)
    temp = path.with_suffix(".cleaning.docx")
    with zipfile.ZipFile(path) as zin:
        payload = {name: zin.read(name) for name in zin.namelist()}
    used_media: set[str] = set()
    rewritten: dict[str, bytes] = {}
    removed_relationships = 0
    for rel_part, rel_bytes in payload.items():
        if not (rel_part.startswith("word/_rels/") and rel_part.endswith(".rels")):
            continue
        src = source_part(rel_part)
        refs = set(RID_RE.findall(payload.get(src, b"")))
        root = ET.fromstring(rel_bytes)
        for rel in list(root):
            target = rel.attrib.get("Target", "")
            rid = rel.attrib.get("Id", "").encode()
            rel_type = rel.attrib.get("Type", "")
            is_media = rel_type.endswith("/image") and target.startswith("media/")
            if is_media and rid not in refs:
                root.remove(rel)
                removed_relationships += 1
            elif is_media:
                used_media.add("word/" + target)
        rewritten[rel_part] = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    orphan_media = {name for name in payload if name.startswith("word/media/")} - used_media
    with zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in payload.items():
            if name in orphan_media:
                continue
            zout.writestr(name, rewritten.get(name, data))
    temp.replace(path)
    print(f"DOCX_MEDIA_CLEANED removed_media={len(orphan_media)} removed_relationships={removed_relationships} retained_media={len(used_media)}")


if __name__ == "__main__":
    main(sys.argv[1])
