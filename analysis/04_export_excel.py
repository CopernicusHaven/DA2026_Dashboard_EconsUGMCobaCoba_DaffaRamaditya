"""
Build dashboard-ready Excel workbooks from the cleaned data and analysis tables.
  output/GelarRasa2026_Data_Bersih.xlsx      -> clean tables (daily/monthly/health/dimension/quality)
  output/GelarRasa2026_Hasil_Analisis.xlsx   -> all analysis result tables (objectives 1-5)
Hourly data (659,664 rows) stays in output/clean/aqms_hourly_clean.csv / .parquet.
Run: python3 analysis/04_export_excel.py
"""
from pathlib import Path
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from common import BASE, CLEAN, TAB

OUTDIR = BASE / "output"


def style(ws):
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", start_color="1C5CAB")
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for col in ws.columns:
        w = max(len(str(c.value)) if c.value is not None else 0 for c in list(col)[:300])
        ws.column_dimensions[get_column_letter(col[0].column)].width = min(max(w + 2, 10), 45)


def write(path, sheets, readme):
    # build in the system temp dir, then copy: random-access seeks while zipping a large workbook
    # directly into this folder timed out (Errno 60) on this machine
    import shutil, tempfile
    tmp = Path(tempfile.gettempdir()) / path.name
    with pd.ExcelWriter(tmp, engine="openpyxl") as xw:
        pd.DataFrame(readme, columns=["sheet", "isi", "baris", "catatan"]).to_excel(xw, sheet_name="README", index=False)
        for name, df in sheets.items():
            df.to_excel(xw, sheet_name=name[:31], index=False)
        for ws in xw.book.worksheets:
            style(ws)
        xw.book["README"].column_dimensions["B"].width = 70
        xw.book["README"].column_dimensions["D"].width = 90
    shutil.copyfile(tmp, path)
    tmp.unlink()


# ---------------- clean data workbook ----------------
daily = pd.read_csv(CLEAN / "aqms_daily.csv", parse_dates=["date"])
monthly = pd.read_csv(CLEAN / "aqms_monthly.csv", parse_dates=["month_start"])
merged = pd.read_csv(CLEAN / "health_aq_daily_merged.csv", parse_dates=["date"])
dim = pd.read_csv(CLEAN / "dim_station.csv")
qual = pd.read_csv(CLEAN / "data_quality_station.csv")
log = pd.read_csv(CLEAN / "cleaning_log.csv")
for df, c in [(daily, "date"), (merged, "date"), (monthly, "month_start")]:
    df[c] = df[c].dt.date

clean_sheets = {"unit_conversion_ppm": pd.read_csv(CLEAN / "unit_conversion_ppm.csv"), "dim_station": dim, "data_quality_station": qual, "cleaning_log": log,
                "aqms_daily": daily, "aqms_monthly": monthly, "health_aq_daily": merged}
clean_readme = [
    ("unit_conversion_ppm", "Dokumentasi konversi ppm -> ug/m3 (BJB-01, MDN-01, PSW-01): basis, massa molar, faktor, rumus",
     6, "Sesuai QnA panitia: metode konversi ditentukan peserta, berdasar ilmiah, konsisten, dijelaskan di laporan."),
    ("dim_station", "Tabel master stasiun: sites + sensors + hospitals + metadata_dates, ditambah pulau & kategori tipe lokasi",
     len(dim), "Kunci: station (mis. JKT-01) <-> location_id <-> sensor_id <-> hospital_id (RS-XXX-NN)."),
    ("data_quality_station", "Kelengkapan data per stasiun setelah pembersihan", len(qual),
     "JMB-02 dikeluarkan (sensor defective, 0,5% jam valid). MER-01, MDN-01, BJB-01 kelengkapan PM2.5 <75%."),
    ("cleaning_log", "Log setiap aturan pembersihan: stasiun, aturan, kolom, jumlah nilai terdampak", len(log),
     "Sumber untuk menjelaskan proses data cleaning di dashboard/presentasi."),
    ("aqms_daily", "Rata-rata harian per stasiun (hari dengan >=18 jam valid), ISPU harian, flag baku mutu & WHO, episode kabut asap",
     len(daily), "Satuan ug/m3. ISPU per Permen LHK 14/2020; baku mutu 24 jam per PP 22/2021; haze_episode_day = episode kabut asap."),
    ("aqms_monthly", "Rata-rata bulanan per stasiun + jumlah hari melebihi baku mutu & hari kabut asap", len(monthly),
     "pm25_complete = True bila >=75% hari dalam bulan valid."),
    ("health_aq_daily", "Kasus kesehatan harian per RS digabung dengan PM2.5 stasiun pasangan (lag 0-7, rata-rata 0-2 & 0-7)",
     len(merged), "exposure_station = stasiun pasangan RS sesuai booklet. RS-XXX-27 (pasangan JMB-02 yang defective) tidak punya data paparan; tidak diganti proksi."),
    ("(file terpisah)", "output/clean/aqms_hourly_clean.csv & .parquet - data per jam bersih; hanya jam yang ada di file asli",
     655808, "Terlalu besar untuk sheet Excel yang nyaman; impor langsung ke Power BI/Tableau/Looker."),
]
write(OUTDIR / "GelarRasa2026_Data_Bersih.xlsx", clean_sheets, clean_readme)

