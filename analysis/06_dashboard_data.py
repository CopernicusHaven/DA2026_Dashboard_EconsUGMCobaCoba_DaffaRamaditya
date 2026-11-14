"""
Export the cleaned data + analysis results into dashboard/data/data.js (window.DATA = {...}).
Only reshapes existing outputs: no new data, no imputation (missing days stay null).
Run: python3 analysis/06_dashboard_data.py
"""
import json
import numpy as np
import pandas as pd
from common import BASE, CLEAN, TAB, POLL

OUT = BASE / "dashboard" / "data"
OUT.mkdir(parents=True, exist_ok=True)
START = pd.Timestamp("2024-01-01")
NDAYS = 1018


def rec(df, nd=3):
    df = df.copy()
    for c in df.columns:
        if pd.api.types.is_float_dtype(df[c]):
            df[c] = df[c].round(nd)
        elif pd.api.types.is_datetime64_any_dtype(df[c]):
            df[c] = df[c].dt.strftime("%Y-%m-%d")
    return json.loads(df.to_json(orient="records", force_ascii=False))


def arr(s, nd=1):
    return [None if pd.isna(v) else (round(float(v), nd) if nd else int(v)) for v in s]


dim = pd.read_csv(CLEAN / "dim_station.csv")
prof = pd.read_csv(TAB / "o1_station_profile.csv")
net = pd.read_csv(TAB / "o5_network_station_assessment.csv")
trend = pd.read_csv(TAB / "o1_trend_pm25.csv")
qual = pd.read_csv(CLEAN / "data_quality_station.csv")

# ---------------- stations ----------------
st = dim[["station", "provinsi", "kota_kabupaten", "kecamatan", "karakteristik_wilayah", "site_type", "site_category",
          "island", "latitude_dd", "longitude_dd", "traffic_intensity_per_h", "distance_to_road_m", "baseline_pm25",
          "nama_sensor", "model_sensor", "status_operasional", "hospital_id", "nama_rumah_sakit", "kelas_faskes",
          "kapasitas_tempat_tidur", "notes"]]
st = st.merge(qual[["station", "completeness_pm25_pct", "used_in_analysis"]], on="station", how="left")
st = st.merge(prof[["station"] + [f"{p}_mean" for p in POLL] + ["pct_days_exceed_bm24h_pm25"]], on="station", how="left")
st = st.merge(net[["station", "reliability", "aksi_alat", "priority_score", "komponen_tidak_tersedia", "nearest_station",
                   "nn_distance_km", "haze_days", "resp_per100beds", "komp_polusi", "komp_kabut_asap",
                   "komp_beban_kesehatan", "komp_defisit_data", "komp_keterisolasian"]], on="station", how="left")
st = st.merge(trend[["station", "trend_overall", "chg_2024_2026_pct", "pm25_2024_jan_14okt", "pm25_2025_jan_14okt",
                     "pm25_2026_jan_14okt", "pm25_agu_okt_2024", "pm25_agu_okt_2025", "pm25_agu_okt_2026",
                     "bg_trend", "bg_sen_slope_ug_per_year"]], on="station", how="left")

# ---------------- daily AQ (full 1018-day arrays; null = no valid value) ----------------
D = pd.read_csv(CLEAN / "aqms_daily.csv", parse_dates=["date"])
D["di"] = (D.date - START).dt.days
CAT = {"1 Baik": 0, "2 Sedang": 1, "3 Tidak Sehat": 2, "4 Sangat Tidak Sehat": 3, "5 Berbahaya": 4}
daily = {}
for s, g in D.groupby("station"):
    g = g.set_index("di").reindex(range(NDAYS))
    daily[s] = {p: arr(g[p], 1) for p in POLL}
    daily[s]["ispu"] = arr(g["ispu"], 0)
    daily[s]["cat"] = [None if pd.isna(v) else CAT[v] for v in g["ispu_kategori"]]
    daily[s]["haze"] = [1 if v is True or v == 1 else 0 for v in g["haze_episode_day"].fillna(False)]
    daily[s]["co8"] = arr(g["co_8h_max"], 0)

# hourly sums & counts per station-day -> station means over any date filter equal the report's
# hourly-based means exactly (sum of valid hours / number of valid hours)
HR = pd.read_parquet(CLEAN / "aqms_hourly_clean.parquet", columns=["station", "date"] + [f"{p}_ug_m3" for p in POLL])
HR["di"] = (pd.to_datetime(HR.date) - START).dt.days
gs = HR.groupby(["station", "di"])
hsum, hcnt = gs[[f"{p}_ug_m3" for p in POLL]].sum(min_count=1), gs[[f"{p}_ug_m3" for p in POLL]].count()
for s in daily:
    S = hsum.loc[s].reindex(range(NDAYS)) if s in hsum.index.get_level_values(0) else None
    C = hcnt.loc[s].reindex(range(NDAYS)).fillna(0) if S is not None else None
    for p in POLL:
        daily[s]["hs_" + p] = arr(S[f"{p}_ug_m3"], 1) if S is not None else [None] * NDAYS
        daily[s]["hn_" + p] = [int(v) for v in C[f"{p}_ug_m3"]] if C is not None else [0] * NDAYS

