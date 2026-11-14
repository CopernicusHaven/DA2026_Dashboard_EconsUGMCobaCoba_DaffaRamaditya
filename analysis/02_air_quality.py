"""
Objectives 1-3: air quality in space & time, critical times/areas (incl. haze), drivers of pollutant variation.
Run: python3 analysis/02_air_quality.py
"""
import warnings
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.formula.api as smf
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
import matplotlib.pyplot as plt
from common import *  # noqa: F401,F403

warnings.filterwarnings("ignore")
dim = load_dim()
H = load_hourly()
D = load_daily()
q = pd.read_csv(CLEAN / "data_quality_station.csv").set_index("station")
meta = dim.set_index("station")
ST = sorted(H.station.unique())

# ======================================================================================
# OBJECTIVE 1 - condition in space & time, vs standards, trend
# ======================================================================================
# 1a. station profile (means from valid hours -> keeps MER-01 which has few complete days)
prof = H.groupby("station")[[f"{p}_ug_m3" for p in POLL]].mean()
prof.columns = [f"{p}_mean" for p in POLL]
prof["pm25_p98_daily"] = D.groupby("station")["pm25"].quantile(0.98)
prof["pm25_max_daily"] = D.groupby("station")["pm25"].max()
prof["valid_days"] = D.groupby("station")["pm25"].count()
for p in ["pm25", "pm10", "so2", "no2"]:
    prof[f"pct_days_exceed_bm24h_{p}"] = D.groupby("station")[f"exc_{p}_bm"].mean() * 100
prof["pct_days_exceed_who24h_pm25"] = D.groupby("station")["exc_pm25_who"].mean() * 100
prof["pm25_x_bm_annual"] = prof.pm25_mean / BM_YEAR["pm25"]
prof["pm25_x_who_annual"] = prof.pm25_mean / WHO_YEAR["pm25"]
prof["meets_bm_annual_pm25"] = prof.pm25_mean <= BM_YEAR["pm25"]
prof["meets_bm_annual_pm10"] = prof.pm10_mean <= BM_YEAR["pm10"]
prof["meets_bm_annual_no2"] = prof.no2_mean <= BM_YEAR["no2"]
prof["meets_bm_annual_so2"] = prof.so2_mean <= BM_YEAR["so2"]
cat_pct = pd.crosstab(D.station, D.ispu_kategori, normalize="index") * 100
cat_pct.columns = ["ispu_pct_" + c.split(" ", 1)[1].lower().replace(" ", "_") for c in cat_pct.columns]
prof = prof.join(cat_pct).fillna({c: 0 for c in cat_pct.columns})
prof["ispu_dominant_pollutant"] = D.groupby("station")["ispu_dominant"].agg(lambda s: s.mode().iat[0] if s.notna().any() else None)
prof = prof.join(meta[["island", "provinsi", "kota_kabupaten", "site_category", "site_type", "baseline_pm25",
                       "traffic_intensity_per_h", "distance_to_road_m", "latitude_dd", "longitude_dd"]])
prof["completeness_pm25_pct"] = q["completeness_pm25_pct"]
prof["data_note"] = np.where(prof.completeness_pm25_pct < 75, "kelengkapan <75%", "")
prof["rank_pm25"] = prof.pm25_mean.rank(ascending=False).astype(int)
prof = prof.sort_values("pm25_mean", ascending=False)
save(prof.round(2), "o1_station_profile", index=True)

# 1b. yearly means (Jan 1 - Oct 14 window each year so 2026 is comparable)
Hw = H[(H.datetime.dt.month < 10) | ((H.datetime.dt.month == 10) & (H.datetime.dt.day <= 14))]
yr = Hw.groupby(["station", "year"])["pm25_ug_m3"].mean().unstack()
yr.columns = [f"pm25_{c}_jan_14okt" for c in yr.columns]
yr["chg_2024_2026_pct"] = (yr.iloc[:, 2] / yr.iloc[:, 0] - 1) * 100

# 1c. trend, split in two components because haze and background behave differently:
#   (i)  background trend  = monthly means of wet-season months (Nov-Apr) -> Mann-Kendall + Theil-Sen
#   (ii) haze-season trend = Aug-Oct mean per year (2026: Aug 1 - Oct 14)
#   overall label from the like-for-like Jan 1 - Oct 14 window: >+10% Memburuk, <-10% Membaik, else Stabil
Hm = H.assign(ms=H.datetime.dt.to_period("M").dt.to_timestamp())
mon = Hm.groupby(["station", "ms"]).pm25_ug_m3.agg(["mean", "count"]).reset_index()
mon = mon[mon["count"] >= 0.5 * 24 * 28]  # >= ~50% valid hours in the month
rows = []
for st in ST:
    g = mon[(mon.station == st) & (mon.ms.dt.month.isin([11, 12, 1, 2, 3, 4]))].sort_values("ms")
    r = {"station": st, "n_wet_months": len(g)}
    if len(g) >= 8:
        t = (g.ms - g.ms.min()).dt.days / 365.25
        tau, p = stats.kendalltau(t, g["mean"])
        slope, icpt, lo, hi = stats.theilslopes(g["mean"], t)
        r.update({"bg_sen_slope_ug_per_year": slope, "bg_slope_ci_low": lo, "bg_slope_ci_high": hi,
                  "bg_slope_pct_per_year": slope / g["mean"].mean() * 100, "bg_kendall_tau": tau, "bg_p_value": p,
                  "bg_trend": "Naik" if (p < 0.05 and slope > 0) else ("Turun" if (p < 0.05 and slope < 0) else "Stabil")})
    rows.append(r)
