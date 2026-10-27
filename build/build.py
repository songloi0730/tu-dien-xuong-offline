"""Build bộ Từ điển offline: StarDict cho GoldenDict-ng + dữ liệu nhúng cho TuDien.html.

Chạy:  python build/build.py
Đầu vào: _src/ (CVDICT.u8, cedict_ts.u8, stardict-vi-master/, hanviet-pinyin-wordlist-main/),
         data/thuat-ngu-xuong.tsv, build/template.html
Đầu ra:  dist/TuDienOffline/GoldenDict/content/*  và  dist/TuDienOffline/TuDien.html
"""
import base64
import sys as _sys
_sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import gzip
import html
import json
import re
import shutil
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "_src"
DIST = ROOT / "dist" / "TuDienOffline"
CONTENT = DIST / "GoldenDict" / "content"

sys.stdout.reconfigure(encoding="utf-8")

# ---------------------------------------------------------------- pinyin
TONE_MARKS = {
    "a": "āáǎàa", "e": "ēéěèe", "i": "īíǐìi", "o": "ōóǒòo", "u": "ūúǔùu", "ü": "ǖǘǚǜü",
}


def syllable_to_marks(syl: str) -> str:
    m = re.fullmatch(r"([A-Za-zü:]+)([1-5])", syl)
    if not m:
        return syl.replace("u:", "ü")
    body, tone = m.group(1).replace("u:", "ü").replace("U:", "Ü"), int(m.group(2))
    low = body.lower()
    if "a" in low:
        idx = low.index("a")
    elif "e" in low:
        idx = low.index("e")
    elif "ou" in low:
        idx = low.index("o")
    else:
        idx = max((i for i, ch in enumerate(low) if ch in "aeiouü"), default=-1)
    if idx < 0:
        return body
    ch = low[idx]
    marked = TONE_MARKS[ch][tone - 1]
    if body[idx].isupper():
        marked = marked.upper()
    return body[:idx] + marked + body[idx + 1:]


def pinyin_marks(py: str) -> str:
    return " ".join(syllable_to_marks(s) for s in py.split())


def pinyin_plain(py: str) -> str:
    return re.sub(r"[1-5]", "", py.replace("u:", "v")).replace(" ", "").lower()


