from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


SRC = Path(r"C:\MyPython\AAA_cmip6_analysis_taylor diagram_dailyMonthly\rendered_publication_word")
OUT = Path(r"C:\MyPython\AAA_cmip6_analysis_taylor diagram_dailyMonthly\rendered_publication_contact")
OUT.mkdir(exist_ok=True)

files = sorted(SRC.glob("page-*.png"))
thumb_w = 420
pad = 28
label_h = 34
cols = 3
rows = 2
per_sheet = cols * rows

for sheet_i in range(0, len(files), per_sheet):
    batch = files[sheet_i : sheet_i + per_sheet]
    thumbs = []
    for f in batch:
        img = Image.open(f).convert("RGB")
        ratio = thumb_w / img.width
        thumb = img.resize((thumb_w, int(img.height * ratio)))
        thumbs.append((f, thumb))
    cell_h = max(t.height for _, t in thumbs) + label_h
    sheet = Image.new("RGB", (cols * thumb_w + (cols + 1) * pad, rows * cell_h + (rows + 1) * pad), "white")
    draw = ImageDraw.Draw(sheet)
    for j, (f, thumb) in enumerate(thumbs):
        r = j // cols
        c = j % cols
        x = pad + c * (thumb_w + pad)
        y = pad + r * (cell_h + pad)
        page_num = f.stem.split("-")[-1]
        draw.text((x, y), f"Page {int(page_num)}", fill="black")
        sheet.paste(thumb, (x, y + label_h))
    out = OUT / f"contact_{sheet_i // per_sheet + 1:02d}.png"
    sheet.save(out)
    print(out)
