"""
GELAR RASA 2026 - Data Analytics Case Study
Step 1: Data cleaning & processing pipeline

Input : 27 AQMS CSV, HLT-01 health CSV, sites/sensors/hospitals, metadata (raw, untouched)
Output: output/clean/*  (hourly, daily, monthly, health, merged, dimension tables, cleaning log)

Run   : python3 analysis/01_clean.py
"""
from pathlib import Path
import re
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
RAW = BASE
OUT = BASE / "output" / "clean"
OUT.mkdir(parents=True, exist_ok=True)

PERIOD_START = pd.Timestamp("2024-01-01 00:00")
PERIOD_END = pd.Timestamp("2026-10-14 23:00")
HOURS = pd.date_range(PERIOD_START, PERIOD_END, freq="h")

POLL = ["pm25", "pm10", "so2", "co", "o3", "no2"]
MET = ["temperature_c", "humidity_pct", "wind_speed_ms", "wind_direction_deg"]
PCOL = {p: f"{p}_ug_m3" for p in POLL}

# ---- unit conversion (ppm -> ug/m3 at 25 degC, 1 atm; molar volume 24.45 L) ----
# Gases: ug/m3 = ppm * MW * 1000 / 24.45
# PM   : "ppm" can only be a mass mixing ratio -> ug/m3 = ppm * rho_air
#        rho_air(25C) = 28.97 * 1000 / 24.45 = 1184.9 ug/m3 per ppm(mass)
MOLAR_VOL = 24.45
MW = {"so2": 64.066, "co": 28.010, "o3": 47.998, "no2": 46.0055, "pm25": 28.97, "pm10": 28.97}
PPM_FACTOR = {p: MW[p] * 1000 / MOLAR_VOL for p in POLL}

# ---- physical plausibility limits (hourly, ug/m3 or native unit) ----
LIMITS = {
    "pm25_ug_m3": (0, 2000), "pm10_ug_m3": (0, 3000), "so2_ug_m3": (0, 2600),
    "co_ug_m3": (0, 60000), "o3_ug_m3": (0, 1200), "no2_ug_m3": (0, 3800),
    "temperature_c": (10, 45), "humidity_pct": (1, 100),
    "wind_speed_ms": (0, 40), "wind_direction_deg": (0, 360),
}
# Placeholder codes written by the logger. Negative codes (-9999/-999/-99/-273.2) and absurd values
# (1450.5 degC, 999.9 %RH) are also caught by the physical limits. 999 is NOT a sentinel for CO
# (999 ug/m3 CO is a normal urban value), so CO only treats 9999 as a code.
SENTINELS = {-9999, -999, -999.9, -99, -99.9, -273.2, 999, 999.9, 9999}
SENTINELS_CO = {-9999, -999, -99, 9999}
FLATLINE_HOURS = 6  # >= 6 identical consecutive pollutant readings = stuck sensor

# QC flags: pollutant analyser state. Meteorology (Vaisala WXT536) is a separate instrument,
# so analyser-only states (calibration/maintenance/warm-up) do not invalidate weather data.
QC_OK_POLL = {"VALID"}
QC_OK_MET = {"VALID", "CALIBRATING", "MAINTENANCE", "WARMUP"}

log_rows = []


def log(station, rule, column, n, note=""):
    if n:
        log_rows.append({"station": station, "rule": rule, "column": column, "n_affected": int(n), "note": note})


# =====================================================================================
# 1. DIMENSION TABLE (sites + sensors + hospitals + metadata)
# =====================================================================================
sites = pd.read_csv(RAW / "sites.csv")
sensors = pd.read_csv(RAW / "sensors.csv")
hosp = pd.read_csv(RAW / "hospitals.csv")
mdates = pd.read_csv(RAW / "metadata" / "metadata_dates.csv")
msens = pd.read_csv(RAW / "metadata" / "metadata_sensors.csv")
# allowed QC categories as documented in metadata_sensors.csv (row "Quality Control Flag")
_qc_units = msens.loc[msens["Header"].str.strip() == "qc_flag", "Units"].iat[0]
QC_DOCUMENTED = {x.strip().upper() for x in _qc_units[_qc_units.find("(") + 1:_qc_units.find(")")].split(",")}

