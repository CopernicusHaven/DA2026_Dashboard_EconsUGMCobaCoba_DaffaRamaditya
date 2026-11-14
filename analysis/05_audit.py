"""
Compliance audit: verifies, from the files themselves, that the outputs follow the booklet, handbook and QnA.
Writes output/audit/audit_checks.csv. Run: python3 analysis/05_audit.py
"""
import hashlib
import re
from pathlib import Path
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
CLEAN = BASE / "output" / "clean"
TAB = BASE / "output" / "analysis"
OUTD = BASE / "output" / "audit"
OUTD.mkdir(parents=True, exist_ok=True)
ORIG = Path.home() / "Downloads" / "Dataset DA Gelar Rasa 2026"
rows = []


def check(area, item, ok, detail=""):
    rows.append({"area": area, "pemeriksaan": item, "status": "LULUS" if ok else "GAGAL", "detail": detail})


# ---------------- A. original files untouched ----------------
raw_files = sorted([p for p in BASE.glob("*.csv")] + list((BASE / "metadata").glob("*.csv")))
md5 = lambda p: hashlib.md5(p.read_bytes()).hexdigest()
same = [md5(p) == md5(ORIG / p.relative_to(BASE)) for p in raw_files if (ORIG / p.relative_to(BASE)).exists()]
check("Handbook/User", "33 file asli tidak diubah (MD5 = unduhan asli)", len(raw_files) == 33 and all(same) and len(same) == 33,
      f"{sum(same)}/{len(raw_files)} identik")

# ---------------- B. only the provided dataset is read ----------------
reads = set()
for py in (BASE / "analysis").glob("0[1-4]_*.py"):
    reads |= set(re.findall(r'read_(?:csv|parquet|excel)\(\s*([^,\)]+)', py.read_text()))
external = [r for r in reads if "http" in r or "Downloads" in r]
check("Handbook", "Hanya dataset panitia yang dibaca (tanpa dataset eksternal)", not external,
      "input: 33 file panitia + tabel turunan output/clean & output/analysis")

# ---------------- C. booklet station table mapping ----------------
BOOK = ["JKT-01", "JKT-02", "JKT-03", "KTG-01", "KTG-02", "BGR-01", "BGR-02", "YKY-01", "IDP-01", "KTB-01", "PKU-01",
        "JMB-01", "BTM-01", "BGL-01", "SRG-01", "MLG-01", "MRS-01", "PLU-01", "STG-01", "PKN-01", "PLB-01", "PSW-01",
        "MER-01", "MDN-01", "SM2-01", "BJB-01", "JMB-02"]
dim = pd.read_csv(CLEAN / "dim_station.csv").set_index("station")
ok_map = all(dim.loc[s, "sensor_id"] == f"SENS-{i:03d}" and dim.loc[s, "hospital_id"] == f"RS-XXX-{i:02d}"
             for i, s in enumerate(BOOK, 1))
check("Booklet", "Pemetaan stasiun-sensor-RS sama dengan tabel Daftar Stasiun booklet (bagian E)", ok_map, "27/27 cocok" if ok_map else "")
sens_ok = all(pd.read_csv(next(BASE.glob(f"{s}_*_AQMS.csv")), usecols=["sensor_id"]).sensor_id.eq(f"SENS-{i:03d}").all()
              for i, s in enumerate(BOOK, 1))
check("Booklet", "sensor_id di setiap file AQMS sesuai booklet", sens_ok)