trend = pd.DataFrame(rows).set_index("station")
hz = H[H.datetime.dt.month.between(8, 10) & ((H.datetime.dt.month < 10) | (H.datetime.dt.day <= 14))]
hzy = hz.groupby(["station", "year"]).pm25_ug_m3.mean().unstack()
hzy.columns = [f"pm25_agu_okt_{c}" for c in hzy.columns]
hzy["haze_season_chg_2024_2026_pct"] = (hzy.iloc[:, 2] / hzy.iloc[:, 0] - 1) * 100
trend = trend.join(yr).join(hzy).join(meta[["island", "site_category"]])
trend["trend_overall"] = np.select([trend.chg_2024_2026_pct > 10, trend.chg_2024_2026_pct < -10],
                                   ["Memburuk", "Membaik"], "Stabil")
save(trend.round(3).sort_values("chg_2024_2026_pct", ascending=False), "o1_trend_pm25", index=True)

# 1d. island summary
isl = prof.groupby("island").agg(n_stasiun=("pm25_mean", "size"), pm25_mean=("pm25_mean", "mean"),
                                 pm25_max_station=("pm25_mean", "max"), pm10_mean=("pm10_mean", "mean"),
                                 no2_mean=("no2_mean", "mean"), so2_mean=("so2_mean", "mean"),
                                 co_mean=("co_mean", "mean"),
                                 pct_days_exceed_bm24h_pm25=("pct_days_exceed_bm24h_pm25", "mean"),
                                 n_stasiun_lolos_bm_tahunan_pm25=("meets_bm_annual_pm25", "sum"))
isl_ispu = pd.crosstab(D.island, D.ispu_kategori, normalize="index") * 100
isl = isl.join(isl_ispu.add_prefix("pct_hari_")).reindex(ISLANDS)
haze_by_isl = D[D.haze_episode_day].groupby("island").size()
isl["hari_episode_kabut_asap_total"] = haze_by_isl.reindex(ISLANDS).fillna(0).astype(int)
save(isl.round(2), "o1_island_summary", index=True)

# ---- figures objective 1 ----
fig, ax = plt.subplots(figsize=(10, 7))
pp = prof.sort_values("pm25_mean")
ax.barh(pp.index, pp.pm25_mean, color=[ISLAND_COLOR[i] for i in pp.island], height=0.7)
ax.axvline(BM_YEAR["pm25"], color=INK2, lw=1, ls="--")
ax.axvline(WHO_YEAR["pm25"], color=MUTED, lw=1, ls=":")
ax.text(BM_YEAR["pm25"] + 0.5, -0.9, "Baku mutu tahunan PP 22/2021 (15)", color=INK2, fontsize=8)
ax.text(WHO_YEAR["pm25"] + 0.5, len(pp) - 0.4, "WHO 2021 (5)", color=MUTED, fontsize=8)
for i, (s, v) in enumerate(zip(pp.index, pp.pm25_mean)):
    flag = " *" if pp.loc[s, "completeness_pm25_pct"] < 75 else ""
    ax.text(v + 0.6, i, f"{v:.0f}{flag}", va="center", fontsize=8, color=INK2)
ax.set_xlabel("Rata-rata PM2.5 (µg/m³), Jan 2024 – 14 Okt 2026")
ax.set_title("Hanya 3 dari 26 stasiun memenuhi baku mutu tahunan PM2.5")
ax.grid(axis="y", visible=False)
ax.legend(handles=patches(ISLAND_COLOR), loc="lower right", title="Pulau", title_fontsize=9)
savefig(fig, "o1_pm25_station_ranking", "* kelengkapan data PM2.5 <75% (MER-01, MDN-01, BJB-01). JMB-02 dikeluarkan (sensor defective).")

fig, ax = plt.subplots(figsize=(11, 4.6))
mi = D.groupby(["island", pd.Grouper(key="date", freq="MS")])["pm25"].mean().unstack(0)
for isl_name in ISLANDS:
    ax.plot(mi.index, mi[isl_name], color=ISLAND_COLOR[isl_name], label=isl_name)
ax.axhline(BM_24H["pm25"], color=INK2, lw=1, ls="--")
ax.text(mi.index[0], BM_24H["pm25"] + 2, "Baku mutu 24 jam (55)", fontsize=8, color=INK2)
ax.set_ylabel("PM2.5 bulanan (µg/m³)")
ax.set_title("Lonjakan PM2.5 berulang tiap Agustus–Oktober di Kalimantan & Sumatera")
ax.legend(ncol=5, loc="upper left")
savefig(fig, "o1_pm25_monthly_island", "Rata-rata bulanan dari rata-rata harian stasiun (hari dengan ≥18 jam valid). Oktober 2026 hanya s.d. tanggal 14.")