ISLAND = {
    "IDP-01": "Sumatera", "MDN-01": "Sumatera", "KTB-01": "Sumatera", "PKU-01": "Sumatera",
    "BTM-01": "Sumatera", "JMB-01": "Sumatera", "JMB-02": "Sumatera", "BGL-01": "Sumatera",
    "PLB-01": "Sumatera", "PSW-01": "Sumatera",
    "JKT-01": "Jawa", "JKT-02": "Jawa", "JKT-03": "Jawa", "BGR-01": "Jawa", "BGR-02": "Jawa",
    "YKY-01": "Jawa", "MLG-01": "Jawa",
    "KTG-01": "Kalimantan", "KTG-02": "Kalimantan", "PKN-01": "Kalimantan", "STG-01": "Kalimantan",
    "SM2-01": "Kalimantan", "BJB-01": "Kalimantan",
    "MRS-01": "Sulawesi", "PLU-01": "Sulawesi",
    "SRG-01": "Papua", "MER-01": "Papua",
}


def site_category(t):
    t = t.lower()
    if "peat" in t:
        return "Gambut / Karhutla"
    if "industrial" in t:
        return "Industri"
    if "traffic" in t or "roadside" in t:
        return "Tepi Jalan (Lalu Lintas)"
    if "clean" in t or "regional" in t or "remote" in t:
        return "Latar Bersih"
    return "Perkotaan"


dim = sites.copy()
dim["station"] = dim["station_code"].str.replace("AQMS-", "", regex=False)
dim = dim.merge(sensors.drop(columns=["latitude", "longitude", "region_group"]), on="location_id", how="left")
dim["hospital_id"] = "RS-XXX-" + dim["sensor_id"].str[-2:]  # SENS-0NN <-> RS-XXX-NN (booklet section E)
dim = dim.merge(hosp.rename(columns={"kota_kabupaten": "rs_kota_kabupaten", "kecamatan": "rs_kecamatan",
                                     "provinsi": "rs_provinsi"}), on="hospital_id", how="left")
dim = dim.merge(mdates[["location_id", "date_start", "date_end", "nominal_resolution"]], on="location_id", how="left")
dim["island"] = dim["station"].map(ISLAND)
dim["site_category"] = dim["site_type"].map(site_category)
dim["unit_in_raw_file"] = dim["pm25_unit"]
# region_group in source is inconsistent (e.g. JMB-02 = "Sumatera", MER-01 = "Papua"): use province instead
dim["region_group_fixed"] = dim["provinsi"]

# =====================================================================================
# 2. AQMS HOURLY CLEANING
# =====================================================================================
NUM_TOKEN = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$")


def to_num(s: pd.Series):
    """Strict numeric parse; returns (values, n_bad_tokens)."""
    s = s.astype("string").str.strip()
    ok = s.str.match(NUM_TOKEN.pattern, na=False)
    out = pd.to_numeric(s.where(ok), errors="coerce")
    n_bad = int((~ok & s.notna() & (s != "")).sum())
    return out.astype(float), n_bad


def circ_mean_deg(x):
    x = x.dropna()
    if x.empty:
        return np.nan
    r = np.deg2rad(x)
    return (np.rad2deg(np.arctan2(np.sin(r).mean(), np.cos(r).mean())) + 360) % 360


hourly_frames = []
station_quality = []