# ---------------- D/E. no added records, no invented values ----------------
H = pd.read_parquet(CLEAN / "aqms_hourly_clean.parquet")
_ct = pd.read_csv(CLEAN / "unit_conversion_ppm.csv").set_index("parameter")
# exact factor (the documentation table shows it rounded to 2 decimals)
conv = _ct["massa_molar_g_per_mol"] * 1000 / _ct["volume_molar_L"]
POLL = ["pm25", "pm10", "so2", "co", "o3", "no2"]
MET = ["temperature_c", "humidity_pct", "wind_speed_ms", "wind_direction_deg"]
added_rows, bad_vals, checked = 0, 0, 0
for s in BOOK:
    raw = pd.read_csv(next(BASE.glob(f"{s}_*_AQMS.csv")), dtype=str, keep_default_na=False)
    t0 = pd.to_datetime(raw.timestamp_start, format="mixed", errors="coerce")
    sub = (pd.to_datetime(raw.timestamp_end, format="mixed", errors="coerce") - t0).dt.total_seconds() < 3600
    key = t0.dt.floor("h") if sub.any() else t0.dt.round("h")
    h = H[H.station == s].set_index("datetime")
    added_rows += int((~h.index.isin(set(key.dropna()))).sum())
    if sub.any():  # aggregated 15-min hours are means of raw values -> checked on the hourly (60-min) rows only
        raw, key = raw[~sub], key[~sub]
    r = raw.assign(datetime=key.values).drop_duplicates("datetime").set_index("datetime")
    common = h.index.intersection(r.index)
    for p in POLL:
        col = f"{p}_ug_m3" if f"{p}_ug_m3" in r else f"{p}_ppm"
        f = conv[p] if col.endswith("_ppm") else 1.0
        rv = pd.to_numeric(r.loc[common, col], errors="coerce") * f
        cv = h.loc[common, f"{p}_ug_m3"]
        m = cv.notna()
        checked += int(m.sum())
        bad_vals += int((~np.isclose(cv[m], rv[m], rtol=1e-6, equal_nan=False)).sum())
    for c in MET:
        rv = pd.to_numeric(r.loc[common, c], errors="coerce")
        cv = h.loc[common, c]
        m = cv.notna()
        checked += int(m.sum())
        bad_vals += int((~np.isclose(cv[m], rv[m], rtol=1e-6)).sum())
check("User (tanpa tambah data)", "Tidak ada jam baru: setiap jam di data bersih ada di file asli", added_rows == 0,
      f"{len(H):,} jam bersih; jam tambahan = {added_rows}")
check("User (tanpa tambah data)", "Tidak ada nilai rekaan: setiap nilai bersih = nilai asli (× faktor ppm bila ada)", bad_vals == 0,
      f"{checked:,} nilai dicek; selisih = {bad_vals}")
check("User (tanpa tambah data)", "Jam yang hilang (MDN-01) tidak diisi", int((H.station == "MDN-01").sum()) == 20800,
      f"MDN-01 bersih {(H.station == 'MDN-01').sum():,} jam = 20.800 baris asli")

D = pd.read_csv(CLEAN / "aqms_daily.csv", parse_dates=["date"])
check("User (tanpa tambah data)", "Tidak ada hari tanpa rekaman di tabel harian", (D.n_hours_recorded > 0).all(),
      f"{len(D):,} hari-stasiun")

# ---------------- G/H. health ----------------
hr = pd.read_csv(BASE / "HLT-01_health_outcomes_daily.csv", parse_dates=["date"])
hm = pd.read_csv(CLEAN / "health_aq_daily_merged.csv", parse_dates=["date"])
cnt = ["resp_admissions_under5", "resp_admissions_over60", "asthma_emergency_cases", "copd_admissions", "resp", "cvd", "death"]
j = hm.merge(hr, on=["date", "hospital_id"], suffixes=("", "_raw"))
eq = all(np.allclose(j[c].astype(float), j[c + "_raw"].astype(float)) for c in cnt)
check("User (tanpa tambah data)", "Angka kasus kesehatan identik dengan file asli", eq and len(hm) == len(hr) - 5,
      f"{len(hm):,} baris = {len(hr):,} asli − 5 baris 2023-12-31")
rs27 = hm[hm.hospital_id == "RS-XXX-27"]
check("User (tanpa tambah data)", "RS-XXX-27 tanpa data paparan pinjaman (tanpa proksi)",
      rs27.pm25.isna().all() and (rs27.exposure_station == "JMB-02").all())
net = pd.read_csv(TAB / "o5_network_station_assessment.csv", index_col=0)
check("User (tanpa tambah data)", "JMB-02 tidak diberi nilai polusi pinjaman di skor jaringan",
      pd.isna(net.loc["JMB-02", "pm25_mean"]) and pd.isna(net.loc["JMB-02", "haze_days"]))

