from __future__ import annotations
import re
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager
from .config import DATA_PROCESSED, OUTPUTS


def _pick_font(preferred: list[str]) -> str:
    """Pick the first installed font from `preferred`; fall back to DejaVu Sans."""
    installed = {f.name for f in font_manager.fontManager.ttflist}
    for name in preferred:
        if name in installed:
            return name
    return "DejaVu Sans"


def _set_style() -> None:
    """Presentation-friendly style without custom colors."""
    plt.rcParams.update({
        "figure.dpi": 150,
        "savefig.dpi": 200,
        "figure.figsize": (9, 5),
        "axes.titlesize": 14,
        "axes.labelsize": 11,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "grid.linestyle": "-",
    })

    # Windows: Malgun Gothic / macOS: AppleGothic / Linux: Nanum or Noto (if installed)
    font = _pick_font(["Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR", "Noto Sans KR"])
    plt.rcParams["font.family"] = font
    plt.rcParams["axes.unicode_minus"] = False


def _ensure_fig_dir() -> Path:
    fig_dir = OUTPUTS / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    return fig_dir


def _save(fig, outpath: Path) -> None:
    outpath.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(outpath, bbox_inches="tight")
    plt.close(fig)


def load_processed() -> dict[str, pd.DataFrame]:
    return {
        "period_type": pd.read_csv(DATA_PROCESSED / "prosecution_reoffend_period_type_2017_tidy.csv"),
        "kosis_prior": pd.read_csv(DATA_PROCESSED / "kosis_prior_convictions_2023_tidy.csv"),
        "edu": pd.read_csv(DATA_PROCESSED / "police_education_2020_tidy.csv"),
        "world": pd.read_csv(DATA_PROCESSED / "world_recidivism_rates_tidy.csv"),
        "e_nara": pd.read_csv(DATA_PROCESSED / "e_nara_3yr_reimprisonment_tidy.csv"),
    }


# -------------------------
# Figure 1: 국내 재복역률 추이
# -------------------------
def fig_domestic_reimprisonment(e_nara: pd.DataFrame, out: Path) -> None:
    df = e_nara.copy()
    df = df[df["metric"].str.contains("재복역기간")].copy()
    df["year"] = df["year"].astype(int)

    fig, ax = plt.subplots()
    for metric, g in df.groupby("metric", sort=False):
        g = g.sort_values("year")
        ax.plot(g["year"], g["value"], marker="o", label=metric)

    ax.set_title("출소자 3년 이내 재복역률 추이")
    ax.set_xlabel("연도")
    ax.set_ylabel("재복역률(%)")
    ax.set_xticks(sorted(df["year"].unique()))
    ax.legend(frameon=False, ncols=3)
    _save(fig, out)


# -------------------------
# Figure 2: 재범까지 경과기간 분포(동종/이종) - 비중%
# -------------------------
def fig_reoffend_time_distribution(period_type: pd.DataFrame, out: Path) -> None:
    order = ["1개월이내", "3개월이내", "6개월이내", "1년이내", "2년이내", "3년이내", "3년초과"]
    df = period_type.copy()

    agg = df.groupby(["recid_type", "period"], as_index=False)["count"].sum()
    agg["period"] = pd.Categorical(agg["period"], categories=order, ordered=True)
    agg = agg.sort_values(["recid_type", "period"])
    agg["share_pct"] = agg.groupby("recid_type")["count"].transform(lambda s: 100 * s / s.sum())

    fig, ax = plt.subplots()
    for recid_type, g in agg.groupby("recid_type", sort=False):
        ax.plot(g["period"].astype(str), g["share_pct"], marker="o", label=recid_type)

    ax.set_title("재범까지 경과기간 분포(비중)")
    ax.set_xlabel("경과기간")
    ax.set_ylabel("비중(%)")
    ax.legend(frameon=False)
    _save(fig, out)


# -------------------------
# Figure 3: 재범자 수 상위 범죄유형 (Top-N) - barh
# -------------------------
def fig_top_crimes(period_type: pd.DataFrame, out: Path, top_n: int = 12) -> None:
    total = period_type.groupby("crime", as_index=False)["count"].sum()
    total = total.sort_values("count", ascending=False).head(top_n).sort_values("count")

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(total["crime"], total["count"])
    ax.set_title(f"재범자 수 상위 {top_n} 범죄유형(집계)")
    ax.set_xlabel("재범자 수(명)")
    ax.set_ylabel("")
    _save(fig, out)


