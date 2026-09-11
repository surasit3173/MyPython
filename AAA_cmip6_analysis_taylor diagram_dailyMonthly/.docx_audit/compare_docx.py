import argparse
import difflib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path


STOP = {
    "the", "a", "an", "and", "or", "of", "to", "in", "for", "with", "was", "were",
    "is", "are", "be", "been", "by", "as", "at", "on", "from", "that", "this", "these",
    "those", "it", "its", "using", "used", "under", "over", "each", "within", "across",
}


def body_paragraphs(doc):
    out = []
    in_refs = False
    for p in doc["paragraphs"]:
        t = p["text"].strip()
        if re.match(r"^(?:\d+\.\s*)?References$", t, re.I):
            in_refs = True
        if in_refs or not t:
            continue
        out.append(p)
    return out


def normalize(s, anonymize=True):
    s = s.lower()
    if anonymize:
        s = re.sub(r"phetchaburi|uttaradit", "province", s)
        s = re.sub(r"\b(?:351|465)\d{3}\b", "stationid", s)
    s = s.replace("−", "-").replace("–", "-").replace("—", "-")
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^a-z0-9%+./<>≥≤=-]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def tokens(s, drop_stop=False):
    ts = re.findall(r"[a-z]+(?:-[a-z0-9]+)*|\d+(?:\.\d+)?|[%+./<>≥≤=-]", normalize(s))
    if drop_stop:
        ts = [t for t in ts if t not in STOP]
    return ts


def jaccard(a, b):
    aa, bb = set(tokens(a, True)), set(tokens(b, True))
    return len(aa & bb) / len(aa | bb) if aa | bb else 0.0


def containment(a, b):
    aa, bb = set(tokens(a, True)), set(tokens(b, True))
    return len(aa & bb) / min(len(aa), len(bb)) if aa and bb else 0.0


def fuzzy_pairs(a_doc, b_doc):
    aa = [p for p in body_paragraphs(a_doc) if len(tokens(p["text"])) >= 12]
    bb = [p for p in body_paragraphs(b_doc) if len(tokens(p["text"])) >= 12]
    pairs = []
    for a in aa:
        na = normalize(a["text"])
        for b in bb:
            nb = normalize(b["text"])
            seq = difflib.SequenceMatcher(None, na, nb, autojunk=False).ratio()
            jac = jaccard(a["text"], b["text"])
            cont = containment(a["text"], b["text"])
            score = max(seq, jac, cont * 0.92)
            if score >= 0.52:
                pairs.append({
                    "a_index": a["index"], "b_index": b["index"],
                    "sequence_ratio": round(seq, 4), "token_jaccard": round(jac, 4),
                    "token_containment": round(cont, 4), "score": round(score, 4),
                    "a_text": a["text"], "b_text": b["text"],
                })
    pairs.sort(key=lambda x: (x["score"], x["sequence_ratio"]), reverse=True)
    return pairs


def ngram_stats(a_doc, b_doc, n=8):
    def doc_tokens(doc):
        parts = [p["text"] for p in body_paragraphs(doc)]
        for table in doc["tables"]:
            for row in table["rows"]:
                parts.extend(row["cells"])
        return tokens(" ".join(parts))
    ta, tb = doc_tokens(a_doc), doc_tokens(b_doc)
    ga = Counter(tuple(ta[i:i+n]) for i in range(max(0, len(ta)-n+1)))
    gb = Counter(tuple(tb[i:i+n]) for i in range(max(0, len(tb)-n+1)))
    common = ga & gb
    shared_instances = sum(common.values())
    return {
        "n": n,
        "a_tokens": len(ta), "b_tokens": len(tb),
        "a_ngrams": sum(ga.values()), "b_ngrams": sum(gb.values()),
        "shared_instances": shared_instances,
        "share_of_smaller": round(shared_instances / min(sum(ga.values()), sum(gb.values())), 4),
        "top_shared": [{"ngram": " ".join(g), "instances": c} for g, c in common.most_common(80)],
    }


def table_similarity(a_doc, b_doc):
    out = []
    for i, ta in enumerate(a_doc["tables"]):
        cells_a = [c for r in ta["rows"] for c in r["cells"]]
        for j, tb in enumerate(b_doc["tables"]):
            cells_b = [c for r in tb["rows"] for c in r["cells"]]
            na = " || ".join(normalize(c) for c in cells_a)
            nb = " || ".join(normalize(c) for c in cells_b)
            seq = difflib.SequenceMatcher(None, na, nb, autojunk=False).ratio()
            jac = jaccard(na, nb)
            out.append({"a_table": i, "b_table": j, "sequence_ratio": round(seq, 4), "token_jaccard": round(jac, 4)})
    out.sort(key=lambda x: max(x["sequence_ratio"], x["token_jaccard"]), reverse=True)
    return out


def heading_like(doc):
    out = []
    for p in doc["paragraphs"]:
        t = p["text"]
        if not t:
            continue
        if "heading" in p["style"].lower() or re.match(r"^\d+(?:\.\d+)*\.?\s+[A-Z]", t) or t.lower() in {"abstract", "keywords", "highlights"}:
            if len(t.split()) <= 12:
                out.append({"index": p["index"], "text": t})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    a = json.loads(Path(args.a).read_text(encoding="utf-8"))
    b = json.loads(Path(args.b).read_text(encoding="utf-8"))
    report = {
        "a": a["path"], "b": b["path"],
        "a_headings": heading_like(a), "b_headings": heading_like(b),
        "ngrams": [ngram_stats(a, b, n) for n in (5, 8, 12, 15)],
        "table_similarity": table_similarity(a, b),
        "fuzzy_paragraph_pairs": fuzzy_pairs(a, b),
    }
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "ngrams": report["ngrams"],
        "top_table_pairs": report["table_similarity"][:8],
        "top_fuzzy_pairs": report["fuzzy_paragraph_pairs"][:20],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