# ---------------- QnA ----------------
f_ok = all(abs(conv[p] - m * 1000 / 24.45) < 0.05 for p, m in
           {"so2": 64.066, "co": 28.010, "o3": 47.998, "no2": 46.0055, "pm25": 28.97, "pm10": 28.97}.items())
check("QnA 1 & 3", "Konversi ppm: satu rumus konsisten (ppm × M × 1000 / 24,45), terdokumentasi", f_ok,
      "tabel unit_conversion_ppm + subbab 2.3.1 laporan")
ppm_cols = [c for c in H.columns if c.endswith("_ppm")]
check("QnA 1 & 3", "Tidak ada kolom ppm tersisa; semua polutan dalam µg/m³", not ppm_cols)
lab = pd.read_csv(TAB / "o4_lag_rr_all_outcomes.csv")
check("QnA 2", "`resp` diperlakukan sebagai pernapasan umum semua umur & jenis",
      (lab.loc[lab.outcome == "resp", "outcome_label"] == "Pernapasan umum (semua umur)").all())
check("QnA 2", "`resp_admissions_over60` diperlakukan sebagai ISPA lansia",
      (lab.loc[lab.outcome == "resp_admissions_over60", "outcome_label"] == "ISPA lansia (>60 th)").all())

# ---------------- model sanity ----------------
check("Kualitas analisis", "Semua model kesehatan konvergen (dispersi wajar)", lab.dispersion.max() < 5,
      f"dispersi maks {lab.dispersion.max():.2f}")

# ---------------- report ----------------
rep = (BASE / "output" / "LAPORAN_ANALISIS.md").read_text()
heads = ["BAB I PENDAHULUAN", "BAB II DESAIN IMPLEMENTASI", "BAB III HASIL DAN ANALISIS", "BAB IV PENUTUP",
         "DAFTAR PUSTAKA", "LAMPIRAN", "2.1 Karakteristik Dataset", "2.2 Tools", "2.3 Preprocessing",
         "2.4 Proses Desain Visualisasi", "3.1 Exploratory Data Analysis", "3.2 Tampilan Dashboard",
         "3.3 Pembahasan", "4.1 Kesimpulan", "4.2 Rekomendasi"]
miss = [x for x in heads if x not in rep]
check("Handbook (template)", "Struktur bab mengikuti template laporan", not miss, "kurang: " + ", ".join(miss) if miss else "lengkap")
imgs = re.findall(r"\((figures/[^)]+\.png)\)", rep)
check("Handbook (template)", "Semua gambar di laporan tersedia", all((BASE / "output" / i).exists() for i in imgs), f"{len(imgs)} gambar")
ext = re.findall(r"(?i)cilegon|\bOKI\b|ogan|jawa tengah|banten|bangka|kalimantan utara|gorontalo|padat penduduk", rep)
check("User (tanpa substansi tambahan)", "Laporan tanpa fakta wilayah dari luar dataset", not ext, ", ".join(set(ext)))
for o in ["1.", "2.", "3.", "4.", "5."]:
    pass
cov = {"Tujuan 1": "3.1.1", "Tujuan 2": "3.1.2", "Tujuan 3": "3.1.3", "Tujuan 4": "3.1.4", "Tujuan 5": "3.1.5"}
check("Booklet", "Tujuan 1–5 masing-masing punya subbab hasil", all(v in rep for v in cov.values()))

# ---------------- booklet sub-requirements, checked against the result tables ----------------
T = lambda n: pd.read_csv(TAB / f"{n}.csv")
has = lambda n: (TAB / f"{n}.csv").exists()
isl = T("o1_island_summary")
check("Booklet T1", "Banding antarstasiun & antarpulau", len(T("o1_station_profile")) == 26 and len(isl) == 5)
ann = T("o1_annual_compliance_iku")
check("Booklet T1", "Evaluasi vs baku mutu PP 22/2021 (tahunan per tahun kalender, 24 jam, 8 jam, 1 jam)",
      has("o1_shortterm_standards") and {"lolos_bm_pm25", "lolos_bm_pm10", "lolos_bm_no2", "lolos_bm_o3", "lolos_bm_so2"} <= set(ann.columns))