# -------------------------
# Figure 4: 전과 유무 구성비(2023, KOSIS) - 비중%
# -------------------------
def fig_prior_conviction_share(kosis_prior: pd.DataFrame, out: Path) -> None:
    df = kosis_prior.copy()
    base = df[(df["crime_lvl1"] == "합계") & (df["crime_lvl2"] == "소계") & (df["crime_lvl3"] == "소계")]

    no_prior = base[(base["group"] == "전과없음") & (base["detail"] == "소계")]["count"].sum()

    # 전과는 "소계"가 있으면 그걸 쓰고(중복 방지), 없으면 1~9+ 합산
    prior_total = base[(base["group"] == "전과") & (base["detail"] == "소계")]["count"].sum()
    if prior_total > 0:
        prior = prior_total
    else:
        prior = base[(base["group"] == "전과") & (base["detail"] != "소계")]["count"].sum()

    unknown = base[(base["group"] == "미상") & (base["detail"] == "소계")]["count"].sum()

    comp = pd.DataFrame({
        "category": ["전과없음", "전과(1회 이상)", "미상"],
        "count": [no_prior, prior, unknown],
    })
    comp["share_pct"] = 100 * comp["count"] / comp["count"].sum()

    fig, ax = plt.subplots()
    ax.bar(comp["category"], comp["share_pct"])
    ax.set_title("범죄자 전과 유무 구성비(2023)")
    ax.set_ylabel("비중(%)")
    for i, v in enumerate(comp["share_pct"]):
        ax.text(i, v, f"{v:.1f}%", ha="center", va="bottom", fontsize=9)
    _save(fig, out)


# -------------------------
# Figure 5: 교육수준(버킷) - 비중%
# -------------------------
def fig_education_bucket_share(edu: pd.DataFrame, out: Path) -> None:
    def bucket(x: str) -> str:
        x = str(x)
        if re.search(r"(대학원|대학|전문대)", x):
            return "대학 이상"
        if x in ["미상", "기타"]:
            return "미상/기타"
        return "고졸 이하"

    df = edu.copy()
    df["bucket"] = df["education"].map(bucket)
    total = df.groupby("bucket", as_index=False)["count"].sum()
    total["share_pct"] = 100 * total["count"] / total["count"].sum()
    total = total.sort_values("share_pct", ascending=False)

    fig, ax = plt.subplots()
    ax.bar(total["bucket"], total["share_pct"])
    ax.set_title("범죄자 교육수준 분포(2020, 버킷)")
    ax.set_ylabel("비중(%)")
    for i, v in enumerate(total["share_pct"]):
        ax.text(i, v, f"{v:.1f}%", ha="center", va="bottom", fontsize=9)
    _save(fig, out)


# -------------------------
# Figure 6: 국가별 재복역률(1~5년) 라인차트 (Reimprisonment 기준)
# -------------------------
def fig_world_followup_lines(world: pd.DataFrame, out: Path) -> None:
    df = world.copy()
    # South Korea is present in this dataset under Reimprisonment (not Reconviction).
    df = df[df["type"].str.lower().eq("reimprisonment")].copy()
    df = df[df["followup_years"].isin([1, 2, 3, 4, 5])].copy()

    # Keep the list small and include South Korea.
    pick = ["France", "United States", "New Zealand", "Israel", "South Korea"]
    df = df[df["country"].isin(pick)].copy()

    # country+followup 중복이면 최신 period만 유지
    df = df.sort_values(["country", "followup_years", "period"]).drop_duplicates(["country", "followup_years"], keep="last")

    fig, ax = plt.subplots(figsize=(9, 5.5))
    for c, g in df.groupby("country", sort=False):
        g = g.sort_values("followup_years")
        ax.plot(g["followup_years"], g["rate_pct"], marker="o", label=c)

    ax.set_title("국가별 재복역률 비교(재수감, 추적 1~5년)")
    ax.set_xlabel("추적기간(년)")
    ax.set_ylabel("재복역률(%)")
    ax.set_xticks([1, 2, 3, 4, 5])
    ax.legend(frameon=False, ncols=2)
    _save(fig, out)


def main() -> None:
    _set_style()
    fig_dir = _ensure_fig_dir()
    t = load_processed()

    fig_domestic_reimprisonment(t["e_nara"], fig_dir / "01_domestic_3yr_reimprisonment_trend.png")
    fig_reoffend_time_distribution(t["period_type"], fig_dir / "02_reoffend_time_distribution.png")
    fig_top_crimes(t["period_type"], fig_dir / "03_top_crimes_reoffenders.png", top_n=12)
    fig_prior_conviction_share(t["kosis_prior"], fig_dir / "04_prior_conviction_share_2023.png")
    fig_education_bucket_share(t["edu"], fig_dir / "05_education_bucket_share_2020.png")
    fig_world_followup_lines(t["world"], fig_dir / "06_world_recidivism_followup_lines.png")

    print(f"[OK] Saved figures to: {fig_dir}")


if __name__ == "__main__":
    main()