fig, ax = plt.subplots(figsize=(10, 7.5))
cats_order = ["ispu_pct_baik", "ispu_pct_sedang", "ispu_pct_tidak_sehat", "ispu_pct_sangat_tidak_sehat", "ispu_pct_berbahaya"]
lab = ["Baik", "Sedang", "Tidak Sehat", "Sangat Tidak Sehat", "Berbahaya"]
pq = prof[prof.valid_days > 30].sort_values(["ispu_pct_baik", "ispu_pct_sedang"])
left = np.zeros(len(pq))
for c, l, col in zip(cats_order, lab, ORDINAL5):
    v = pq[c].values if c in pq else np.zeros(len(pq))
    ax.barh(pq.index, v, left=left, color=col, label=l, height=0.72, edgecolor=SURFACE, linewidth=1)
    left += v
ax.set_xlim(0, 100)
ax.set_xlabel("% hari (ISPU harian, Permen LHK 14/2020)")
ax.set_title("Distribusi kategori ISPU harian per stasiun")
ax.legend(ncol=5, loc="upper center", bbox_to_anchor=(0.45, -0.07))
ax.grid(axis="y", visible=False)
savefig(fig, "o1_ispu_distribution", "MER-01 tidak ditampilkan (hanya 2 hari memenuhi syarat ≥18 jam valid).")

fig, axes = plt.subplots(1, 2, figsize=(12, 7), sharey=True)
tt = trend.dropna(subset=["pm25_2024_jan_14okt"]).sort_values("pm25_2026_jan_14okt")
y = np.arange(len(tt))
YC = {2024: "#9ec5f4", 2025: "#3987e5", 2026: "#0d366b"}
for ax, pref, ttl in [(axes[0], "pm25_{}_jan_14okt", "Sepanjang tahun (1 Jan – 14 Okt)"),
                      (axes[1], "pm25_agu_okt_{}", "Musim kabut asap (Agu – 14 Okt)")]:
    three = tt[[pref.format(k) for k in (2024, 2025, 2026)]]
    ax.hlines(y, three.min(axis=1), three.max(axis=1), color=AXIS, lw=2)
    for yr_ in [2024, 2025, 2026]:
        ax.scatter(tt[pref.format(yr_)], y, color=YC[yr_], s=42, zorder=3, edgecolor=SURFACE, linewidth=1.2, label=str(yr_))
    ax.set_title(ttl, fontsize=10)
    ax.set_xlabel("PM2.5 rata-rata (µg/m³)")
    ax.grid(axis="y", visible=False)
axes[0].set_yticks(y, [f"{s}  {'▲' if t == 'Memburuk' else ('▼' if t == 'Membaik' else '•')}" for s, t in zip(tt.index, tt.trend_overall)])
axes[1].legend(loc="lower right", title="Tahun")
fig.suptitle("PM2.5 memburuk di 12 stasiun Sumatera & Kalimantan (didorong kabut asap); Jawa, Sulawesi & Papua stabil",
             x=0.01, y=1.03, ha="left", fontweight="bold", color=INK)
savefig(fig, "o1_trend_pm25", "▲ memburuk (>+10% 2024→2026, periode 1 Jan–14 Okt), • stabil (±10%). Rata-rata dari jam valid.")

# ======================================================================================
# OBJECTIVE 2 - critical times & areas
# ======================================================================================
haze_days = D.loc[D.haze_episode_day, ["station", "date"]].assign(h=True)
H2 = H.merge(haze_days, on=["station", "date"], how="left")
H2["haze"] = H2["h"].fillna(False).astype(bool)
Hn = H2[~H2.haze]

# 2a. diurnal profile by site category (non-haze days, to isolate local routine)
diur = Hn.groupby(["site_category", "hour"])[["pm25_ug_m3", "no2_ug_m3", "co_ug_m3", "o3_ug_m3"]].mean().reset_index()
save(diur.round(2), "o2_diurnal_by_category")
diur_st = Hn.groupby(["station", "hour"])["pm25_ug_m3"].mean().unstack()
peak = pd.DataFrame({"peak_hour_pm25": diur_st.idxmax(axis=1), "peak_value": diur_st.max(axis=1),
                     "low_hour_pm25": diur_st.idxmin(axis=1), "low_value": diur_st.min(axis=1)})
peak["peak_to_low_ratio"] = peak.peak_value / peak.low_value
peak = peak.join(meta[["site_category", "island"]])
save(peak.round(2), "o2_peak_hour_station", index=True)

# 2b. weekday vs weekend (non-haze days; Mann-Whitney on daily means)
Dn = D[~D.haze_episode_day]
wk = []
for st, g in Dn.groupby("station"):
    for p in ["pm25", "no2", "co"]:
        a, b = g.loc[~g.is_weekend, p].dropna(), g.loc[g.is_weekend, p].dropna()
        if len(a) > 20 and len(b) > 10:
            u, pv = stats.mannwhitneyu(a, b)
            wk.append({"station": st, "pollutant": p, "weekday_mean": a.mean(), "weekend_mean": b.mean(),
                       "weekend_vs_weekday_pct": (b.mean() / a.mean() - 1) * 100, "p_value": pv})