for f in sorted(RAW.glob("*_AQMS.csv")):
    st = f.name.split("_")[0]
    raw = pd.read_csv(f, dtype=str, keep_default_na=False)
    n_raw = len(raw)
    _undoc = raw["qc_flag"].str.strip().str.upper()
    _undoc = _undoc[~_undoc.isin(QC_DOCUMENTED)]
    log(st, f"qc_flag di luar kategori metadata_sensors ({', '.join(sorted(QC_DOCUMENTED))}) -> diperlakukan tidak valid",
        "qc_flag", len(_undoc), ", ".join(f"{k}:{v}" for k, v in _undoc.value_counts().items()))
    d = pd.DataFrame({"measurement_id": raw["measurement_id"], "sensor_id": raw["sensor_id"],
                      "qc_flag": raw["qc_flag"].str.strip().str.upper()})

    # ---- 2a. timestamps ----
    t0 = pd.to_datetime(raw["timestamp_start"], format="mixed", errors="coerce")
    t1 = pd.to_datetime(raw["timestamp_end"], format="mixed", errors="coerce")
    d["dur_min"] = (t1 - t0).dt.total_seconds() / 60
    bad_ts = t0.isna() | t1.isna() | (t0 < PERIOD_START - pd.Timedelta("1h")) | (t0 > PERIOD_END + pd.Timedelta("1h")) | (d["dur_min"] <= 0)
    log(st, "Timestamp invalid (unparseable / 1970 epoch / di luar periode / end<=start) -> baris dibuang", "timestamp", bad_ts.sum())
    drift = (t0 - t0.dt.round("h")).abs()
    log(st, "Clock drift (offset menit/detik dari jam bulat) -> dibulatkan ke jam terdekat", "timestamp",
        int((drift > pd.Timedelta(0)).sum()), f"median offset {drift.median()}")
    d["t0"] = t0

    # ---- 2b. numeric parsing + unit conversion ----
    for p in POLL:
        if f"{p}_ug_m3" in raw.columns:
            v, nb = to_num(raw[f"{p}_ug_m3"])
        else:
            v, nb = to_num(raw[f"{p}_ppm"])
            v = v * PPM_FACTOR[p]
            log(st, f"Konversi satuan ppm -> ug/m3 (x{PPM_FACTOR[p]:.1f})", f"{p}_ppm", v.notna().sum())
        log(st, "Token non-numerik (kode error, #VALUE!, inf) -> NaN", PCOL[p], nb)
        d[PCOL[p]] = v
    for m in MET:
        v, nb = to_num(raw[m])
        log(st, "Token non-numerik (kode error, #VALUE!, inf) -> NaN", m, nb)
        d[m] = v

    d = d[~bad_ts].copy()

    # ---- 2c. sentinel & physical range ----
    for c, (lo, hi) in LIMITS.items():
        x = d[c]
        sent = x.isin(SENTINELS_CO if c == "co_ug_m3" else SENTINELS)
        rng = (~sent) & x.notna() & ((x < lo) | (x > hi) | ~np.isfinite(x))
        log(st, "Nilai sentinel kode logger (-9999/-999/-99/999/999.9/9999) -> NaN", c, sent.sum())
        log(st, f"Di luar batas fisik [{lo}, {hi}] -> NaN", c, rng.sum())
        d.loc[sent | rng, c] = np.nan

    # ---- 2d. QC flag filtering ----
    bad_p = ~d["qc_flag"].isin(QC_OK_POLL)
    bad_m = ~d["qc_flag"].isin(QC_OK_MET)
    for c in PCOL.values():
        log(st, "QC flag bukan VALID -> polutan dibuang", c, (bad_p & d[c].notna()).sum(),
            ", ".join(sorted(d.loc[bad_p, "qc_flag"].unique())))
        d.loc[bad_p, c] = np.nan
    for c in MET:
        log(st, "QC flag SUSPECT/MISSING/error -> meteorologi dibuang", c, (bad_m & d[c].notna()).sum())
        d.loc[bad_m, c] = np.nan

    # ---- 2e. PM2.5 > PM10 (physically impossible) ----
    inc = d["pm25_ug_m3"] > d["pm10_ug_m3"]
    log(st, "PM2.5 > PM10 (tidak konsisten fisik) -> keduanya NaN", "pm25/pm10", inc.sum())
    d.loc[inc, ["pm25_ug_m3", "pm10_ug_m3"]] = np.nan

    # ---- 2f. sub-hourly -> hourly (PLB-01 Sep-Oct 15-minute windows) ----
    d["datetime"] = d["t0"].dt.floor("h") if (d["dur_min"] < 60).any() else d["t0"].dt.round("h")
    sub = d["dur_min"] < 60
    if sub.any():
        log(st, "Jendela 15 menit diagregasi ke rata-rata jam (min. 3 dari 4 valid)", "all", sub.sum())
        hourly_part = d[~sub]
        s = d[sub]
        g = s.groupby("datetime")
        agg = g[list(PCOL.values()) + ["temperature_c", "humidity_pct", "wind_speed_ms"]].mean()
        cnt = g[list(PCOL.values()) + ["temperature_c", "humidity_pct", "wind_speed_ms"]].count()
        agg = agg.where(cnt >= 3)
        agg["wind_direction_deg"] = g["wind_direction_deg"].apply(circ_mean_deg).where(g["wind_direction_deg"].count() >= 3)
        agg["qc_flag"] = np.where(cnt["pm25_ug_m3"] >= 3, "VALID", "INSUFFICIENT_SUBHOURLY")
        agg["measurement_id"] = g["measurement_id"].first()
        agg["sensor_id"] = g["sensor_id"].first()
        agg = agg.reset_index()
        d = pd.concat([hourly_part, agg], ignore_index=True)

    # ---- 2g. duplicates after rounding: keep the row with most valid pollutant values ----
    d["_nvalid"] = d[list(PCOL.values())].notna().sum(axis=1)
    d = d.sort_values(["datetime", "_nvalid"], ascending=[True, False])
    dup = d.duplicated("datetime", keep="first")
    log(st, "Duplikat timestamp setelah pembulatan -> simpan baris paling lengkap", "datetime", dup.sum())
    d = d[~dup]

    # ---- 2h. flatline (stuck sensor) on pollutants ----
    d = d.set_index("datetime").reindex(HOURS)
    d.index.name = "datetime"
    for c in PCOL.values():
        x = d[c]
        grp = (x != x.shift()).cumsum()
        run = x.groupby(grp).transform("size")
        flat = x.notna() & (run >= FLATLINE_HOURS)
        if flat.any():
            vals = x[flat].round(4).value_counts().head(3).to_dict()
            log(st, f"Flatline >= {FLATLINE_HOURS} jam nilai identik (sensor macet) -> NaN", c, flat.sum(), f"nilai: {vals}")
        d.loc[flat, c] = np.nan

    # ---- 2i. isolated single-hour spikes (pollutants) ----
    # Strict on purpose: BOTH adjacent hours must exist and be < 1/5 of the value. A smoke front that
    # arrives and stays (e.g. SM2 47 -> 235 -> 261) is real signal and must not be removed.
    for c in PCOL.values():
        x = d[c]
        prev, nxt = x.shift(1), x.shift(-1)
        spike = x.notna() & prev.notna() & nxt.notna() & (x > 5 * np.maximum(prev, nxt)) & \
            ((x - np.maximum(prev, nxt)) > 200)
        log(st, "Spike terisolasi 1 jam (>5x kedua jam tetangga & selisih >200) -> NaN", c, spike.sum())
        d.loc[spike, c] = np.nan

    # ---- 2j. missing hours ----
    no_rec = d["qc_flag"].isna()
    log(st, "Jam tanpa rekaman di file asli (gap) -> dibiarkan kosong; tidak ditambahkan ke output & tidak diimputasi", "datetime", no_rec.sum())
    d["qc_flag"] = d["qc_flag"].fillna("NO_RECORD")

    d["station"] = st
    d = d.reset_index()
    cols = ["station", "datetime", "qc_flag"] + list(PCOL.values()) + MET
    d = d[cols]
    hourly_frames.append(d)

    station_quality.append({
        "station": st, "raw_rows": n_raw, "expected_hours": len(HOURS),
        "hours_with_record": int((d.qc_flag != "NO_RECORD").sum()),
        "hours_valid_pm25": int(d.pm25_ug_m3.notna().sum()),
        "completeness_pm25_pct": round(d.pm25_ug_m3.notna().mean() * 100, 1),
        "completeness_temp_pct": round(d.temperature_c.notna().mean() * 100, 1),
    })