# ---------------- analysis workbook ----------------
DESC = {
    "o1_station_profile": "T1 - Profil polutan per stasiun, % hari melebihi baku mutu/WHO, distribusi ISPU",
    "o1_island_summary": "T1 - Ringkasan per pulau",
    "o1_annual_compliance_iku": "T1 - Rata-rata tahunan per tahun kalender vs baku mutu tahunan PP 22/2021 + IKU (Permen LHK 27/2021)",
    "o1_annual_compliance_summary": "T1 - Jumlah stasiun lolos baku mutu tahunan per tahun (stasiun kelengkapan >=75%)",
    "o1_shortterm_standards": "T1 - Baku mutu 1 jam, 8 jam & 24 jam: jumlah jam/hari terlampaui & nilai maksimum",
    "o1_trend_pm25": "T1 - Tren PM2.5: rata-rata 1 Jan-14 Okt per tahun, musim kabut, tren latar (Mann-Kendall/Theil-Sen)",
    "o2_diurnal_by_category": "T2 - Pola per jam menurut tipe lokasi (hari non-kabut asap)",
    "o2_peak_hour_station": "T2 - Jam puncak & jam terendah PM2.5 per stasiun",
    "o2_weekday_weekend": "T2 - Hari kerja vs akhir pekan per stasiun & polutan (uji Mann-Whitney)",
    "o2_weekday_weekend_by_category": "T2 - Selisih akhir pekan per tipe lokasi",
    "o2_season_station": "T2 - Musim kemarau vs hujan, bulan puncak",
    "o2_month_of_year_station": "T2 - Matriks stasiun x bulan (heatmap)",
    "o2_haze_episodes": "T2 - Daftar episode kabut asap (>=3 hari PM2.5 >55,4 & >2x median musim hujan)",
    "o2_haze_by_station_year": "T2 - Jumlah episode & hari kabut asap per stasiun per tahun",
    "o2_smoke_fingerprint": "T2 - Sidik jari asap: rasio PM2.5/PM10 & CO saat kabut vs normal",
    "o2_site_category_profile": "T2 - Perbandingan karakteristik perkotaan, tepi jalan, industri, gambut & latar bersih",
    "o2_critical_area_ranking": "T2 - Skor wilayah kritis (level, % hari lewat baku mutu, P98, hari ISPU tidak sehat+)",
    "o3_meteo_correlation_station": "T3 - Korelasi Spearman per jam PM2.5 vs suhu/kelembapan/angin per stasiun",
    "o3_meteo_correlation_by_category": "T3 - Korelasi meteorologi rata-rata per tipe lokasi",
    "o3_meteo_fixed_effects": "T3 - Model efek tetap stasiun: % perubahan PM2.5 per 1 SD meteorologi",
    "o3_wind_sector_pm25": "T3 - PM2.5 per sektor arah angin (8 arah)",
    "o3_site_factor_correlation": "T3 - Korelasi antarstasiun: lalu lintas & jarak jalan vs PM2.5/NO2/CO (musim hujan)",
    "o3_site_category_means_wetseason": "T3 - Rata-rata polutan musim hujan per tipe lokasi",
    "o3_station_wetseason_vs_site": "T3 - Data antarstasiun untuk scatter lalu lintas",
    "o3_all_pollutants_meteo_correlation": "T3 - Korelasi Spearman per jam 6 polutan vs suhu/kelembapan/kecepatan angin (rata-rata stasiun)",
    "o3_all_pollutants_site_factors": "T3 - 6 polutan vs lalu lintas, jarak jalan (Spearman) & tipe lokasi (Kruskal-Wallis)",
    "o3_rf_permutation_importance_groups": "T3 - Kepentingan faktor (Random Forest, permutation importance, uji 2026)",
    "o3_rf_permutation_importance_features": "T3 - Kepentingan per fitur",
    "o4_admissions_per100beds_by_ispu": "T4 - Rata-rata kasus per 100 tempat tidur menurut kategori ISPU hari itu",
    "o4_admissions_relative_to_sedang": "T4 - Kasus relatif terhadap hari 'Sedang'",
    "o4_lag_rr_all_outcomes": "T4 - RR per +10 ug/m3 per jeda (model jeda tunggal, quasi-Poisson)",
    "o4_peak_lag_by_outcome": "T4 - Jeda dengan efek terbesar per outcome",
    "o4_distributed_lag_model": "T4 - Distributed lag model (lag 0-7 bersamaan) + kumulatif",
    "o4_dlm_peak_and_cumulative": "T4 - Ringkasan puncak & kumulatif DLM",
    "o4_sensitivity": "T4 - Analisis sensitivitas (df waktu, rentang paparan)",
    "o4_vulnerability_under5_vs_over60": "T4 - Kerentanan balita vs lansia, per pulau",
    "o4_exposure_response_ispu_band": "T4 - Risiko relatif per kategori ISPU PM2.5 (vs Baik)",
    "o4_haze_vs_normal_days": "T4 - Kenaikan kasus saat hari kabut asap vs hari normal",
    "o4_attributable_cases_above_who": "T4 - Kasus teratribusi PM2.5 di atas kategori Baik (~WHO 24 jam), per pulau",
    "o4_hospital_burden": "T4 - Beban kasus per rumah sakit",
    "o5_network_station_assessment": "T5 - Penilaian tiap stasiun: keandalan, jarak tetangga, isu data, skor prioritas",
    "o5_island_coverage": "T5 - Cakupan jaringan per pulau & celah terlebar antarstasiun",
    "o5_monitoring_gap_corridors": "T5 - Celah pemantauan: sisi pohon rentang minimum antarstasiun per pulau (dari koordinat dataset)",
}
an_sheets, an_readme = {}, []
for name, desc in DESC.items():
    df = pd.read_csv(TAB / f"{name}.csv")
    short = name.replace("_by_", "_").replace("permutation_importance", "rf_imp").replace("vulnerability", "vuln")[:31]
    an_sheets[short] = df
    an_readme.append((short, desc, len(df), ""))
write(OUTDIR / "GelarRasa2026_Hasil_Analisis.xlsx", an_sheets, an_readme)
print("written:", [p.name for p in OUTDIR.glob("GelarRasa2026_*.xlsx")])
