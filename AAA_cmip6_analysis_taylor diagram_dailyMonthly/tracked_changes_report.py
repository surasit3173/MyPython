from pathlib import Path
import re, zipfile

docx_path = Path(r"D:\วารสารบูรพา\Evaluation of Quantile Delta Mapping for Bias Correction of CMIP6 Daily Rainfall Using Independent Temporal Holdout.docx")

with zipfile.ZipFile(docx_path) as z:
    for name in z.namelist():
        if not name.startswith("word/") or not name.endswith(".xml"):
            continue
        data = z.read(name).decode("utf-8", errors="ignore")
        ins = len(re.findall(r"<w:ins\b", data))
        dele = len(re.findall(r"<w:del\b", data))
        if ins or dele:
            print(f"{name}\tins={ins}\tdel={dele}")
            for tag in ["ins", "del"]:
                for m in re.finditer(fr"<w:{tag}\b.*?</w:{tag}>", data, flags=re.S):
                    text = " ".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", m.group(0), flags=re.S))
                    text = re.sub(r"\s+", " ", text)
                    print(f"  {tag}: {text[:220]}")
                    break