hourly = pd.concat(hourly_frames, ignore_index=True)
quality = pd.DataFrame(station_quality)

# station-level exclusion
EXCLUDE = {"JMB-02": "Sensor DEFECTIVE (status_operasional); hanya 0,5% jam valid; timestamp rusak. Dikeluarkan dari analisis."}
quality["status_operasional"] = quality["station"].map(dim.set_index("station")["status_operasional"])
quality["used_in_analysis"] = ~quality["station"].isin(EXCLUDE)
quality["note"] = quality["station"].map(EXCLUDE).fillna("")
quality.loc[(quality.completeness_pm25_pct < 75) & quality.used_in_analysis, "note"] = \
    "Kelengkapan PM2.5 < 75%: rata-rata tahunan dilaporkan dengan catatan (data tidak representatif penuh)"

# =====================================================================================
# 3. TIME FEATURES + DAILY / MONTHLY AGGREGATES (75% completeness rule)
# =====================================================================================
hourly = hourly.merge(dim[["station", "island", "provinsi", "site_category", "site_type"]], on="station", how="left")
dt = hourly["datetime"]
hourly["date"] = dt.dt.normalize()
hourly["year"] = dt.dt.year
hourly["month"] = dt.dt.month
hourly["hour"] = dt.dt.hour
hourly["dow"] = dt.dt.dayofweek
hourly["is_weekend"] = hourly["dow"] >= 5
# Indonesia monsoon seasons: dry (kemarau) May-Oct, wet (hujan) Nov-Apr
hourly["season"] = np.where(hourly["month"].between(5, 10), "Kemarau (Mei-Okt)", "Hujan (Nov-Apr)")
hourly["used_in_analysis"] = ~hourly["station"].isin(EXCLUDE)