wk = pd.DataFrame(wk).merge(meta[["site_category", "island", "traffic_intensity_per_h"]], left_on="station", right_index=True)
save(wk.round(4), "o2_weekday_weekend")
wk_cat = wk.groupby(["site_category", "pollutant"])["weekend_vs_weekday_pct"].mean().unstack()
save(wk_cat.round(2), "o2_weekday_weekend_by_category", index=True)

# 2c. season
sea = D.groupby(["station", "season"])["pm25"].mean().unstack()
sea["dry_vs_wet_pct"] = (sea["Kemarau (Mei-Okt)"] / sea["Hujan (Nov-Apr)"] - 1) * 100
moy = D.groupby(["station", "month"])["pm25"].mean().unstack()
sea["peak_month"] = moy.idxmax(axis=1)
sea["peak_month_pm25"] = moy.max(axis=1)
sea = sea.join(meta[["site_category", "island"]])
save(sea.round(2), "o2_season_station", index=True)
save(moy.round(1), "o2_month_of_year_station", index=True)

# 2d. haze episodes
ep = D[D.haze_episode_day].groupby("haze_episode_id").agg(
    station=("station", "first"), start=("date", "min"), end=("date", "max"), days=("date", "size"),
    pm25_mean=("pm25", "mean"), pm25_peak_daily=("pm25", "max"), pm25_peak_hour=("pm25_1h_max", "max"),
    pm10_mean=("pm10", "mean"), co_mean=("co", "mean"), ispu_max=("ispu", "max"),
    days_sangat_tidak_sehat_plus=("ispu", lambda s: int((s > 200).sum())))
ep["pm25_pm10_ratio"] = ep.pm25_mean / ep.pm10_mean
ep = ep.join(meta[["island", "provinsi", "site_category"]], on="station").sort_values(["station", "start"])
ep["year"] = ep.start.dt.year
save(ep.round(2), "o2_haze_episodes", index=True)
epy = ep.groupby(["station", "year"]).agg(episodes=("days", "size"), haze_days=("days", "sum"),
                                          peak_daily=("pm25_peak_daily", "max")).unstack()
save(epy, "o2_haze_by_station_year", index=True)
# smoke fingerprint: PM2.5/PM10 ratio & CO, haze vs non-haze
fp = D.assign(ratio=D.pm25 / D.pm10).groupby(["station", "haze_episode_day"])[["pm25", "ratio", "co"]].mean().unstack()
fp.columns = [f"{a}_{'haze' if b else 'normal'}" for a, b in fp.columns]
fp = fp.dropna(subset=["pm25_haze"])
fp["co_increase_pct"] = (fp.co_haze / fp.co_normal - 1) * 100
fp["pm25_increase_x"] = fp.pm25_haze / fp.pm25_normal
save(fp.round(3), "o2_smoke_fingerprint", index=True)

# 2e. hotspot ranking (critical areas) - composite of level, exceedance, peak
crit = prof[["island", "provinsi", "site_category", "pm25_mean", "pct_days_exceed_bm24h_pm25", "pm25_p98_daily"]].copy()
crit["haze_days"] = D[D.haze_episode_day].groupby("station").size().reindex(crit.index).fillna(0)
crit["days_ispu_tidak_sehat_plus"] = D[D.ispu > 100].groupby("station").size().reindex(crit.index).fillna(0)
for c in ["pm25_mean", "pct_days_exceed_bm24h_pm25", "pm25_p98_daily", "days_ispu_tidak_sehat_plus"]:
    crit[c + "_rank"] = crit[c].rank(pct=True)
crit["critical_score"] = crit.filter(like="_rank").mean(axis=1) * 100
crit = crit.sort_values("critical_score", ascending=False)
save(crit.round(2), "o2_critical_area_ranking", index=True)

# ---- figures objective 2 ----
fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
for cat in CATS:
    g = diur[diur.site_category == cat]
    axes[0].plot(g.hour, g.pm25_ug_m3, color=CAT_COLOR[cat], label=cat)
    axes[1].plot(g.hour, g.no2_ug_m3, color=CAT_COLOR[cat], label=cat)
axes[0].set_title("PM2.5 per jam (hari non-kabut asap)")
axes[1].set_title("NO2 per jam (penanda lalu lintas)")
for a in axes:
    a.set_xticks(range(0, 24, 3))
    a.set_xlabel("Jam (WIB)")
axes[0].set_ylabel("µg/m³")
axes[1].legend(loc="upper left", bbox_to_anchor=(1, 1))
fig.suptitle("Pola harian: dua puncak, pagi 07–08 dan sore 18–19, di semua tipe lokasi",
             x=0.01, y=1.03, ha="left", fontweight="bold", color=INK)
savefig(fig, "o2_diurnal_profile")

fig, ax = plt.subplots(figsize=(12, 7.5))
hm = moy.loc[prof.index[prof.valid_days > 30]]
im = ax.imshow(hm.values, aspect="auto", cmap=matplotlib.colors.LinearSegmentedColormap.from_list("seq", SEQ))
ax.set_yticks(range(len(hm)), hm.index)
ax.set_xticks(range(12), ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"])
for i in range(hm.shape[0]):
    for j in range(hm.shape[1]):
        v = hm.values[i, j]
        if np.isfinite(v):
            dark = (v - np.nanmin(hm.values)) / (np.nanmax(hm.values) - np.nanmin(hm.values)) > 0.45
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=7, color="#ffffff" if dark else INK)
ax.grid(False)
cb = fig.colorbar(im, ax=ax, shrink=0.6)
cb.set_label("PM2.5 rata-rata (µg/m³)", color=INK2)
ax.set_title("Kalender bulan kritis: rata-rata PM2.5 per stasiun per bulan (2024–2026)")
savefig(fig, "o2_heatmap_station_month")

