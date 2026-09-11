from __future__ import annotations

import argparse
import os
from pathlib import Path
import tempfile
import zipfile

from lxml import etree


FONT = "Palatino Linotype"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"


def normalize_xml(name: str, payload: bytes) -> bytes:
    if not name.startswith("word/") or not name.endswith(".xml"):
        return payload
    root = etree.fromstring(payload)

    for r_fonts in root.xpath(".//w:rFonts", namespaces={"w": W}):
        for attr in ("ascii", "hAnsi", "eastAsia", "cs"):
            r_fonts.set(f"{{{W}}}{attr}", FONT)

    if name == "word/theme/theme1.xml":
        for node in root.xpath(
            ".//a:fontScheme/a:majorFont/* | .//a:fontScheme/a:minorFont/*",
            namespaces={"a": A},
        ):
            if "typeface" in node.attrib:
                node.set("typeface", FONT)

    if name == "word/fontTable.xml":
        fonts = root.xpath("./w:font", namespaces={"w": W})
        for node in fonts:
            if node.get(f"{{{W}}}name") != FONT:
                root.remove(node)

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def normalize(in_path: Path, out_path: Path) -> None:
    same_path = in_path.resolve() == out_path.resolve()
    if same_path:
        descriptor, temp_name = tempfile.mkstemp(suffix=".docx", dir=out_path.parent)
        os.close(descriptor)
        target = Path(temp_name)
    else:
        target = out_path
    try:
        with zipfile.ZipFile(in_path, "r") as source, zipfile.ZipFile(target, "w") as output:
            for item in source.infolist():
                payload = normalize_xml(item.filename, source.read(item.filename))
                output.writestr(item, payload)
        if same_path:
            os.replace(target, out_path)
    finally:
        if target.exists() and target != out_path:
            target.unlink()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    normalize(Path(args.input), Path(args.out))
    print(f"normalized DOCX text/theme fonts to {FONT}: {args.out}")


if __name__ == "__main__":
    main()
