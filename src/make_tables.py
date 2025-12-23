from __future__ import annotations
import pandas as pd
from .config import DATA_PROCESSED, OUTPUTS

def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    # H2: distribution of recidivism period (동종/이종 합계)
    df_p = pd.read_csv(DATA_PROCESSED / "prosecution_reoffend_period_type_2017_tidy.csv", encoding="utf-8-sig")
    h2 = (
        df_p.groupby(["recid_type", "period"], as_index=False)["count"].sum()
          .sort_values(["recid_type", "count"], ascending=[True, False])
    )
    h2.to_csv(OUTPUTS / "H2_period_distribution.csv", index=False, encoding="utf-8-sig")

    # H1(대체): 2023 전과(없음 vs 있음) 비중 (KOSIS)
    df_k = pd.read_csv(DATA_PROCESSED / "kosis_prior_convictions_2023_tidy.csv", encoding="utf-8-sig")
    # use only overall total row: (합계/소계/소계) & group=='전과없음' or '전과'
    total = df_k[(df_k["crime_lvl1"]=="합계") & (df_k["crime_lvl2"]=="소계") & (df_k["crime_lvl3"]=="소계")]
    h1 = total[total["group"].isin(["전과없음","전과"])].groupby(["year","group"], as_index=False)["count"].sum()
    # share
    denom = h1.groupby("year")["count"].transform("sum")
    h1["share"] = h1["count"]/denom
    h1.to_csv(OUTPUTS / "H1_prior_share_2023.csv", index=False, encoding="utf-8-sig")

    # H3: education distribution aggregated to <=고졸 vs 대졸+
    df_e = pd.read_csv(DATA_PROCESSED / "police_education_2020_tidy.csv", encoding="utf-8-sig")
    def edu_bucket(x: str) -> str:
        if x.startswith("대학") or x.startswith("대학원"):
            return "대학이상"
        if x.startswith("고등학교") or x.startswith("중학교") or x.startswith("초등학교") or x=="불취학":
            return "고졸이하"
        return "기타/미상"
    df_e["bucket"] = df_e["education"].map(edu_bucket)
    h3 = df_e.groupby(["bucket"], as_index=False)["count"].sum()
    h3["share"] = h3["count"]/h3["count"].sum()
    h3.to_csv(OUTPUTS / "H3_education_bucket_share_2020.csv", index=False, encoding="utf-8-sig")

    # H4: Country comparison (1y & 5y, Reimprisonment 우선)
    df_w = pd.read_csv(DATA_PROCESSED / "world_recidivism_rates_tidy.csv", encoding="utf-8-sig")
    h4 = df_w[df_w["followup_years"].isin([1.0, 5.0])].copy()
    h4.to_csv(OUTPUTS / "H4_country_1y_5y.csv", index=False, encoding="utf-8-sig")

    # Domestic trend: e-nara 3yr reimprisonment
    df_n = pd.read_csv(DATA_PROCESSED / "e_nara_3yr_reimprisonment_tidy.csv", encoding="utf-8-sig")
    trend = df_n[df_n["metric"].astype(str).str.contains("재복역기간3년이내")]
    trend.to_csv(OUTPUTS / "domestic_3yr_reimprisonment_rate.csv", index=False, encoding="utf-8-sig")

    print("✅ outputs saved to:", OUTPUTS)


if __name__ == "__main__":
    main()
