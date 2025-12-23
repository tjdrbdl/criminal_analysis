from __future__ import annotations
import re
from pathlib import Path
import pandas as pd
from .config import DATA_RAW, DATA_PROCESSED


def clean_prosecution_period_type(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="cp949")
    id_col = "범죄분류"
    value_cols = [c for c in df.columns if c != id_col]

    long = df.melt(id_vars=[id_col], value_vars=value_cols, var_name="metric", value_name="count")
    parsed = long["metric"].str.extract(r"(?P<recid_type>동종재범|이종재범)_(?P<period>.+)")
    long = pd.concat([long[[id_col, "count"]], parsed], axis=1)

    long = long.rename(columns={id_col: "crime"})
    long["count"] = pd.to_numeric(long["count"], errors="coerce").fillna(0).astype(int)
    return long[["crime", "recid_type", "period", "count"]]


def clean_kosis_prior_convictions(path: Path) -> pd.DataFrame:
    """KOSIS style CSV: first 2 rows are multi-headers for year columns."""
    df = pd.read_csv(path, encoding="cp949")
    header1 = df.iloc[0]
    header2 = df.iloc[1]

    crime_cols = ["범죄별(1)", "범죄별(2)", "범죄별(3)"]
    year_cols = [c for c in df.columns if c not in crime_cols]

    new_cols = {}
    for c in year_cols:
        year = re.findall(r"\d{4}", str(c))
        year = year[0] if year else str(c)

        top = str(header1[c]).strip().replace("nan", "").strip()
        sub = str(header2[c]).strip().replace("nan", "").strip()

        name = "_".join([x for x in [year, top, sub] if x])
        new_cols[c] = name

    df = df.rename(columns=new_cols).iloc[2:].copy()
    df = df[~df["범죄별(1)"].astype(str).str.contains("범죄별", na=False)]

    value_cols = [c for c in df.columns if c not in crime_cols]
    long = df.melt(id_vars=crime_cols, value_vars=value_cols, var_name="metric", value_name="count")

    parts = long["metric"].str.split("_", n=2, expand=True)
    long["year"] = parts[0]
    long["group"] = parts[1].fillna("")
    long["detail"] = parts[2].fillna("")

    long["count"] = pd.to_numeric(long["count"], errors="coerce")
    long = long.dropna(subset=["count"])
    long["count"] = long["count"].astype(int)

    long = long.rename(
        columns={
            "범죄별(1)": "crime_lvl1",
            "범죄별(2)": "crime_lvl2",
            "범죄별(3)": "crime_lvl3",
        }
    )
    return long[["year", "crime_lvl1", "crime_lvl2", "crime_lvl3", "group", "detail", "count"]]


def clean_police_education(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="cp949")
    id_cols = ["범죄대분류", "범죄중분류"]
    value_cols = [c for c in df.columns if c not in id_cols]

    long = df.melt(id_vars=id_cols, value_vars=value_cols, var_name="education", value_name="count")
    long["count"] = pd.to_numeric(long["count"], errors="coerce").fillna(0).astype(int)

    long = long.rename(columns={"범죄대분류": "crime_major", "범죄중분류": "crime_minor"})
    return long[["crime_major", "crime_minor", "education", "count"]]


def clean_police_prior_record(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="cp949")
    id_cols = ["범죄대분류", "범죄중분류"]
    value_cols = [c for c in df.columns if c not in id_cols]

    long = df.melt(id_vars=id_cols, value_vars=value_cols, var_name="prior_record", value_name="count")
    long["count"] = pd.to_numeric(long["count"], errors="coerce").fillna(0).astype(int)

    long = long.rename(columns={"범죄대분류": "crime_major", "범죄중분류": "crime_minor"})
    return long[["crime_major", "crime_minor", "prior_record", "count"]]


def clean_world_recidivism(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["rate_pct"] = pd.to_numeric(df["Rate"].astype(str).str.replace("%", ""), errors="coerce")

    df["followup_years"] = pd.to_numeric(df["Follow-Up"].astype(str).str.extract(r"(\d+\.?\d*)")[0], errors="coerce")
    is_month = df["Follow-Up"].astype(str).str.contains("month", case=False, na=False)
    df.loc[is_month, "followup_years"] = df.loc[is_month, "followup_years"] / 12.0

    return df.rename(
        columns={"Country": "country", "Type": "type", "Duration": "period"}
    )[["country", "followup_years", "rate_pct", "type", "period"]]


def clean_enara_3yr_excel(path: Path) -> pd.DataFrame:
    raw = pd.read_excel(path)

    header_row = None
    for i, row in raw.iterrows():
        joined = " ".join([str(x) for x in row.values if pd.notna(x)])
        if "2019" in joined and "2020" in joined:
            header_row = i
            break
    if header_row is None:
        raise ValueError("Could not find the year-header row in the Excel sheet.")

    header = raw.iloc[header_row].tolist()
    df = raw.iloc[header_row + 1 :].copy()
    df.columns = header
    df = df.rename(columns={df.columns[0]: "metric"})
    df = df[df["metric"].notna()]
    df = df[~df["metric"].astype(str).str.contains("출처", na=False)]

    year_cols = [c for c in df.columns if c != "metric" and str(c) != "nan"]
    long = df.melt(id_vars=["metric"], value_vars=year_cols, var_name="year", value_name="value")

    long["value"] = (
        long["value"].astype(str).str.replace(",", "", regex=False)
    )
    long["value"] = pd.to_numeric(long["value"], errors="coerce")
    long = long.dropna(subset=["value"])
    return long[["metric", "year", "value"]]


def main() -> None:
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    clean_prosecution_period_type(DATA_RAW / "prosecution_reoffend_period_type_2017.csv") \
        .to_csv(DATA_PROCESSED / "prosecution_reoffend_period_type_2017_tidy.csv", index=False, encoding="utf-8-sig")

    clean_kosis_prior_convictions(DATA_RAW / "kosis_prior_convictions_2023.csv") \
        .to_csv(DATA_PROCESSED / "kosis_prior_convictions_2023_tidy.csv", index=False, encoding="utf-8-sig")

    clean_police_education(DATA_RAW / "police_education_2020.csv") \
        .to_csv(DATA_PROCESSED / "police_education_2020_tidy.csv", index=False, encoding="utf-8-sig")

    clean_police_prior_record(DATA_RAW / "police_prior_record_2020.csv") \
        .to_csv(DATA_PROCESSED / "police_prior_record_2020_tidy.csv", index=False, encoding="utf-8-sig")

    clean_world_recidivism(DATA_RAW / "world_recidivism_rates.csv") \
        .to_csv(DATA_PROCESSED / "world_recidivism_rates_tidy.csv", index=False, encoding="utf-8-sig")

    clean_enara_3yr_excel(DATA_RAW / "e_nara_3yr_reimprisonment.xlsx") \
        .to_csv(DATA_PROCESSED / "e_nara_3yr_reimprisonment_tidy.csv", index=False, encoding="utf-8-sig")

    print("✅ processed csv saved to:", DATA_PROCESSED)


if __name__ == "__main__":
    main()
