"""Dữ liệu tiếng Nhật / tiếng Hàn cho TuDien.html (bản Nhật, Hàn, Đa ngữ).

Nguồn (trong _src/):
  jmdict/jmdict-eng-*.json        JMdict (EDRDG, CC BY-SA 4.0) — Nhật→Anh
  kanjidic/kanjidic2-all-*.json   KANJIDIC2 (EDRDG, CC BY-SA 4.0) — âm Hán-Việt, âm Hangul của chữ Hán
  kengdic-master/kengdic.tsv      kengdic (MPL 2.0 / LGPL) — Hàn→Anh, kèm chữ Hán
  stardict-vi-master/ja-vi, ko-vi OVDP (GPLv2) — Nhật→Việt, Hàn→Việt (dịch qua tiếng Anh, chất lượng vừa phải)

Mỗi dòng xuất ra (tách bằng TAB):
  JA: các_dạng_kanji (|) \t các_cách_đọc_kana (|) \t nghĩa_Anh (/) \t nghĩa_Việt (/) \t Hán-Việt \t thông_dụng(1/0)
  KO: hangul \t chữ_Hán (|) \t nghĩa_Anh (/) \t nghĩa_Việt (/) \t Hán-Việt
"""
import glob
import json
import re
import struct
import gzip
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "_src"
VNMARK = re.compile(r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]", re.I)
KANA = re.compile(r"[぀-ヿ]")
HANGUL = re.compile(r"[가-힣]")
HAN = re.compile(r"[㐀-鿿豈-﫿]")


def clean(s: str) -> str:
    # NFC: đổi chữ Hán "tương thích" của tiếng Hàn (U+F900…) về chữ Hán chuẩn → khớp KANJIDIC, không bị lặp
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s).replace("\t", " ").replace("/", "／")).strip()


# ---------------------------------------------------------------- StarDict (OVDP)
def read_stardict(base: Path):
    idx = base.with_suffix(".idx").read_bytes()
    dz = base.parent / (base.name + ".dict.dz")
    raw = gzip.decompress(dz.read_bytes()) if dz.exists() else (base.parent / (base.name + ".dict")).read_bytes()
    out, i = defaultdict(list), 0
    while i < len(idx):
        j = idx.index(b"\0", i)
        w = idx[i:j].decode("utf-8", "replace")
        off, size = struct.unpack(">II", idx[j + 1:j + 9])
        i = j + 9
        out[w].append(raw[off:off + size].decode("utf-8", "replace"))
    return out


def ovdp_vi_senses(defn: str, limit=6):
    """Lấy các nghĩa tiếng Việt từ bài OVDP (bỏ phần {tiếng Anh}, [ghi chú], cách đọc)."""
    out = []
    for ln in defn.split("\n"):
        ln = ln.strip()
        if not ln or ln[0] not in "-=":
            continue
        t = re.sub(r"\{[^}]*\}", " ", ln[1:])
        t = re.sub(r"\[[^\]]*\]", " ", t)
        t = re.sub(r"^[가-힣぀-ヿ㐀-鿿0-9]+\s*", "", t.strip())  # headword lặp lại đầu dòng (ko-vi)
        t = clean(t.strip(" ,;:+"))
        if re.match(r"\(thông tục\) loại a|\(âm nhạc\) la|người giả định thứ nhất", t):
            continue                                     # rác: mạo từ tiếng Anh "a" bị dịch thành chữ cái a
        if t and VNMARK.search(t) and not HANGUL.search(t) and not KANA.search(t):
            out.append(t[:160])
        if len(out) >= limit:
            break
    return out


# ---------------------------------------------------------------- KANJIDIC2
def load_kanjidic():
    path = glob.glob(str(SRC / "kanjidic" / "kanjidic2-all-*.json"))[0]
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    vi, ko = {}, {}
    for ch in data["characters"]:
        rm = ch.get("readingMeaning") or {}
        for grp in rm.get("groups", []):
            for r in grp.get("readings", []):
                if r["type"] == "vietnam" and ch["literal"] not in vi:
                    vi[ch["literal"]] = r["value"].lower()
                if r["type"] == "korean_h" and ch["literal"] not in ko:
                    ko[ch["literal"]] = r["value"]
    return vi, ko


def hv_of(text: str, kvi: dict) -> str:
    """Âm Hán-Việt cho chữ Hán (bỏ qua kana/hangul); '' nếu thiếu quá nửa."""
    chars = [c for c in text if HAN.match(c)]
    if not chars:
        return ""
    out = [kvi.get(c, "?") for c in chars]
    return "" if out.count("?") * 2 > len(out) else " ".join(out)


