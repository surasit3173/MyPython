from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir")
    parser.add_argument("output_dir")
    parser.add_argument("--prefix", default="contact")
    parser.add_argument("--pages-per-sheet", type=int, default=6)
    args = parser.parse_args()

    src = Path(args.input_dir)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    pages = sorted(src.glob("page-*.png"))
    if not pages:
        raise SystemExit(f"No rendered pages found under {src}")

    cols = 2
    thumb_w, thumb_h = 720, 980
    label_h, gutter = 34, 20
    rows = math.ceil(args.pages_per_sheet / cols)
    for batch_i in range(0, len(pages), args.pages_per_sheet):
        batch = pages[batch_i : batch_i + args.pages_per_sheet]
        canvas = Image.new(
            "RGB",
            (cols * thumb_w + (cols + 1) * gutter,
             rows * (thumb_h + label_h) + (rows + 1) * gutter),
            "#d9d9d9",
        )
        draw = ImageDraw.Draw(canvas)
        for i, path in enumerate(batch):
            image = Image.open(path).convert("RGB")
            image.thumbnail((thumb_w, thumb_h))
            cell_x = gutter + (i % cols) * (thumb_w + gutter)
            cell_y = gutter + (i // cols) * (thumb_h + label_h + gutter)
            x = cell_x + (thumb_w - image.width) // 2
            y = cell_y + label_h + (thumb_h - image.height) // 2
            canvas.paste(image, (x, y))
            draw.text((cell_x + 8, cell_y + 7), path.stem, fill="black")
        target = out / f"{args.prefix}-{batch_i // args.pages_per_sheet + 1}.jpg"
        canvas.save(target, quality=88)
        print(target)


if __name__ == "__main__":
    main()