check("Booklet T1", "Kategori ISPU (Permen LHK 14/2020)", "ispu_kategori" in D.columns and D.ispu_kategori.notna().sum() > 20000)
check("Booklet T1", "Penilaian IKU (Permen LHK 27/2021)", "IKU" in ann.columns and ann.IKU.notna().all(),
      "rumus Ieu/IKU KLHK — cocokkan dengan lampiran Permen LHK 27/2021")
check("Booklet T1", "Pedoman kesehatan (WHO 2021)", "pct_days_exceed_who24h_pm25" in T("o1_station_profile").columns)
check("Booklet T1", "Kecenderungan perbaikan/pemburukan", "trend_overall" in T("o1_trend_pm25").columns)
check("Booklet T2", "Pola per jam", has("o2_diurnal_by_category") and has("o2_peak_hour_station"))
check("Booklet T2", "Hari kerja vs akhir pekan", has("o2_weekday_weekend"))
check("Booklet T2", "Musim", has("o2_season_station"))
check("Booklet T2", "Episode kabut asap karhutla/gambut", len(T("o2_haze_episodes")) > 0)
check("Booklet T2", "Beda karakteristik perkotaan, industri, latar bersih", has("o2_site_category_profile")
      and {"Perkotaan", "Industri", "Latar Bersih"} <= set(T("o2_site_category_profile").site_category))
mc = T("o3_all_pollutants_meteo_correlation")
check("Booklet T3", "Suhu, kelembapan, kecepatan angin — untuk semua polutan",
      set(mc.pollutant) == set(POLL) and set(mc.factor) == {"temperature_c", "humidity_pct", "wind_speed_ms"})
check("Booklet T3", "Arah angin", has("o3_wind_sector_pm25"))
sf = T("o3_all_pollutants_site_factors")
check("Booklet T3", "Lalu lintas, jarak ke jalan, tipe lokasi", {"traffic_intensity_per_h", "distance_to_road_m"} <= set(sf.factor)
      and sf.factor.str.startswith("site_category").any())
check("Booklet T3", "Faktor paling berpengaruh ditentukan", has("o3_rf_permutation_importance_groups"))
dl = T("o4_distributed_lag_model")
check("Booklet T4", "PM2.5 vs ISPA, asma, PPOK, kardiovaskular, kematian", dl.outcome.nunique() == 7)
check("Booklet T4", "Efek jeda setelah paparan", set(dl.lag.astype(str)) >= {str(i) for i in range(8)})
check("Booklet T4", "Banding kerentanan balita vs lansia", T("o4_vulnerability_under5_vs_over60").group.str.contains("balita/lansia").any())
check("Booklet T5", "Tinjau sebaran stasiun & rekomendasi wilayah prioritas",
      has("o5_monitoring_gap_corridors") and "priority_score" in T("o5_network_station_assessment").columns)
log = pd.read_csv(CLEAN / "cleaning_log.csv")
check("Booklet (33 file)", "metadata_sensors.csv dipakai (validasi kategori QC & satuan)",
      log.rule.str.startswith("qc_flag di luar kategori metadata_sensors").any())
dist = BASE / "dashboard-app" / "dist"
built = (dist / "index.html").exists() and (dist / "logo_gelar_rasa.png").exists() and (dist / "data" / "dashboard.json").exists()
check("Booklet", "Tujuan 6: dashboard interaktif dibangun (dengan logo Gelar Rasa)", built,
      "web app dashboard-app/dist siap; BELUM dipublikasikan — link & subbab 3.2–3.3 laporan masih kosong")

out = pd.DataFrame(rows)
out.to_csv(OUTD / "audit_checks.csv", index=False)
pd.set_option("display.width", 250)
pd.set_option("display.max_colwidth", 95)
print(out.to_string(index=False))
