
# config/target_loader.py
import pandas as pd

def load_target_file(uploaded_file):
    """
    目標データCSVファイルを読み込み、診療科と目標件数の辞書を返す
    複数のエンコーディングを試行して読み込む
    """
    encodings = ['cp932', 'utf-8-sig', 'utf-8', 'shift-jis', 'euc-jp']

    for encoding in encodings:
        try:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, encoding=encoding)
            df.columns = df.columns.str.strip()

            dept_col = None
            target_col = None

            for col in ["実施診療科", "診療科"]:
                if col in df.columns:
                    dept_col = col
                    break

            for col in ["目標（週合計）", "目標件数", "目標"]:
                if col in df.columns:
                    target_col = col
                    break

            if dept_col is None or target_col is None:
                continue

            df = df[[dept_col, target_col]]
            df.rename(columns={dept_col: "診療科", target_col: "目標件数"}, inplace=True)
            df["目標件数"] = pd.to_numeric(df["目標件数"], errors="coerce")
            df.dropna(subset=["目標件数"], inplace=True)

            return dict(zip(df["診療科"], df["目標件数"]))

        except Exception:
            continue

    raise ValueError(f"目標データファイルをいずれのエンコーディング({', '.join(encodings)})でも読み込めませんでした。")