# rolling 8-hour CO and O3 (for ISPU & baku mutu 8-jam)
hourly = hourly.sort_values(["station", "datetime"])
for c in ["co_ug_m3", "o3_ug_m3"]:
    hourly[c.replace("_ug_m3", "_8h")] = hourly.groupby("station")[c].transform(
        lambda s: s.rolling(8, min_periods=6).mean())

# The full hourly grid is used INTERNALLY only (so rolling windows, lags and runs never bridge a gap).
# Hours/days that have no record in the original files are NOT written to the outputs: nothing is added.
hourly["has_record"] = hourly["qc_flag"] != "NO_RECORD"
agg_mean = {c: "mean" for c in list(PCOL.values()) + ["temperature_c", "humidity_pct", "wind_speed_ms"]}
g = hourly.groupby(["station", "date"])
daily = g.agg(agg_mean)
daily["n_hours_recorded"] = g["has_record"].sum()
cnt = g[list(PCOL.values()) + ["temperature_c", "humidity_pct", "wind_speed_ms"]].count()
_nrec = daily.pop("n_hours_recorded")
daily = daily.where(cnt >= 18)  # >= 18 of 24 hours
daily["n_hours_recorded"] = _nrec
daily.columns = [c.replace("_ug_m3", "") for c in daily.columns]
daily["pm25_valid_hours"] = cnt["pm25_ug_m3"]
# daily maxima only on days that pass the same >= 18 valid-hour rule (otherwise a day with 2 valid
# hours would get an ISPU from one gas and look artificially "Baik")
daily["co_8h_max"] = g["co_8h"].max().where(cnt["co_ug_m3"] >= 18)
daily["o3_8h_max"] = g["o3_8h"].max().where(cnt["o3_ug_m3"] >= 18)
daily["o3_1h_max"] = g["o3_ug_m3"].max().where(cnt["o3_ug_m3"] >= 18)
daily["no2_1h_max"] = g["no2_ug_m3"].max().where(cnt["no2_ug_m3"] >= 18)
daily["so2_1h_max"] = g["so2_ug_m3"].max().where(cnt["so2_ug_m3"] >= 18)
daily["pm25_1h_max"] = g["pm25_ug_m3"].max().where(cnt["pm25_ug_m3"] >= 18)
daily["wind_direction_deg"] = g["wind_direction_deg"].apply(circ_mean_deg)
daily = daily.reset_index()

