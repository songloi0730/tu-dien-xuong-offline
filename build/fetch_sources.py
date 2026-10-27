"""Tải dữ liệu nguồn vào _src/ (cần internet, chạy một lần trước build.py).

    python build/fetch_sources.py

Nguồn và giấy phép: xem README.md.
"""
import io
import sys
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "_src"
UA = {"User-Agent": "tu-dien-xuong-offline/1.0"}


def get(url: str) -> bytes:
    print("  tải", url)
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
        return r.read()


def unzip(data: bytes, dest: Path, members=None):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for n in z.namelist():
            if members is None or any(n.startswith(m) for m in members):
                z.extract(n, dest)


def latest_tag(repo: str) -> str:
    req = urllib.request.Request(f"https://github.com/{repo}/releases/latest", headers=UA, method="HEAD")
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.geturl().rsplit("/tag/", 1)[1]


def main():
    SRC.mkdir(exist_ok=True)
    print("CC-CEDICT (Trung-Anh)")
    unzip(get("https://www.mdbg.net/chinese/export/cedict/cedict_1_0_ts_utf-8_mdbg.zip"), SRC)
    print("CVDICT (Trung-Việt)")
    (SRC / "CVDICT.u8").write_bytes(get("https://github.com/ph0ngp/CVDICT/raw/refs/heads/main/CVDICT.u8"))
    print("hanviet-pinyin-wordlist (âm Hán-Việt)")
    unzip(get("https://github.com/ph0ngp/hanviet-pinyin-wordlist/archive/refs/heads/main.zip"), SRC)
    print("OVDP stardict-vi (Anh-Việt, Việt-Anh, Trung/Nhật/Hàn-Việt)")
    unzip(get("https://github.com/dynamotn/stardict-vi/archive/refs/heads/master.zip"), SRC,
          [f"stardict-vi-master/{d}/" for d in ("en-vi", "vi-en", "zh-vi", "ja-vi", "ko-vi")])
    print("JMdict + KANJIDIC2 (Nhật)")
    tag = latest_tag("scriptin/jmdict-simplified")
    ver = urllib.parse.unquote(tag)
    base = f"https://github.com/scriptin/jmdict-simplified/releases/download/{urllib.parse.quote(ver)}"
    unzip(get(f"{base}/jmdict-eng-{urllib.parse.quote(ver)}.json.zip"), SRC / "jmdict")
    unzip(get(f"{base}/kanjidic2-all-{urllib.parse.quote(ver)}.json.zip"), SRC / "kanjidic")
    print("kengdic (Hàn-Anh)")
    unzip(get("https://github.com/garfieldnate/kengdic/archive/refs/heads/master.zip"), SRC, ["kengdic-master/kengdic.tsv"])
    print("Xong. Chạy tiếp: python build/build.py")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
