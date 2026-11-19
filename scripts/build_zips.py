# -*- coding: utf-8 -*-
"""配布用のzipを作る。

使い方：リポジトリの一番上で `python scripts/build_zips.py`
- dist/今日の先行研究_キット.zip（Claude版）
- dist/今日の先行研究_Gemini版キット.zip（Gemini版）

Windowsで文字化けしないように、次の2つを行う。
- 日本語のファイル名に「UTF-8で書いてある」という目印を付ける（Python の zipfile は自動で付ける）
- .md ファイルの先頭にBOM（UTF-8だと示す印）を付ける
"""
import os
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")
BOM = b"\xef\xbb\xbf"

KITS = [
    ("今日の先行研究_キット.zip", "今日の先行研究_キット", "claude"),
    ("今日の先行研究_Gemini版キット.zip", "今日の先行研究_Gemini版キット", "gemini"),
]


def build(zip_name, top, src_dir):
    os.makedirs(DIST, exist_ok=True)
    out = os.path.join(DIST, zip_name)
    src = os.path.join(ROOT, src_dir)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(os.listdir(src)):
            path = os.path.join(src, name)
            if not os.path.isfile(path):
                continue
            data = open(path, "rb").read()
            if name.lower().endswith(".md") and not data.startswith(BOM):
                data = BOM + data
            z.writestr(f"{top}/{name}", data)
    print("作成しました：", out)


if __name__ == "__main__":
    for args in KITS:
        build(*args)
