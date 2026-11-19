# -*- coding: utf-8 -*-
"""自分でダウンロードした論文PDFの名前を「保存日_タイトル.pdf」に変える。

使い方（ゼミフォルダの「PDFの名前を整える.bat」から呼ばれる）
- PDFを .bat の上にドラッグ＆ドロップ → その場で名前を変える
- .bat をダブルクリック → ゼミフォルダの「名前を変える」フォルダにあるPDFの名前を変え、
  「後で読む論文」フォルダへ移す

タイトルの探し方（上から順に試す）
1. PDFの1〜2ページ目にあるDOIから、doi.org の書誌情報でタイトルを取る
2. 1ページ目（だめなら2ページ目）で一番大きな文字の行（雑誌名・巻号らしいものは除く）
3. PDFに埋め込まれたタイトル情報（本文に同じ文字列があるときだけ）
保存日は、PDFファイルを保存した日（ファイルの更新日）。
"""
import datetime
import json
import os
import re
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ZEMI = os.path.dirname(HERE)
INBOX = os.path.join(ZEMI, "名前を変える")
LATER = os.path.join(ZEMI, "後で読む論文")
DATED = re.compile(r"^\d{8}_")


def ensure_pypdf():
    need = []
    try:
        import pypdf  # noqa: F401
    except ImportError:
        need.append("pypdf")
    try:
        import cryptography  # noqa: F401  鍵のかかったPDF（J-STAGEなど）を開くのに使う
    except ImportError:
        need.append("cryptography")
    if need:
        print("PDFを読む部品を入れています。初回だけ1分ほどかかります…")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "--quiet",
                               "--disable-pip-version-check", "--no-warn-script-location", *need])
        # 入れたばかりの部品をこの実行の中でも読めるようにする
        import importlib
        import site
        site.addsitedir(site.getusersitepackages())
        importlib.invalidate_caches()


def safe_name(s):
    table = {":": "：", "?": "？", "*": "＊", '"': "”", "<": "＜", ">": "＞", "|": "｜", "/": "／", "\\": "＼"}
    for k, v in table.items():
        s = s.replace(k, v)
    s = re.sub(r"[\x00-\x1f]", "", s)
    s = re.sub(r"\s+", " ", s).strip().rstrip(".")
    s = re.sub(r"\s*：\s*", "：", s)
    return s[:150].strip()


JOURNALISH = re.compile(r"第\s*\d+\s*巻|\d+\s*巻\s*\d*\s*号|\bVol\.?\s*\d|\bNo\.\s*\d|PsycARTICLES|ScienceDirect|Journal of|学会誌|研究紀要", re.I)


def looks_like_title(t):
    """雑誌名・巻号・データベース名らしいものを除く。"""
    if not t or len(t) < 6:
        return False
    if JOURNALISH.search(t):
        return False
    if re.fullmatch(r"[A-Za-z]+", t.strip()):  # 英単語1語だけ（例：PsycARTICLES）
        return False
    return True


def norm(s):
    return re.sub(r"[\s\u3000・:：\-―—‐]", "", s or "").lower()