fig, ax = plt.subplots(figsize=(12, 6))
ep_st = ep.station.unique()
order = [s for s in prof.index if s in ep_st]
for i, s in enumerate(order):
    for _, r in ep[ep.station == s].iterrows():
        ax.barh(i, (r.end - r.start).days + 1, left=r.start, height=0.6,
                color=ISLAND_COLOR[r.island], edgecolor=SURFACE, linewidth=0.5)
ax.set_yticks(range(len(order)), order)
ax.set_title("Episode kabut asap (≥3 hari PM2.5 >55,4 & >2× median musim hujan)")
ax.legend(handles=patches({k: ISLAND_COLOR[k] for k in ["Sumatera", "Kalimantan"]}), loc="upper left")
ax.grid(axis="y", visible=False)
savefig(fig, "o2_haze_timeline")

fig, ax = plt.subplots(figsize=(10, 4.6))
wk_plot = wk[wk.pollutant == "no2"].set_index("station").sort_values("weekend_vs_weekday_pct")
ax.bar(wk_plot.index, wk_plot.weekend_vs_weekday_pct, color=[CAT_COLOR[c] for c in wk_plot.site_category], width=0.7)
ax.axhline(0, color=INK2, lw=1)
ax.set_ylabel("Akhir pekan vs hari kerja (%)")
ax.set_title("Tidak ada efek akhir pekan: selisih NO2 akhir pekan vs hari kerja < ±1% di semua stasiun")
ax.set_ylim(-5, 5)
ax.tick_params(axis="x", rotation=60)
ax.legend(handles=patches(CAT_COLOR), fontsize=8, loc="lower right", ncol=2)
ax.grid(axis="x", visible=False)
savefig(fig, "o2_weekend_effect_no2")

# ======================================================================================
# OBJECTIVE 3 - drivers
# ======================================================================================
# 3a. within-station Spearman correlation, hourly, non-haze & all
rc = []
for st, g in H2.groupby("station"):
    for scope, gg in [("semua", g), ("non_kabut", g[~g.haze])]:
        for f in ["temperature_c", "humidity_pct", "wind_speed_ms"]:
            x = gg[["pm25_ug_m3", f]].dropna()
            if len(x) > 500:
                r, p = stats.spearmanr(x.pm25_ug_m3, x[f])
                rc.append({"station": st, "scope": scope, "factor": f, "spearman_r": r, "p_value": p, "n": len(x)})
rc = pd.DataFrame(rc).merge(meta[["site_category", "island"]], left_on="station", right_index=True)
save(rc.round(4), "o3_meteo_correlation_station")
rc_cat = rc[rc.scope == "semua"].groupby(["site_category", "factor"]).spearman_r.mean().unstack()
save(rc_cat.round(3), "o3_meteo_correlation_by_category", index=True)

# 3b. within-station multivariate (station FE): log PM2.5 ~ meteo + time controls, daily
Dm = D.dropna(subset=["pm25", "temperature_c", "humidity_pct", "wind_speed_ms"]).copy()
Dm["log_pm25"] = np.log(Dm.pm25)
Dm["hazeseason"] = Dm.month.between(8, 10).astype(int)
for c in ["temperature_c", "humidity_pct", "wind_speed_ms"]:
    Dm[c + "_z"] = (Dm[c] - Dm.groupby("station")[c].transform("mean")) / Dm[c].std()
fe = smf.ols("log_pm25 ~ temperature_c_z + humidity_pct_z + wind_speed_ms_z + C(dow) + C(month) + C(year) + C(station)",
             data=Dm).fit(cov_type="cluster", cov_kwds={"groups": Dm.station.astype("category").cat.codes})
fe_tab = pd.DataFrame({"coef_log": fe.params, "se": fe.bse, "p_value": fe.pvalues}).loc[
    ["temperature_c_z", "humidity_pct_z", "wind_speed_ms_z"]]
fe_tab["pct_change_per_1sd"] = (np.exp(fe_tab.coef_log) - 1) * 100
fe_tab["sd_unit"] = [Dm.temperature_c.std(), Dm.humidity_pct.std(), Dm.wind_speed_ms.std()]
fe_tab.loc["_model", "coef_log"] = fe.rsquared
save(fe_tab.round(4), "o3_meteo_fixed_effects", index=True)