# ---------------------------------------------------------------- Japanese
def build_ja(kvi):
    path = glob.glob(str(SRC / "jmdict" / "jmdict-eng-*.json"))[0]
    words = json.loads(Path(path).read_text(encoding="utf-8"))["words"]
    javi = read_stardict(SRC / "stardict-vi-master" / "ja-vi" / "star_nhatviet")
    lines = []
    for w in words:
        kanji = [k["text"] for k in w["kanji"]][:4]
        kana = [k["text"] for k in w["kana"]][:4]
        common = any(k.get("common") for k in w["kanji"] + w["kana"])
        senses = []
        for s in w["sense"][:8]:
            g = "; ".join(x["text"] for x in s["gloss"][:5])
            if g:
                senses.append(clean(g))
        vi = []
        for key in kanji + kana:
            if key in javi:
                for d in javi[key]:
                    if d.lstrip().startswith("@"):        # bài Nhật-Việt soạn tay
                        vi += ovdp_vi_senses(d)
                    elif common:                         # bài dịch vòng qua tiếng Anh: chỉ từ thông dụng, ít nghĩa
                        vi += ovdp_vi_senses(d, limit=3)
                if vi:
                    break
        hv = hv_of(kanji[0], kvi) if kanji else ""
        lines.append("\t".join(["|".join(kanji), "|".join(kana), "/".join(senses), "/".join(vi[:6]), hv, "1" if common else "0"]))
    # thông dụng lên trước để khi trùng dạng chữ, mục thông dụng được ưu tiên
    lines.sort(key=lambda l: l.endswith("\t0"))
    return lines


# ---------------------------------------------------------------- Korean
def build_ko(kvi):
    ken = defaultdict(lambda: {"hanja": [], "en": []})
    with open(SRC / "kengdic-master" / "kengdic.tsv", encoding="utf-8") as f:
        next(f)
        for ln in f:
            p = ln.rstrip("\n").split("\t")
            if len(p) < 4:
                continue
            surf, hanja, gloss = clean(p[1]), clean(p[2]), clean(p[3])
            if not surf or not HANGUL.search(surf):
                continue
            e = ken[surf]
            for hj in re.split(r"[,，;/ ]+", hanja):
                if hj and HAN.search(hj) and hj not in e["hanja"]:
                    e["hanja"].append(hj)
            if gloss and gloss not in e["en"]:
                e["en"].append(gloss)
    kovi = read_stardict(SRC / "stardict-vi-master" / "ko-vi" / "star_hanviet")
    for head, defs in kovi.items():
        surf = clean(head)
        if not HANGUL.search(surf):
            continue
        e = ken[surf]
        for d in defs:
            e.setdefault("vi", [])
            e["vi"] += ovdp_vi_senses(d)
            for hj in re.findall(r"\[([㐀-鿿豈-﫿]+)]", unicodedata.normalize("NFC", d)):
                if hj not in e["hanja"]:
                    e["hanja"].append(hj)
            if not e["en"]:  # tiếng Anh trong {…} của OVDP khi kengdic không có
                e["en"] += [clean(x) for x in re.findall(r"\{([^}]+)\}", d)[:4]]
    lines = []
    for surf, e in ken.items():
        if not e["en"] and not e.get("vi"):
            continue
        hv = " / ".join(filter(None, (hv_of(h, kvi) for h in e["hanja"][:3])))
        lines.append("\t".join([surf, "|".join(e["hanja"][:4]), "/".join(e["en"][:8]),
                                "/".join(dict.fromkeys(e.get("vi", [])))[:600].rstrip("/"), hv]))
    return lines


# ---------------------------------------------------------------- glossary translations
def load_jako_translations():
    """zh -> (danh sách tiếng Nhật, danh sách tiếng Hàn) từ data/dich-ja-ko*.tsv."""
    tr = {}
    for f in sorted((ROOT / "data").glob("dich-ja-ko*.tsv")):
        for ln in f.read_text(encoding="utf-8").splitlines():
            if not ln.strip() or ln.startswith("#"):
                continue
            p = ln.split("\t")
            if len(p) < 3:
                print("  ! dòng dịch Nhật/Hàn thiếu cột:", ln)
                continue
            zh = p[0].strip()
            ja = [x.strip() for x in p[1].split(" / ") if x.strip()]
            ko = [x.strip() for x in p[2].split(" / ") if x.strip()]
            if zh in tr:
                print(f"  ! trùng bản dịch Nhật/Hàn cho {zh} — giữ bản đầu")
                continue
            tr[zh] = (ja, ko)
    return tr


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    kvi, _ = load_kanjidic()
    ja = build_ja(kvi)
    ko = build_ko(kvi)
    print("JA", len(ja), "dòng,", sum(len(l) for l in ja) / 1e6, "MB;", "KO", len(ko), "dòng,", sum(len(l) for l in ko) / 1e6, "MB")
    for l in ja:
        if l.startswith("治具") or l.startswith("検査") or l.startswith("真空|"):
            print(" ", l[:300])
    for l in ko:
        if l.split("\t")[0] in ("실린더", "검사", "나사", "지그", "원점"):
            print(" ", l[:300])
    print("dịch Nhật/Hàn:", len(load_jako_translations()))