# ---------------------------------------------------------------- Hán-Việt
def load_hanviet():
    table = defaultdict(dict)  # trad char -> {pinyin|'*': [readings]}
    path = SRC / "hanviet-pinyin-wordlist-main" / "hanviet.csv"
    import csv
    with open(path, encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        for ch, hv, py in r:
            readings = [x.strip().strip("'\"") for x in hv.strip("[]").split(",") if x.strip()]
            if readings:
                table[ch][py.lower()] = readings
    return table


HV = None


def hanviet_of(trad: str, py: str) -> str:
    """Âm Hán-Việt cho từng chữ (theo pinyin nếu có). Trả '' nếu thiếu quá nửa."""
    sylls = py.split()
    if len(sylls) != len(trad):
        sylls = [None] * len(trad)
    out, miss = [], 0
    for ch, s in zip(trad, sylls):
        d = HV.get(ch)
        if not d or not ch.strip():
            out.append("?")
            miss += 1
            continue
        reading = (d.get(s.lower()) if s else None) or d.get("*")
        if not reading and s:  # cùng âm khác thanh
            base = re.sub(r"[1-5]", "", s.lower())
            reading = next((v for k, v in d.items() if re.sub(r"[1-5]", "", k) == base), None)
        if not reading:
            reading = next(iter(d.values()))
        out.append(reading[0])
    if miss * 2 > len(trad):
        return ""
    return " ".join(out)


# ---------------------------------------------------------------- CC-CEDICT format
LINE_RE = re.compile(r"^(\S+) (\S+) \[([^\]]*)\] /(.*)/\s*$")


def load_cedict(path: Path):
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                continue
            m = LINE_RE.match(line.rstrip("\n"))
            if m:
                trad, simp, py, defs = m.groups()
                entries.append((trad, simp, py, [d for d in defs.split("/") if d]))
    return entries


def build_trad_map(entries):
    cnt = defaultdict(Counter)
    for trad, simp, _, _ in entries:
        if len(trad) == len(simp):
            for t, s in zip(trad, simp):
                cnt[s][t] += 1
    return {s: c.most_common(1)[0][0] for s, c in cnt.items()}


# ---------------------------------------------------------------- StarDict writer
def stardict_key(word: str):
    b = word.encode("utf-8")
    return (b.lower(), b)


def write_stardict(name: str, bookname: str, entries, description: str):
    """entries: list of (headwords:list[str], html:str). Headword đầu là chính, còn lại vào .syn."""
    folder = CONTENT / name
    folder.mkdir(parents=True, exist_ok=True)
    data = bytearray()
    main = []  # (word, off, size)
    syns = []  # (word, entry_ordinal_placeholder -> resolved later)
    for heads, body in entries:
        b = body.encode("utf-8")
        off = len(data)
        data += b
        main.append((heads[0], off, len(b)))
        syns.append(heads[1:])
    order = sorted(range(len(main)), key=lambda i: stardict_key(main[i][0]))
    pos = {orig: new for new, orig in enumerate(order)}
    idx = bytearray()
    for i in order:
        w, off, size = main[i]
        idx += w.encode("utf-8") + b"\0" + struct.pack(">II", off, size)
    syn_list = []
    for i, alts in enumerate(syns):
        seen = {main[i][0]}
        for a in alts:
            if a and a not in seen:
                seen.add(a)
                syn_list.append((a, pos[i]))
    syn_list.sort(key=lambda x: stardict_key(x[0]))
    syn = bytearray()
    for w, p in syn_list:
        syn += w.encode("utf-8") + b"\0" + struct.pack(">I", p)
    (folder / f"{name}.dict").write_bytes(bytes(data))
    (folder / f"{name}.idx").write_bytes(bytes(idx))
    if syn_list:
        (folder / f"{name}.syn").write_bytes(bytes(syn))
    ifo = [
        "StarDict's dict ifo file",
        "version=3.0.0",
        f"wordcount={len(main)}",
        f"idxfilesize={len(idx)}",
        f"bookname={bookname}",
        "sametypesequence=h",
        f"description={description}",
    ]
    if syn_list:
        ifo.insert(3, f"synwordcount={len(syn_list)}")
    (folder / f"{name}.ifo").write_text("\n".join(ifo) + "\n", encoding="utf-8")
    print(f"  {name}: {len(main)} mục, {len(syn_list)} từ đồng dạng")


def esc(s: str) -> str:
    return html.escape(s, quote=False)


def zh_header(simp, trad, py, hv):
    head = f'<b style="font-size:130%">{esc(simp)}</b>'
    if trad != simp:
        head += f' <span style="color:#888">({esc(trad)})</span>'
    head += f' <span style="color:#c0392b">{esc(pinyin_marks(py))}</span>'
    if hv:
        head += f' <span style="color:#2471a3">[Hán-Việt: {esc(hv)}]</span>'
    return head


def zh_heads(simp, trad, py):
    p = pinyin_plain(py)
    return [simp, trad, p] if p.isascii() else [simp, trad]


# ---------------------------------------------------------------- glossary
def auto_pinyin(simp, py_by_simp):
    """Pinyin cho thuật ngữ nhập tay để trống cột pinyin: lấy cả từ nếu CC-CEDICT có, không thì ghép từng chữ."""
    out, i = [], 0
    while i < len(simp):  # tách theo từ dài nhất có trong CC-CEDICT để chữ đa âm đọc đúng (调整 = tiao2 zheng3)
        for j in range(min(len(simp), i + 8), i, -1):
            if simp[i:j] in py_by_simp:
                out.append(py_by_simp[simp[i:j]])
                i = j
                break
        else:
            out.append(simp[i])
            i += 1
    return " ".join(out)


def load_glossary(trad_map, cedict_by_simp, py_by_simp):
    rows, seen = [], {}
    files = sorted((ROOT / "data").glob("thuat-ngu-*.tsv"), key=lambda p: p.name != "thuat-ngu-xuong.tsv")
    lines = [(f.name, ln) for f in files for ln in f.read_text(encoding="utf-8").splitlines()]
    for fname, line in lines:
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            print("  ! dòng thuật ngữ thiếu cột:", line)
            continue
        simp, py, vi, en = (x.strip() for x in parts[:4])
        group = parts[4].strip() if len(parts) > 4 else ""
        if not py:
            py = auto_pinyin(simp, py_by_simp)
        if simp in seen:
            print(f"  ! trùng thuật ngữ {simp} ({seen[simp]} và {fname}) — giữ bản đầu")
            continue
        seen[simp] = fname
        known = cedict_by_simp.get(simp)
        trad = known if known else "".join(trad_map.get(c, c) for c in simp)
        rows.append({"s": simp, "t": trad, "p": py, "vi": vi, "en": en, "g": group})
    return rows


# ---------------------------------------------------------------- OVDP StarDict reader
def read_stardict(base: Path):
    idx = base.with_suffix(".idx").read_bytes()
    dz = base.parent / (base.name + ".dict.dz")
    raw = gzip.decompress(dz.read_bytes()) if dz.exists() else (base.parent / (base.name + ".dict")).read_bytes()
    out, i = [], 0
    while i < len(idx):
        j = idx.index(b"\0", i)
        w = idx[i:j].decode("utf-8", "replace")
        off, size = struct.unpack(">II", idx[j + 1:j + 9])
        i = j + 9
        out.append((w, raw[off:off + size].decode("utf-8", "replace")))
    return out


def pack(text: str) -> str:
    return base64.b64encode(gzip.compress(text.encode("utf-8"), 9)).decode("ascii")


# ---------------------------------------------------------------- main
def main():
    global HV
    print("Đọc dữ liệu…")
    HV = load_hanviet()
    cv = load_cedict(SRC / "CVDICT.u8")
    ce = load_cedict(SRC / "cedict_ts.u8")
    print(f"  CVDICT {len(cv)} mục, CC-CEDICT {len(ce)} mục")
    trad_map = build_trad_map(ce)
    cedict_by_simp, py_by_simp = {}, {}
    for trad, simp, py, defs in ce:
        cedict_by_simp.setdefault(simp, trad)
        # ưu tiên âm đọc thường (chữ thường), bỏ tên riêng / biến thể
        if not re.search(r"[A-Z]", py) and not re.match(r"(surname|old variant|variant of)", defs[0] if defs else ""):
            py_by_simp.setdefault(simp, py)
    gloss = load_glossary(trad_map, cedict_by_simp, py_by_simp)
    print(f"  Thuật ngữ xưởng: {len(gloss)} mục")

    # ---- GoldenDict
    if CONTENT.exists():
        for p in CONTENT.iterdir():
            if p.is_dir() and p.name.startswith(("1_", "2_", "3_", "4_", "5_", "6_", "7_")):
                # chỉ xóa file, giữ thư mục (OneDrive hay khóa thư mục khi đang đồng bộ)
                for f in p.iterdir():
                    if f.is_file():
                        f.unlink()
    CONTENT.mkdir(parents=True, exist_ok=True)
    print("Ghi StarDict…")

    # Từ điển chung theo chữ giản thể (ưu tiên âm đọc thường) — dùng để giải nghĩa thành phần của thuật ngữ ghép
    gen = {}
    vi_by_key = {(t, s, p.lower()): d for t, s, p, d in cv}
    for trad, simp, py, defs in ce:
        if re.search(r"[A-Z]", py) or re.match(r"(surname|old variant|variant of)", defs[0] if defs else ""):
            continue
        gen.setdefault(simp, (py, vi_by_key.get((trad, simp, py.lower()), []), defs, trad))

    def parts_html(simp):
        """Tách thuật ngữ ghép theo từ điển chung (từ dài nhất) và giải nghĩa từng phần."""
        out, i = [], 0
        while i < len(simp):
            for j in range(min(len(simp), i + 8), i, -1):
                if j - i < len(simp) and simp[i:j] in gen:
                    out.append(simp[i:j]); i = j
                    break
            else:
                out.append(simp[i]); i += 1
        if len(out) < 2:
            return ""
        h = '<hr><span style="color:#888">Từ điển chung — theo từng thành phần:</span>'
        for p in out:
            if p not in gen:
                h += f"<br><b>{esc(p)}</b>"
                continue
            py, vi, en, trad = gen[p]
            hv = hanviet_of(trad, py)
            h += (f'<br><b>{esc(p)}</b> <span style="color:#c0392b">{esc(pinyin_marks(py))}</span>'
                  + (f' <span style="color:#2471a3">[{esc(hv)}]</span>' if hv else "")
                  + (f' — VI: {esc("; ".join(vi[:3]))}' if vi else "")
                  + (f' · EN: {esc("; ".join(en[:3]))}' if en else ""))
        return h

    g_entries = []
    for r in gloss:
        hv = hanviet_of(r["t"], r["p"])
        body = (zh_header(r["s"], r["t"], r["p"], hv)
                + f'<br><span style="color:#888">VI:</span> <b>{esc(r["vi"])}</b>'
                + f'<br><span style="color:#888">EN:</span> {esc(r["en"])}'
                + (f'<br><span style="color:#888">Nhóm: {esc(r["g"])}</span>' if r["g"] else "")
                + (parts_html(r["s"]) if r["s"] not in gen else ""))
        heads = zh_heads(r["s"], r["t"], r["p"])
        heads += [e.strip() for e in re.split(r"[,;]", r["en"]) if e.strip()]
        g_entries.append((heads, body))
    write_stardict("1_ThuatNguXuong", "① Thuật ngữ xưởng (Trung-Việt-Anh)", g_entries,
                   "Bộ thuật ngữ nhà máy tự soạn. Sửa data/thuat-ngu-xuong.tsv rồi chạy lại build.")

    def cedict_entries(entries):
        out = []
        for trad, simp, py, defs in entries:
            hv = hanviet_of(trad, py)
            body = zh_header(simp, trad, py, hv) + "<ol>" + "".join(f"<li>{esc(d)}</li>" for d in defs) + "</ol>"
            out.append((zh_heads(simp, trad, py), body))
        return out

    write_stardict("2_CVDICT_TrungViet", "② CVDICT Trung-Việt", cedict_entries(cv),
                   "CVDICT (c) Phong Phan, CC BY-SA 4.0 — https://github.com/ph0ngp/CVDICT. Dịch máy từ CC-CEDICT, có thể còn lỗi.")
    write_stardict("3_CCCEDICT_TrungAnh", "③ CC-CEDICT Trung-Anh", cedict_entries(ce),
                   "CC-CEDICT, CC BY-SA 4.0 — https://www.mdbg.net/chinese/dictionary?page=cc-cedict")

    ovdp = SRC / "stardict-vi-master"
    for sub, name in [("en-vi", "4_OVDP_AnhViet"), ("vi-en", "5_OVDP_VietAnh"), ("zh-vi", "6_OVDP_TrungViet_thamkhao")]:
        dst = CONTENT / name
        dst.mkdir(exist_ok=True)
        for f in (ovdp / sub).iterdir():
            target = dst / f.name
            if f.suffix == ".ifo":
                txt = f.read_text(encoding="utf-8")
                if sub == "zh-vi":
                    txt = txt.replace("bookname=Từ điển Trung-Việt", "bookname=⑥ OVDP Trung-Việt (dịch qua tiếng Anh, chỉ tham khảo)")
                elif sub == "en-vi":
                    txt = txt.replace("bookname=Từ điển Anh-Việt", "bookname=④ OVDP Anh-Việt")
                else:
                    txt = txt.replace("bookname=Từ điển Việt-Anh", "bookname=⑤ OVDP Việt-Anh")
                target.write_text(txt, encoding="utf-8")
            else:
                shutil.copy2(f, target)
        print(f"  {name}: chép từ OVDP")

    # ---- HTML data
    print("Đóng gói dữ liệu cho TuDien.html…")
    merged = {}
    for trad, simp, py, defs in ce:
        merged.setdefault((trad, simp, py), [trad, simp, py, "", ""])[4] = "/".join(defs)
    for trad, simp, py, defs in cv:
        merged.setdefault((trad, simp, py), [trad, simp, py, "", ""])[3] = "/".join(defs)
    zh_lines = []
    for trad, simp, py, vi, en in merged.values():
        hv = hanviet_of(trad, py)
        zh_lines.append("\t".join([simp, trad, py, hv, vi.replace("\t", " "), en.replace("\t", " ")]))
    print(f"  Trung: {len(zh_lines)} mục gộp")

    def flat(defn: str) -> str:
        return defn.replace("\\", "\\\\").replace("\t", " ").replace("\r", "").replace("\n", "\\n")

    envi = read_stardict(ovdp / "en-vi" / "star_anhviet")
    vien = read_stardict(ovdp / "vi-en" / "star_vietanh")
    en_text = "\n".join(f"{w}\t{flat(d)}" for w, d in envi)
    vi_text = "\n".join(f"{w}\t{flat(d)}" for w, d in vien)
    print(f"  Anh-Việt {len(envi)} mục, Việt-Anh {len(vien)} mục")

    # ---- Nhật / Hàn
    print("Dữ liệu tiếng Nhật / tiếng Hàn…")
    import build_jako as jk
    kvi, _ = jk.load_kanjidic()
    ja_lines = jk.build_ja(kvi)
    ko_lines = jk.build_ko(kvi)
    tr = jk.load_jako_translations()
    n_tr = 0
    for r in gloss:
        ja, ko = tr.get(r["s"], ([], []))
        if ja or ko:
            n_tr += 1
        r["j"], r["k"] = ja, ko
    print(f"  Nhật {len(ja_lines)} mục, Hàn {len(ko_lines)} mục; thuật ngữ có bản dịch Nhật/Hàn: {n_tr}/{len(gloss)}")

    blobs = {
        "zh": pack("\n".join(zh_lines)),
        "ja": pack("\n".join(ja_lines)),
        "ko": pack("\n".join(ko_lines)),
        "en": pack(en_text),
        "vi": pack(vi_text),
        "gl": pack(json.dumps(gloss, ensure_ascii=False)),
    }
    for k, v in blobs.items():
        print(f"  {k}: {len(v) / 1e6:.1f} MB base64")
    # Phiên bản: v{lớn}.{nhỏ}.{ngày build YYMMDD} — số lớn/nhỏ trong file VERSION (chỉ đổi khi chủ dự án yêu cầu)
    import datetime
    version = "v" + (ROOT / "VERSION").read_text(encoding="utf-8").strip() + "." + datetime.date.today().strftime("%y%m%d")
    print(f"  Phiên bản: {version}")
    (DIST / "VERSION.txt").write_text(version + "\n", encoding="utf-8")
    tpl = (ROOT / "build" / "template.html").read_text(encoding="utf-8").replace("@@VERSION@@", version)
    assert tpl.count("@@DATA@@") == 1 and tpl.count("/*@@EDITION@@*/") == 1 and tpl.count("/*@@NO_SPEECH@@*/false") == 1

    # Các bản: (tên file, ngôn ngữ tra). Bản Trung giữ tên cũ TuDien.html cho người đã quen.
    editions = [("TuDien", ["zh"]), ("TuDien-Nhat", ["ja"]), ("TuDien-Han", ["ko"]), ("TuDien-DaNgu", ["zh", "ja", "ko"])]
    for name, langs in editions:
        data = "\n".join(f'<script type="text/plain" id="D_{k}">{blobs[k]}</script>'
                         for k in langs + ["en", "vi", "gl"])
        html_ = (tpl.replace("@@DATA@@", data)
                    .replace("/*@@EDITION@@*/", json.dumps({"langs": langs, "name": name})))
        for suffix, no_speech in (("", "false"), ("-KhongLoa", "true")):
            out = DIST / f"{name}{suffix}.html"
            out.write_text(html_.replace("/*@@NO_SPEECH@@*/false", no_speech), encoding="utf-8")
            print(f"Xong: {out.name} ({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