# 3c. wind direction sectors
SECT = ["U", "TL", "T", "TG", "S", "BD", "B", "BL"]  # Utara, Timur Laut, ...
Hd = H2.dropna(subset=["wind_direction_deg", "pm25_ug_m3"]).copy()
Hd["sector"] = pd.cut((Hd.wind_direction_deg + 22.5) % 360, bins=np.arange(0, 361, 45), labels=SECT, include_lowest=True)
wd = Hd[~Hd.haze].groupby(["station", "sector"], observed=True)["pm25_ug_m3"].agg(["mean", "size"]).unstack()
wdm = wd["mean"].where(wd["size"] >= 100)
wds = pd.DataFrame({"dirtiest_sector": wdm.idxmax(axis=1), "dirtiest_pm25": wdm.max(axis=1),
                    "cleanest_sector": wdm.idxmin(axis=1), "cleanest_pm25": wdm.min(axis=1)})
wds["sector_ratio"] = wds.dirtiest_pm25 / wds.cleanest_pm25
wds = wds.join(wdm.round(1)).join(meta[["site_category"]])
save(wds.round(2), "o3_wind_sector_pm25", index=True)

# 3d. cross-station site characteristics (wet-season mean = local sources, without haze)
cs = D[D.season.str.startswith("Hujan")].groupby("station")[["pm25", "no2", "co", "pm10"]].mean()
cs = cs.join(meta[["traffic_intensity_per_h", "distance_to_road_m", "site_category", "island"]]).dropna(subset=["pm25", "no2", "co"])
srows = []
for y_ in ["pm25", "no2", "co"]:
    for x_ in ["traffic_intensity_per_h", "distance_to_road_m"]:
        r, p = stats.spearmanr(cs[x_], cs[y_])
        srows.append({"pollutant": y_, "factor": x_, "spearman_r": r, "p_value": p, "n_stations": len(cs)})
cs_corr = pd.DataFrame(srows)
save(cs_corr.round(4), "o3_site_factor_correlation")
cs_ols = smf.ols("np.log(pm25) ~ np.log(traffic_intensity_per_h) + np.log(distance_to_road_m)", data=cs).fit()
cs_cat = cs.groupby("site_category")[["pm25", "no2", "co"]].mean()
save(cs_cat.round(2), "o3_site_category_means_wetseason", index=True)
save(cs.round(2), "o3_station_wetseason_vs_site", index=True)

# 3e. pooled Random Forest + permutation importance (train 2024-2025, test 2026)
Df = D.dropna(subset=["pm25", "temperature_c", "humidity_pct", "wind_speed_ms", "wind_direction_deg"]).copy()
Df = Df.join(meta[["traffic_intensity_per_h", "distance_to_road_m"]], on="station")
Df["wd_sin"] = np.sin(np.radians(Df.wind_direction_deg))
Df["wd_cos"] = np.cos(np.radians(Df.wind_direction_deg))
Df["month_sin"] = np.sin(2 * np.pi * Df.month / 12)
Df["month_cos"] = np.cos(2 * np.pi * Df.month / 12)
Xcols = ["temperature_c", "humidity_pct", "wind_speed_ms", "wd_sin", "wd_cos", "month_sin", "month_cos", "dow",
         "traffic_intensity_per_h", "distance_to_road_m"]
X = pd.concat([Df[Xcols], pd.get_dummies(Df.site_category, prefix="tipe", dtype=float),
               pd.get_dummies(Df.island, prefix="pulau", dtype=float)], axis=1)
y = np.log(Df.pm25)
tr, te = Df.year < 2026, Df.year == 2026
rf = RandomForestRegressor(n_estimators=300, min_samples_leaf=5, n_jobs=-1, random_state=42).fit(X[tr], y[tr])
r2_test = rf.score(X[te], y[te])
pi = permutation_importance(rf, X[te], y[te], n_repeats=5, random_state=42, n_jobs=-1)
imp = pd.DataFrame({"feature": X.columns, "importance": pi.importances_mean, "std": pi.importances_std})
GROUP = {"temperature_c": "Suhu", "humidity_pct": "Kelembapan", "wind_speed_ms": "Kecepatan angin",
         "wd_sin": "Arah angin", "wd_cos": "Arah angin", "month_sin": "Musim (bulan)", "month_cos": "Musim (bulan)",
         "dow": "Hari dalam minggu", "traffic_intensity_per_h": "Intensitas lalu lintas",
         "distance_to_road_m": "Jarak ke jalan raya"}
imp["group"] = imp.feature.map(GROUP).fillna(imp.feature.str.split("_").str[0].map({"tipe": "Tipe lokasi", "pulau": "Pulau"}))
imp_g = imp.groupby("group").importance.sum().sort_values(ascending=False).to_frame()
imp_g["share_pct"] = imp_g.importance / imp_g.importance.clip(lower=0).sum() * 100
imp_g.loc["_R2_test_2026", "importance"] = r2_test
save(imp.round(5), "o3_rf_permutation_importance_features")
save(imp_g.round(4), "o3_rf_permutation_importance_groups", index=True)

# ---- figures objective 3 ----
fig, ax = plt.subplots(figsize=(8, 4.2))
ig = imp_g.drop("_R2_test_2026").sort_values("importance")
ax.barh(ig.index, ig.importance, color=SERIES[0], height=0.6)
for i, v in enumerate(ig.importance):
    ax.text(v, i, f"  {ig.share_pct.iloc[i]:.0f}%", va="center", fontsize=8, color=INK2)