# ---- ISPU (Permen LHK No. 14/2020) ----
ISPU_I = [0, 50, 100, 200, 300, 500]
ISPU_BP = {  # breakpoint concentrations (ug/m3)
    "pm10": [0, 50, 150, 350, 420, 500],      # 24 jam
    "pm25": [0, 15.5, 55.4, 150.4, 250.4, 500],  # 24 jam
    "so2": [0, 52, 180, 400, 800, 1200],       # 24 jam
    "co": [0, 4000, 8000, 15000, 30000, 45000],  # 8 jam (maks harian)
    "o3": [0, 120, 235, 400, 800, 1000],       # 1 jam (maks harian)
    "no2": [0, 80, 200, 1130, 2260, 3000],     # 1 jam (maks harian)
}
ISPU_SRC = {"pm10": "pm10", "pm25": "pm25", "so2": "so2", "co": "co_8h_max", "o3": "o3_1h_max", "no2": "no2_1h_max"}


def ispu(x, bp):
    if pd.isna(x):
        return np.nan
    for i in range(1, len(bp)):
        if x <= bp[i]:
            return ISPU_I[i - 1] + (ISPU_I[i] - ISPU_I[i - 1]) / (bp[i] - bp[i - 1]) * (x - bp[i - 1])
    return 500.0


for p, c in ISPU_SRC.items():
    daily[f"ispu_{p}"] = daily[c].map(lambda v, b=ISPU_BP[p]: ispu(v, b)).round(0)
ispu_cols = [f"ispu_{p}" for p in ISPU_SRC]
# PM2.5 is the dominant ISPU pollutant at every station; without it the daily ISPU would be biased low
daily["ispu"] = daily[ispu_cols].max(axis=1).where(daily["ispu_pm25"].notna())
_has = daily["ispu"].notna()
daily["ispu_dominant"] = None
daily.loc[_has, "ispu_dominant"] = daily.loc[_has, ispu_cols].fillna(-1).idxmax(axis=1).str.replace("ispu_", "")


def ispu_cat(v):
    if pd.isna(v):
        return np.nan
    if v <= 50:
        return "1 Baik"
    if v <= 100:
        return "2 Sedang"
    if v <= 200:
        return "3 Tidak Sehat"
    if v <= 300:
        return "4 Sangat Tidak Sehat"
    return "5 Berbahaya"


daily["ispu_kategori"] = daily["ispu"].map(ispu_cat)

# ---- Baku mutu PP 22/2021 (Lampiran VII) & WHO AQG 2021 daily exceedance flags ----
daily["exc_pm25_bm"] = daily["pm25"] > 55      # PP22: 24 jam 55
daily["exc_pm10_bm"] = daily["pm10"] > 75      # PP22: 24 jam 75
daily["exc_so2_bm"] = daily["so2"] > 75        # PP22: 24 jam 75
daily["exc_no2_bm"] = daily["no2"] > 65        # PP22: 24 jam 65
daily["exc_co_bm"] = daily["co_8h_max"] > 4000  # PP22: 8 jam 4000
daily["exc_o3_bm"] = daily["o3_8h_max"] > 100  # PP22: 8 jam 100
daily["exc_pm25_who"] = daily["pm25"] > 15     # WHO 24h 15
daily["exc_pm10_who"] = daily["pm10"] > 45     # WHO 24h 45
for c in [c for c in daily.columns if c.startswith("exc_")]:
    src = {"pm25": "pm25", "pm10": "pm10", "so2": "so2", "no2": "no2", "co": "co_8h_max", "o3": "o3_8h_max"}[c.split("_")[1]]
    daily[c] = daily[c].where(daily[src].notna())

daily = daily.merge(dim[["station", "island", "provinsi", "site_category", "site_type", "hospital_id"]], on="station", how="left")
d0 = daily["date"]
daily["year"] = d0.dt.year
daily["month"] = d0.dt.month
daily["dow"] = d0.dt.dayofweek
daily["is_weekend"] = daily["dow"] >= 5
daily["season"] = np.where(daily["month"].between(5, 10), "Kemarau (Mei-Okt)", "Hujan (Nov-Apr)")
daily["used_in_analysis"] = ~daily["station"].isin(EXCLUDE)