# ---------------- health (complete 1018 days per hospital) ----------------
H = pd.read_csv(CLEAN / "health_daily_clean.csv", parse_dates=["date"])
H["di"] = (H.date - START).dt.days
OUTC = ["resp_admissions_under5", "resp_admissions_over60", "asthma_emergency_cases", "copd_admissions", "resp", "cvd", "death"]
health = {}
for h, g in H.groupby("hospital_id"):
    g = g.set_index("di").reindex(range(NDAYS))
    health[h] = {o: arr(g[o], 0) for o in OUTC}
    health[h]["station"] = g.station.dropna().iat[0]

# ---------------- diurnal profiles from hourly (non-haze days), weekday/weekend ----------------
hr = pd.read_parquet(CLEAN / "aqms_hourly_clean.parquet",
                     columns=["station", "date", "hour", "is_weekend", "pm25_ug_m3", "no2_ug_m3", "co_ug_m3", "o3_ug_m3",
                              "used_in_analysis"])
hr = hr[hr.used_in_analysis]
hz = D.loc[D.haze_episode_day == True, ["station", "date"]].assign(hz=True)  # noqa: E712
hr = hr.merge(hz, on=["station", "date"], how="left")
hr = hr[hr.hz.isna()]
diurnal = {}
for s, g in hr.groupby("station"):
    m = g.groupby("hour")[["pm25_ug_m3", "no2_ug_m3", "co_ug_m3", "o3_ug_m3"]].mean().reindex(range(24))
    wd = g[~g.is_weekend].groupby("hour")[["pm25_ug_m3", "no2_ug_m3"]].mean().reindex(range(24))
    we = g[g.is_weekend].groupby("hour")[["pm25_ug_m3", "no2_ug_m3"]].mean().reindex(range(24))
    diurnal[s] = {"pm25": arr(m.pm25_ug_m3, 2), "no2": arr(m.no2_ug_m3, 2), "co": arr(m.co_ug_m3, 1), "o3": arr(m.o3_ug_m3, 2),
                  "pm25_wd": arr(wd.pm25_ug_m3, 2), "pm25_we": arr(we.pm25_ug_m3, 2),
                  "no2_wd": arr(wd.no2_ug_m3, 2), "no2_we": arr(we.no2_ug_m3, 2)}

# ---------------- analysis tables ----------------
T = lambda n, **k: pd.read_csv(TAB / f"{n}.csv", **k)
imp = T("o3_rf_permutation_importance_groups", index_col=0)
r2 = float(imp.loc["_R2_test_2026", "importance"])
imp = imp.drop("_R2_test_2026").reset_index().rename(columns={"index": "group"})
log = pd.read_csv(CLEAN / "cleaning_log.csv")
log["aturan"] = log.rule.str.replace(r"\s*\(.*?\)", "", regex=True).str.split(" -> ").str[0]
logsum = log.groupby(["rule"]).agg(n=("n_affected", "sum"), stasiun=("station", lambda x: ", ".join(sorted(set(x))))).reset_index() \
    .sort_values("n", ascending=False)

data = {
    "meta": {"start": "2024-01-01", "ndays": NDAYS, "end": "2026-10-14", "team": "NamaTim", "leader": "NamaKetua",
             "rf_r2": round(r2, 3), "generated": pd.Timestamp.now().strftime("%Y-%m-%d")},
    "stations": rec(st), "daily": daily, "health": health, "diurnal": diurnal,
    "annual": rec(T("o1_annual_compliance_iku")), "shortterm": rec(T("o1_shortterm_standards")),
    "island": rec(T("o1_island_summary").rename(columns={"Unnamed: 0": "island"})),
    "catprof": rec(T("o2_site_category_profile")), "episodes": rec(T("o2_haze_episodes")),
    "smoke": rec(T("o2_smoke_fingerprint")), "critical": rec(T("o2_critical_area_ranking")),
    "weekend": rec(T("o2_weekday_weekend")),
    "importance": rec(imp), "meteo": rec(T("o3_all_pollutants_meteo_correlation")),
    "sitefac": rec(T("o3_all_pollutants_site_factors")), "wet": rec(T("o3_station_wetseason_vs_site")),
    "wind": rec(T("o3_wind_sector_pm25")[["station", "dirtiest_sector", "dirtiest_pm25", "cleanest_sector", "cleanest_pm25",
                                           "sector_ratio", "site_category"]]),
    "dlm": rec(T("o4_distributed_lag_model").assign(lag=lambda x: x.lag.astype(str))),
    "band": rec(T("o4_exposure_response_ispu_band")), "vuln": rec(T("o4_vulnerability_under5_vs_over60")),
    "hazehealth": rec(T("o4_haze_vs_normal_days")), "attr": rec(T("o4_attributable_cases_above_who")),
    "sens": rec(T("o4_sensitivity")),
    "gaps": rec(T("o5_monitoring_gap_corridors")), "coverage": rec(T("o5_island_coverage").rename(columns={"Unnamed: 0": "island"})),
    "conversion": rec(pd.read_csv(CLEAN / "unit_conversion_ppm.csv")), "cleaning": rec(logsum),
}
js = "window.DATA = " + json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + ";\n"
(OUT / "data.js").write_text(js, encoding="utf-8")
# web app (Vite/React) reads the same data as JSON
APP = BASE / "dashboard-app" / "public" / "data"
APP.mkdir(parents=True, exist_ok=True)
(APP / "dashboard.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False), encoding="utf-8")
print(f"data.js {len(js) / 1e6:.2f} MB; stations {len(st)}, daily stations {len(daily)}, hospitals {len(health)}")
