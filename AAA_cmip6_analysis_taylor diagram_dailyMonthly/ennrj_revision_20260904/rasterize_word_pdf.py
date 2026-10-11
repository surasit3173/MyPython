import argparse,importlib.util
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('docx');p.add_argument('pdf');p.add_argument('out');a=p.parse_args()
renderer=Path(r'C:\Users\PC\.codex\plugins\cache\openai-primary-runtime\documents\26.903.11726\skills\documents\render_docx.py')
spec=importlib.util.spec_from_file_location('official_docx_renderer',renderer);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
pdf=Path(a.pdf).resolve()
assert pdf.is_file() and pdf.stat().st_size>1000
mod.convert_to_pdf=lambda *args,**kwargs:(str(pdf),'Microsoft Word read-only PDF export used; LibreOffice unavailable')
paths=mod.rasterize(str(Path(a.docx).resolve()),str(Path(a.out).resolve()),150,False,False)
print('PAGES',len(paths),'OUTPUT',str(Path(a.out).resolve()))