def title_from_doi(text):
    m = re.search(r"\b(10\.\d{4,9}/[^\s\"<>]+)", text)
    if not m:
        return None, None
    doi = m.group(1).rstrip(".,;)］】")
    req = urllib.request.Request(
        "https://doi.org/" + doi,
        headers={"Accept": "application/vnd.citationstyles.csl+json", "User-Agent": "Mozilla/5.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode("utf-8"))
        t = data.get("title")
        if isinstance(t, list):
            t = t[0] if t else None
        sub = data.get("subtitle")
        if isinstance(sub, list):
            sub = sub[0] if sub else None
        if t and sub and sub not in t:
            t = f"{t}：{sub}"
        return (re.sub(r"<[^>]+>", "", t).strip() if t else None), doi
    except Exception:
        return None, doi


def title_from_meta(reader, text):
    try:
        t = (reader.metadata or {}).get("/Title")
    except Exception:
        t = None
    if not t:
        return None
    t = str(t).strip()
    bad = (t.lower().endswith((".pdf", ".doc", ".docx", ".tex", ".dvi")) or t.lower().startswith(("microsoft word", "untitled"))
           or len(t) < 8)
    if bad or not looks_like_title(t) or norm(t) not in norm(text):
        return None
    return t


def title_from_fontsize(page):
    segs = []

    def visit(text, cm, tm, font_dict, font_size):
        if not text or not text.strip():
            return
        scale = (abs(tm[3]) or abs(tm[0]) or 1) * (abs(cm[3]) or 1)
        segs.append((round(font_size * scale, 1), text))

    try:
        page.extract_text(visitor_text=visit)
    except Exception:
        return None
    if not segs:
        return None
    big = max(s for s, _ in segs)
    picked = "".join(t for s, t in segs if s >= big * 0.92)
    picked = re.sub(r"\s+", " ", picked).strip()
    picked = re.sub(r"\s*[0-9０-９]{1,2}[）)]?$", "", picked).strip()  # 末尾の注番号を外す
    return picked if 5 <= len(picked) <= 300 and looks_like_title(picked) else None


def find_title(path):
    from pypdf import PdfReader
    reader = PdfReader(path)
    text = ""
    for i in range(min(2, len(reader.pages))):
        try:
            text += (reader.pages[i].extract_text() or "") + "\n"
        except Exception:
            pass
    t, doi = title_from_doi(text)
    if t:
        return t, f"DOI {doi} の書誌情報"
    for i in range(min(2, len(reader.pages))):
        t = title_from_fontsize(reader.pages[i])
        if t:
            return t, f"{i + 1}ページ目の一番大きな文字（念のため確かめてください）"
    t = title_from_meta(reader, text)
    if t:
        return t, "PDFに埋め込まれたタイトル情報"
    return None, None


def process(path, dest_dir):
    name = os.path.basename(path)
    if not name.lower().endswith(".pdf"):
        print(f"とばしました（PDFではありません）：{name}")
        return False
    if DATED.match(name):
        print(f"とばしました（すでに「保存日_」の名前です）：{name}")
        return False
    try:
        title, how = find_title(path)
    except Exception as e:
        print(f"読めませんでした：{name}（{e}）")
        return False
    if not title:
        print(f"タイトルが分かりませんでした：{name}　手で名前を付けてください。")
        return False
    day = datetime.date.fromtimestamp(os.path.getmtime(path)).strftime("%Y%m%d")
    new = f"{day}_{safe_name(title)}.pdf"
    target = os.path.join(dest_dir, new)
    if os.path.exists(target):
        print(f"同じ名前のファイルがあるので、変えませんでした：{new}")
        return False
    os.makedirs(dest_dir, exist_ok=True)
    os.rename(path, target)
    print(f"変更しました：{name}\n　→ {new}\n　（タイトルの出どころ：{how}）")
    return True


def main():
    ensure_pypdf()
    files = [a for a in sys.argv[1:] if os.path.isfile(a)]
    if files:
        pairs = [(f, os.path.dirname(os.path.abspath(f))) for f in files]
    else:
        os.makedirs(INBOX, exist_ok=True)
        pairs = [(os.path.join(INBOX, n), LATER) for n in sorted(os.listdir(INBOX)) if n.lower().endswith(".pdf")]
        if not pairs:
            print("「名前を変える」フォルダにPDFがありません。")
            print("ダウンロードした論文PDFを、ゼミフォルダの「名前を変える」に入れてから、もう一度ダブルクリックしてください。")
            print("（PDFをこの .bat の上にドラッグ＆ドロップしても使えます）")
            return
    ok = sum(process(p, d) for p, d in pairs)
    print(f"\n完了：{ok} 件の名前を変えました（{len(pairs)} 件中）")


if __name__ == "__main__":
    main()