ax.set_xlabel("Penurunan R² saat fitur diacak (permutation importance, data uji 2026)")
ax.set_title(f"Faktor paling berpengaruh terhadap PM2.5 harian (Random Forest, R² uji = {r2_test:.2f})")
ax.grid(axis="y", visible=False)
savefig(fig, "o3_driver_importance")

fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
for ax, ycol, lab_ in [(axes[0], "no2", "NO2"), (axes[1], "pm25", "PM2.5")]:
    for cat in CATS:
        g = cs[cs.site_category == cat]
        ax.scatter(g.traffic_intensity_per_h, g[ycol], color=CAT_COLOR[cat], s=60, edgecolor=SURFACE, linewidth=1.5, label=cat)
    r = cs_corr[(cs_corr.pollutant == ycol) & (cs_corr.factor == "traffic_intensity_per_h")].iloc[0]
    ax.set_title(f"{lab_} vs lalu lintas (Spearman ρ = {r.spearman_r:.2f}, p = {r.p_value:.3f})", fontsize=10)
    ax.set_xlabel("Kendaraan per jam")
    ax.set_ylabel(f"{lab_} musim hujan (µg/m³)")
    for s, rr in cs.iterrows():
        if rr.traffic_intensity_per_h > 2300 or rr[ycol] > cs[ycol].quantile(0.85):
            ax.annotate(s, (rr.traffic_intensity_per_h, rr[ycol]), fontsize=7, color=INK2, xytext=(4, 2), textcoords="offset points")
axes[1].legend(fontsize=7.5, loc="upper left", bbox_to_anchor=(1, 1))
fig.suptitle("Antarstasiun, intensitas lalu lintas berkorelasi kuat dengan PM2.5 musim hujan",
             x=0.01, y=1.03, ha="left", fontweight="bold", color=INK)
savefig(fig, "o3_traffic_scatter", "Rata-rata musim hujan (Nov–Apr) dipakai agar efek kabut asap tidak mendominasi.")

NAMA_SEKTOR = {"U": "Utara", "TL": "Timur Laut", "T": "Timur", "TG": "Tenggara", "S": "Selatan",
               "BD": "Barat Daya", "B": "Barat", "BL": "Barat Laut"}
fig, ax = plt.subplots(figsize=(9, 6.5))
ww = wds.dropna(subset=["sector_ratio"]).assign(pct=lambda x: (x.sector_ratio - 1) * 100).sort_values("pct")
ax.barh(ww.index, ww.pct, color=[SERIES[0] if v >= 10 else AXIS for v in ww.pct], height=0.7)
for k, (s_, r_) in enumerate(ww.iterrows()):
    ax.text(r_.pct + 0.4, k, f"dari {NAMA_SEKTOR[r_.dirtiest_sector]}", va="center", fontsize=7.5, color=INK2)
ax.set_xlabel("PM2.5 saat angin dari sektor terkotor vs sektor terbersih (%)")
ax.set_title("Arah angin hanya berpengaruh di 3 stasiun (selisih >10%)")
ax.grid(axis="y", visible=False)
ax.set_xlim(0, ww.pct.max() * 1.35)
savefig(fig, "o3_wind_direction_effect", "Hari non-kabut asap; sektor 45°, hanya sektor dengan ≥100 jam data.")

# ======================================================================================
# AUDIT ADDITIONS (booklet: evaluate vs baku mutu nasional incl. IKU; distinguish urban/industrial/clean
# background; factors for pollutants in general, not only PM2.5)
# ======================================================================================
# A1. calendar-year compliance with PP 22/2021 annual standards (2026 = 1 Jan - 14 Okt, partial year)
EXP_H = {2024: 366 * 24, 2025: 365 * 24, 2026: 287 * 24}
YP = ["pm25", "pm10", "so2", "no2", "o3"]
ann = H.groupby(["station", "year"]).agg(**{f"{p}_tahunan": (f"{p}_ug_m3", "mean") for p in YP},
                                         jam_valid_pm25=("pm25_ug_m3", "count")).reset_index()
ann["kelengkapan_pct"] = ann.jam_valid_pm25 / ann.year.map(EXP_H) * 100
ann["tahun_parsial"] = ann.year == 2026
for p in YP:
    ann[f"lolos_bm_{p}"] = ann[f"{p}_tahunan"] <= BM_YEAR[p]
ann = ann.merge(meta[["island", "site_category"]], left_on="station", right_index=True)
# IKU (Permen LHK 27/2021 refers to the KLHK air quality index from annual NO2 & SO2):
#   Ieu = ((NO2/40) + (SO2/20)) / 2 ;  IKU = 100 - (50/0.9) * (Ieu - 0.1), bounded 0-100
ann["Ieu"] = (ann.no2_tahunan / 40 + ann.so2_tahunan / 20) / 2
ann["IKU"] = (100 - (50 / 0.9) * (ann.Ieu - 0.1)).clip(0, 100)
ann["IKU_kategori"] = pd.cut(ann.IKU, [-0.1, 25, 50, 70, 90, 100.1],
                             labels=["Sangat Kurang", "Kurang", "Sedang", "Baik", "Sangat Baik"], right=False).astype(str)
save(ann.round(3), "o1_annual_compliance_iku")
comp_sum = ann[ann.kelengkapan_pct >= 75].groupby("year")[[f"lolos_bm_{p}" for p in YP]].agg(["sum", "size"])
save(comp_sum, "o1_annual_compliance_summary", index=True)

