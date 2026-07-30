import os
import re
import json
import base64
import pandas as pd
from pathlib import Path
from openai import OpenAI

# ==============================
# ここにAPIキーを入れてください
# ==============================
API_KEY = "ここにAPIキーを貼り付ける"

# ==============================
# ファイルの場所を指定してください
# ==============================
# 筆ぐるめからエクスポートしたCSVのパス（不要なら空文字 "" にする）
FUDEGURUME_CSV = ""

# EvernoteからエクスポートしたCSVのパス（不要なら空文字 "" にする）
EVERNOTE_CSV = ""

# PDF・JPGが入っているフォルダのパス
IMAGE_FOLDER = "C:/Users/gnout/OneDrive/デスクトップ/顧客画像"

# 出力するExcelファイルの名前
OUTPUT_FILE = "C:/Users/gnout/OneDrive/デスクトップ/顧客一覧.xlsx"

# ==============================

client = OpenAI(api_key=API_KEY)


def ocr_image(image_path):
    """GPT-4oのVision機能で画像から顧客情報を抽出する"""
    print(f"  読み取り中: {Path(image_path).name}")
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    ext = Path(image_path).suffix.lower()
    media_type = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{media_type};base64,{image_data}"}
                },
                {
                    "type": "text",
                    "text": (
                        "この画像からお米の顧客情報を抽出してください。"
                        "以下のJSON形式で返してください（余計な説明不要）:\n"
                        '{"氏名": "", "郵便番号": "", "住所": "", "電話番号": "", "メモ": ""}'
                    )
                }
            ]
        }]
    )

    content = response.choices[0].message.content
    match = re.search(r"\{.*?\}", content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {"氏名": "", "郵便番号": "", "住所": "", "電話番号": "", "メモ": content[:100]}


def pdf_to_images(pdf_path):
    """PDFを画像に変換する（pdf2imageが必要）"""
    try:
        from pdf2image import convert_from_path
        images = convert_from_path(pdf_path)
        temp_paths = []
        for i, img in enumerate(images):
            temp_path = f"_temp_pdf_page_{i}.jpg"
            img.save(temp_path, "JPEG")
            temp_paths.append(temp_path)
        return temp_paths
    except ImportError:
        print("  ※ pdf2imageが未インストールのためPDFをスキップします")
        return []


def load_fudegurume(csv_path):
    """筆ぐるめのCSVを読み込む"""
    if not csv_path or not Path(csv_path).exists():
        return pd.DataFrame()
    print(f"筆ぐるめCSV読み込み中: {csv_path}")
    df = pd.read_csv(csv_path, encoding="shift_jis", on_bad_lines="skip")
    # 列名を統一（筆ぐるめの列名に合わせて調整が必要な場合あり）
    rename_map = {}
    for col in df.columns:
        if "名前" in col or "氏名" in col or "姓" in col:
            rename_map[col] = "氏名"
        elif "郵便" in col:
            rename_map[col] = "郵便番号"
        elif "住所" in col:
            rename_map[col] = "住所"
        elif "電話" in col or "TEL" in col.upper():
            rename_map[col] = "電話番号"
    df = df.rename(columns=rename_map)
    df["出典"] = "筆ぐるめ"
    return df


def load_evernote(csv_path):
    """EvernoteエクスポートCSVを読み込む"""
    if not csv_path or not Path(csv_path).exists():
        return pd.DataFrame()
    print(f"EvernoteCSV読み込み中: {csv_path}")
    df = pd.read_csv(csv_path, encoding="utf-8", on_bad_lines="skip")
    df["出典"] = "Evernote"
    return df


def load_images(folder):
    """フォルダ内のJPG・PDFをOCRで読み込む"""
    if not folder or not Path(folder).exists():
        print(f"フォルダが見つかりません: {folder}")
        return pd.DataFrame()

    print(f"\n画像フォルダ読み込み中: {folder}")
    records = []
    folder_path = Path(folder)

    for file in sorted(folder_path.iterdir()):
        ext = file.suffix.lower()
        if ext in [".jpg", ".jpeg", ".png"]:
            info = ocr_image(str(file))
            info["出典"] = str(file.name)
            records.append(info)
        elif ext == ".pdf":
            temp_images = pdf_to_images(str(file))
            for temp in temp_images:
                info = ocr_image(temp)
                info["出典"] = str(file.name)
                records.append(info)
                os.remove(temp)

    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records)


def main():
    all_dfs = []

    # 各ソースを読み込む
    df1 = load_fudegurume(FUDEGURUME_CSV)
    if not df1.empty:
        all_dfs.append(df1)

    df2 = load_evernote(EVERNOTE_CSV)
    if not df2.empty:
        all_dfs.append(df2)

    df3 = load_images(IMAGE_FOLDER)
    if not df3.empty:
        all_dfs.append(df3)

    if not all_dfs:
        print("データが見つかりませんでした。パスを確認してください。")
        return

    # 全データを結合
    print("\n全データを統合中...")
    combined = pd.concat(all_dfs, ignore_index=True)

    # 列を統一
    columns = ["氏名", "郵便番号", "住所", "電話番号", "メモ", "出典"]
    for col in columns:
        if col not in combined.columns:
            combined[col] = ""
    combined = combined[columns]

    # 重複削除（氏名＋住所が同じものを除外）
    before = len(combined)
    combined = combined.drop_duplicates(subset=["氏名", "住所"], keep="first")
    after = len(combined)
    print(f"重複削除: {before - after}件削除 → {after}件")

    # 空行を削除
    combined = combined[combined["氏名"].str.strip() != ""]

    # Excelに出力
    combined.to_excel(OUTPUT_FILE, index=False)
    print(f"\n完了！Excelに保存しました: {OUTPUT_FILE}")
    print(f"合計 {len(combined)} 件の顧客情報")


if __name__ == "__main__":
    main()