# ---- haze episode detection (kabut asap) ----
# Episode day: daily PM2.5 > 55.4 (ISPU Tidak Sehat) AND > 2x station wet-season median (separates
# episodic smoke from chronic urban pollution). Episode = run of >= 3 consecutive episode days.
wet_med = daily[daily.season.str.startswith("Hujan")].groupby("station")["pm25"].median()
daily["pm25_wet_median"] = daily["station"].map(wet_med)
daily["haze_day_candidate"] = (daily["pm25"] > 55.4) & (daily["pm25"] > 2 * daily["pm25_wet_median"])
daily = daily.sort_values(["station", "date"])
daily["_run"] = (daily["haze_day_candidate"] != daily.groupby("station")["haze_day_candidate"].shift()).cumsum()
runlen = daily.groupby("_run")["haze_day_candidate"].transform("size")
daily["haze_episode_day"] = daily["haze_day_candidate"] & (runlen >= 3) & daily["used_in_analysis"]
daily["haze_episode_id"] = np.where(daily["haze_episode_day"], daily["station"] + "#" + daily["_run"].astype(str), None)
daily = daily.drop(columns=["_run"])

# monthly (>= 75% valid days)
gm = daily.groupby(["station", pd.Grouper(key="date", freq="MS")])
monthly = gm[["pm25", "pm10", "so2", "co", "o3", "no2", "temperature_c", "humidity_pct", "wind_speed_ms", "ispu"]].mean()
mcnt = gm["pm25"].count()
ndays = gm["pm25"].size()
monthly["pm25_valid_days"] = mcnt
monthly["days_in_period"] = ndays  # calendar days of the month inside the observation period
monthly["pm25_complete"] = (mcnt / ndays) >= 0.75
monthly["exc_pm25_bm_days"] = gm["exc_pm25_bm"].sum()
monthly["haze_days"] = gm["haze_episode_day"].sum()
monthly = monthly.reset_index().rename(columns={"date": "month_start"})
monthly = monthly.merge(dim[["station", "island", "provinsi", "site_category"]], on="station", how="left")

# =====================================================================================
# 4. HEALTH DATA CLEANING
# =====================================================================================
h = pd.read_csv(RAW / "HLT-01_health_outcomes_daily.csv")
n0 = len(h)
h["date"] = pd.to_datetime(h["date"], errors="coerce")
cnt_cols = ["resp_admissions_under5", "resp_admissions_over60", "asthma_emergency_cases",
            "copd_admissions", "resp", "cvd", "death"]
out_window = (h["date"] < PERIOD_START.normalize()) | (h["date"] > PERIOD_END.normalize()) | h["date"].isna()
log("HLT-01", "Tanggal di luar periode AQMS (2023-12-31) -> dibuang", "date", out_window.sum())
h = h[~out_window].copy()
dow_bad = h["date"].dt.day_name() != h["dow"]
log("HLT-01", "Nama hari tidak sesuai tanggal", "dow", dow_bad.sum())
log("HLT-01", "Kolom 'time' dihitung per-RS (tidak seragam) -> diganti day_index global", "time",
    int((h["time"] != (h["date"] - PERIOD_START).dt.days + 1).sum()))
h["day_index"] = (h["date"] - PERIOD_START).dt.days + 1
for c in cnt_cols:
    neg = h[c] < 0
    log("HLT-01", "Hitungan negatif -> NaN", c, neg.sum())
    h.loc[neg, c] = np.nan
    h[c] = h[c].round().astype("Int64")
# Per QnA panitia: `resp` = rawat inap gangguan pernapasan UMUM (semua umur, semua jenis), so it should be
# >= ISPA balita + ISPA lansia (both are subsets). Rows violating this are flagged, never altered or dropped.
h["flag_resp_lt_u5_o60"] = (h["resp"] < h["resp_admissions_under5"] + h["resp_admissions_over60"]).astype(bool)
log("HLT-01", "resp (pernapasan umum semua umur) < ISPA balita + ISPA lansia: ditandai, tidak diubah/dibuang", "resp",
    h["flag_resp_lt_u5_o60"].sum())