# A2. short-term standards PP 22/2021: 1-hour (SO2 150, NO2 200, CO 10000, O3 150) and 8-hour (CO 4000, O3 100)
BM_1H = {"so2": 150, "no2": 200, "co": 10000, "o3": 150}
st_ = H.groupby("station").agg(**{f"jam_lewat_bm1jam_{p}": (f"{p}_ug_m3", lambda x, t=t: int((x > t).sum())) for p, t in BM_1H.items()},
                               **{f"maks_1jam_{p}": (f"{p}_ug_m3", "max") for p in BM_1H})
st_["hari_lewat_bm8jam_co"] = D.groupby("station").exc_co_bm.sum()
st_["hari_lewat_bm8jam_o3"] = D.groupby("station").exc_o3_bm.sum()
st_["maks_8jam_co"] = D.groupby("station").co_8h_max.max()
st_["maks_8jam_o3"] = D.groupby("station").o3_8h_max.max()
for p in ["pm25", "pm10", "so2", "no2"]:
    st_[f"hari_lewat_bm24jam_{p}"] = D.groupby("station")[f"exc_{p}_bm"].sum()
st_ = st_.join(meta[["island", "site_category"]])
save(st_.round(1), "o1_shortterm_standards", index=True)

# A3. urban vs industrial vs clean background (booklet objective 2)
hz_st = D[D.haze_episode_day].groupby("station").size().reindex(prof.index).fillna(0)
cp = prof.groupby("site_category").agg(n_stasiun=("pm25_mean", "size"), stasiun=("pm25_mean", lambda x: ", ".join(sorted(x.index))),
                                       pm25=("pm25_mean", "mean"), pm10=("pm10_mean", "mean"), no2=("no2_mean", "mean"),
                                       co=("co_mean", "mean"), so2=("so2_mean", "mean"), o3=("o3_mean", "mean"),
                                       pct_hari_lewat_bm24jam_pm25=("pct_days_exceed_bm24h_pm25", "mean"))
cp["rasio_puncak_vs_terendah_harian"] = peak.groupby("site_category").peak_to_low_ratio.mean()
cp["kemarau_vs_hujan_pm25_pct"] = sea.groupby("site_category").dry_vs_wet_pct.mean()
cp["hari_kabut_asap_per_stasiun"] = hz_st.groupby(prof.site_category).mean()
cp["akhir_pekan_vs_hari_kerja_no2_pct"] = wk_cat["no2"]
cp = cp.reindex(CATS)
save(cp.round(2), "o2_site_category_profile", index=True)

# A4. factors for ALL pollutants (booklet objective 3 says "konsentrasi polutan")
ap = []
for st, g in H2[~H2.haze].groupby("station"):
    for p in POLL:
        for fct in ["temperature_c", "humidity_pct", "wind_speed_ms"]:
            x = g[[f"{p}_ug_m3", fct]].dropna()
            if len(x) > 500:
                ap.append({"station": st, "pollutant": p, "factor": fct, "r": stats.spearmanr(x.iloc[:, 0], x.iloc[:, 1])[0]})
ap = pd.DataFrame(ap)
ap_sum = ap.groupby(["pollutant", "factor"]).r.agg(r_rata2="mean", r_median="median",
                                                    n_stasiun_abs_r_gt_0_3=lambda x: int((x.abs() > 0.3).sum()),
                                                    n_stasiun="size").reset_index()
save(ap_sum.round(3), "o3_all_pollutants_meteo_correlation")
cs_all = D[D.season.str.startswith("Hujan")].groupby("station")[POLL].mean().join(
    meta[["traffic_intensity_per_h", "distance_to_road_m", "site_category"]]).dropna(subset=POLL)
sa = []
for p in POLL:
    for fct in ["traffic_intensity_per_h", "distance_to_road_m"]:
        r, pv = stats.spearmanr(cs_all[fct], cs_all[p])
        sa.append({"pollutant": p, "factor": fct, "spearman_r": r, "p_value": pv, "n_stasiun": len(cs_all)})
    kw = stats.kruskal(*[g[p].values for _, g in cs_all.groupby("site_category")])
    sa.append({"pollutant": p, "factor": "site_category (Kruskal-Wallis)", "spearman_r": np.nan, "p_value": kw.pvalue,
               "n_stasiun": len(cs_all)})
save(pd.DataFrame(sa).round(4), "o3_all_pollutants_site_factors")

print("compliance summary:\n", comp_sum)
print("IKU:\n", ann.groupby("year").IKU_kategori.value_counts().unstack(fill_value=0))
print(st_[[c for c in st_.columns if c.startswith(("jam_lewat", "hari_lewat_bm8"))]].sum())
print(cp.round(1).T)
print(ap_sum.round(2).to_string())
print(pd.DataFrame(sa).round(3).to_string())
print("R2 test RF:", round(r2_test, 3))
print("FE meteo:\n", fe_tab.round(3))
print("cross-station OLS:\n", cs_ols.params.round(3), cs_ols.pvalues.round(3), "R2", round(cs_ols.rsquared, 3))
print("done objectives 1-3")
