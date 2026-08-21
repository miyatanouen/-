# -*- coding: utf-8 -*-
"""
2L判（127×178mm）POPカード生成スクリプト

CARDS の中身を書き換えて実行すると、1枚ずつPDFが出力されます。
文中で改行したいところには「/」を入れてください。
"""
import subprocess
import tempfile
from pathlib import Path

# ==============================
# ここにカードの内容を書いてください
# ==============================
CARDS = [
    {
        "見出し": "宮田農園",
        "問いかけ": "北海道の雪解け水で育つと、/お米はどんな味になると思いますか。",
        "添え書き": "答えは、ひとくちめに。",
        "品名": "ゆめぴりか　二キロ",
        "価格": 2000,
    },
]

# Chromium（Chrome）の実行ファイルの場所
CHROMIUM = "/opt/pw-browsers/chromium"

# 出力先フォルダ
OUT_DIR = Path(__file__).parent / "output"

# ==============================

TEMPLATE = (Path(__file__).parent / "template.html").read_text(encoding="utf-8")


def render_card(card, out_pdf):
    html = (
        TEMPLATE
        .replace("{{HEADER}}", card.get("見出し", ""))
        .replace("{{COPY}}", card["問いかけ"].replace("/", "<br>"))
        .replace("{{SUB}}", card.get("添え書き", ""))
        .replace("{{ITEM}}", card.get("品名", ""))
        .replace("{{PRICE}}", f"¥{card['価格']:,}")
    )
    with tempfile.NamedTemporaryFile(
        "w", suffix=".html", encoding="utf-8", delete=False
    ) as f:
        f.write(html)
        html_path = f.name
    subprocess.run(
        [
            CHROMIUM,
            "--headless",
            "--no-sandbox",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={out_pdf}",
            f"file://{html_path}",
        ],
        check=True,
        capture_output=True,
    )
    Path(html_path).unlink()


def main():
    OUT_DIR.mkdir(exist_ok=True)
    for i, card in enumerate(CARDS, 1):
        name = card.get("品名", f"card{i}").replace("　", "").replace(" ", "")
        out = OUT_DIR / f"{i:02d}_{name}.pdf"
        render_card(card, out)
        print(f"出力しました: {out}")


if __name__ == "__main__":
    main()
