from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent


def build(source: Path, pattern: str, output_prefix: str, batch: int, thumb_width: int = 500) -> None:
    paths = sorted(source.glob(pattern), key=lambda path: int(path.stem.split("-")[-1]))
    for start in range(0, len(paths), batch):
        current = paths[start : start + batch]
        thumbs = []
        for path in current:
            image = Image.open(path).convert("RGB")
            height = round(image.height * thumb_width / image.width)
            thumb = image.resize((thumb_width, height), Image.Resampling.LANCZOS)
            thumbs.append((path.name, thumb))
        max_height = max(image.height for _, image in thumbs)
        sheet = Image.new("RGB", (thumb_width * len(thumbs), max_height + 36), "#D0D0D0")
        draw = ImageDraw.Draw(sheet)
        for index, (name, thumb) in enumerate(thumbs):
            x = index * thumb_width
            sheet.paste(thumb, (x, 36))
            draw.text((x + 8, 8), name, fill="black")
        output = ROOT / f"{output_prefix}_{start + 1:02d}-{start + len(current):02d}.png"
        sheet.save(output)


build(ROOT / "render_main", "page-*.png", "contact_main", batch=5)
build(ROOT / "render_supplement", "page-*.png", "contact_supplement", batch=3)