dups = h.duplicated(["date", "hospital_id"])
log("HLT-01", "Duplikat (date, hospital_id) -> dibuang", "date,hospital_id", dups.sum())
h = h[~dups].drop(columns=["time"])
h = h.merge(hosp, on="hospital_id", how="left")
h["station"] = h["hospital_id"].map(dict(zip(dim["hospital_id"], dim["station"])))
# Each hospital keeps the station the booklet pairs it with. RS-XXX-27's station (JMB-02) is defective, so it
# has no exposure data; it is NOT given a substitute station (that would add data the dataset does not have).
h["exposure_station"] = h["station"]
log("HLT-01", "RS-XXX-27: stasiun pasangan JMB-02 defective -> tanpa data paparan, tidak dimodelkan (tanpa proksi)",
    "exposure_station", (h["station"] == "JMB-02").sum())
h["island"] = h["station"].map(ISLAND)
h["resp_per100beds"] = h["resp"] / h["kapasitas_tempat_tidur"] * 100

# =====================================================================================
# 5. MERGED HEALTH x AIR QUALITY (with exposure lags 0-7)
# =====================================================================================
aq = daily[["station", "date", "pm25", "pm10", "so2", "co", "no2", "o3", "ispu", "ispu_kategori",
            "temperature_c", "humidity_pct", "wind_speed_ms", "haze_episode_day"]].copy()
aq = aq.sort_values(["station", "date"])
for L in range(1, 8):
    aq[f"pm25_lag{L}"] = aq.groupby("station")["pm25"].shift(L)
aq["pm25_ma02"] = aq[["pm25", "pm25_lag1", "pm25_lag2"]].mean(axis=1, skipna=False)
aq["pm25_ma07"] = aq[["pm25"] + [f"pm25_lag{L}" for L in range(1, 8)]].mean(axis=1, skipna=True)
aq = aq.rename(columns={"station": "exposure_station", "temperature_c": "aq_temperature_c",
                        "humidity_pct": "aq_humidity_pct", "wind_speed_ms": "aq_wind_speed_ms"})
merged = h.merge(aq, on=["exposure_station", "date"], how="left")

# =====================================================================================
# 6. WRITE OUTPUTS
# =====================================================================================
cleaning_log = pd.DataFrame(log_rows)
# drop the internal-grid rows that have no record in the original files
hourly_out = hourly[hourly["has_record"]].drop(columns=["co_8h", "o3_8h", "has_record"])
daily = daily[daily["n_hours_recorded"] > 0]

hourly_out.to_csv(OUT / "aqms_hourly_clean.csv", index=False)
hourly_out.to_parquet(OUT / "aqms_hourly_clean.parquet", index=False)
daily.to_csv(OUT / "aqms_daily.csv", index=False)
monthly.to_csv(OUT / "aqms_monthly.csv", index=False)
h.to_csv(OUT / "health_daily_clean.csv", index=False)
merged.to_csv(OUT / "health_aq_daily_merged.csv", index=False)
dim.to_csv(OUT / "dim_station.csv", index=False)
cleaning_log.to_csv(OUT / "cleaning_log.csv", index=False)
quality.to_csv(OUT / "data_quality_station.csv", index=False)
# documentation of the ppm -> ug/m3 conversion (QnA panitia: method is the participant's choice, must be
# scientifically grounded, applied consistently and explained in the report)
pd.DataFrame([
    {"parameter": p, "basis_ppm": "ppmv (fraksi volume gas)" if p in ("so2", "co", "o3", "no2") else "ppmw (fraksi massa terhadap udara)",
     "massa_molar_g_per_mol": MW[p], "volume_molar_L": MOLAR_VOL, "faktor_ug_m3_per_ppm": round(PPM_FACTOR[p], 2),
     "rumus": f"ug/m3 = ppm x {MW[p]} x 1000 / {MOLAR_VOL}",
     "keterangan": "berat molekul gas" if p in ("so2", "co", "o3", "no2") else
                   "massa molar udara kering 28,97 -> setara ppm(massa) x densitas udara 1,185 kg/m3 (25 C, 1 atm)",
     "stasiun_terdampak": "BJB-01, MDN-01, PSW-01"} for p in POLL
]).to_csv(OUT / "unit_conversion_ppm.csv", index=False)

print("hourly", hourly_out.shape, "daily", daily.shape, "monthly", monthly.shape)
print("health", h.shape, "(raw", n0, ") merged", merged.shape)
print(quality.to_string())
print("\nCleaning log rows:", len(cleaning_log))
