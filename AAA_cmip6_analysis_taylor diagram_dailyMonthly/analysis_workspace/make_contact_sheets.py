import argparse
from pathlib import Path

from PIL import Image, ImageDraw


parser = argparse.ArgumentParser()
parser.add_argument("subfolder", nargs="?", default="render_v1")
args = parser.parse_args()
source = Path(__file__).resolve().parent / "output" / args.subfolder
pages = sorted(source.glob("page-*.png"))
thumb_width = 700
margin = 24
label_height = 34
for start in range(0, len(pages), 4):
    batch = pages[start : start + 4]
    thumbs = []
    for page in batch:
        image = Image.open(page).convert("RGB")
        height = round(image.height * thumb_width / image.width)
        thumbs.append((page, image.resize((thumb_width, height), Image.Resampling.LANCZOS)))
    cell_height = max(image.height for _, image in thumbs) + label_height
    sheet = Image.new("RGB", (2 * thumb_width + 3 * margin, 2 * cell_height + 3 * margin), "#d7d7d7")
    draw = ImageDraw.Draw(sheet)
    for offset, (page, image) in enumerate(thumbs):
        row, column = divmod(offset, 2)
        x = margin + column * (thumb_width + margin)
        y = margin + row * (cell_height + margin)
        sheet.paste(image, (x, y + label_height))
        number = int(page.stem.split("-")[-1])
        draw.text((x + 4, y + 5), f"Page {number}", fill="black")
    output = source / f"contact_{start + 1:02d}_{start + len(batch):02d}.png"
    sheet.save(output, optimize=True)
    print(output)
