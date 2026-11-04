"""Day 5 (DAT): load the raw PSI tables and print columns, dtypes and missing values."""

from pathlib import Path

import pandas as pd

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


def main() -> None:
    for path in sorted(RAW.glob("*.csv")):
        df = pd.read_csv(path, encoding="utf-8", encoding_errors="replace")
        df.columns = [c.strip() for c in df.columns]
        print(f"\n===== {path.name}  shape={df.shape}")
        info = pd.DataFrame(
            {
                "dtype": df.dtypes.astype(str),
                "missing": df.isna().sum(),
                "placeholder": df.apply(
                    lambda s: s.astype(str).str.contains("�|n/a|~", regex=True).sum()
                ),
                "unique": df.nunique(),
                "example": df.apply(lambda s: s.dropna().iloc[0] if s.notna().any() else None),
            }
        )
        print(info.to_string())
        if "FLEX Test #" in df.columns:
            ids = df["FLEX Identifier"]
            print("\nduplicate IDs:", ids[ids.duplicated(keep=False)].tolist())
            zero_p = df["Ambient pressure; mmHg"] == 0
            print("pressure==0 rows:", ids[zero_p].tolist())
            print(df["Test end"].value_counts().to_string())
            print(df["Fuel"].value_counts().to_string())
            print(df.describe().T.to_string())


if __name__ == "__main__":
    main()
