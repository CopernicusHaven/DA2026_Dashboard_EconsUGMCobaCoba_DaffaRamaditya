"""
Objective 4: health impact of PM2.5 (lag effects, vulnerable groups)
Objective 5: adequacy of the monitoring network & priority areas
Run: python3 analysis/03_health_network.py
"""
import warnings
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
import re
import matplotlib.pyplot as plt
from common import *  # noqa: F401,F403

warnings.filterwarnings("ignore")


def fit_qp(formula, data):
    """Quasi-Poisson GLM with a convergence guard: IRLS occasionally diverges on these collinear lag terms
    (e.g. dispersion ~1e70); then refit from the converged no-exposure model as starting values."""
    m = smf.glm(formula, data=data, family=sm.families.Poisson()).fit(scale="X2", maxiter=100)
    if m.converged and np.isfinite(m.scale) and m.scale < 50:
        return m
    base_f = re.sub(r"~\s*[^+]+\+", "~ ", formula, count=1)
    m0 = smf.glm(base_f, data=data, family=sm.families.Poisson()).fit(maxiter=100)
    mod = smf.glm(formula, data=data, family=sm.families.Poisson())
    start = pd.Series(0.0, index=mod.exog_names)
    start.loc[m0.params.index] = m0.params
    m = mod.fit(start_params=start.values, scale="X2", maxiter=300)
    if not (m.converged and np.isfinite(m.scale) and m.scale < 50):
        raise RuntimeError(f"GLM did not converge: {formula[:60]}")
    return m

dim = load_dim()
meta = dim.set_index("station")
M = pd.read_csv(CLEAN / "health_aq_daily_merged.csv", parse_dates=["date"])
q = pd.read_csv(CLEAN / "data_quality_station.csv").set_index("station")
prof = pd.read_csv(TAB / "o1_station_profile.csv", index_col=0)
D = load_daily()

OUT = {"resp_admissions_under5": "ISPA balita (<5 th)", "resp_admissions_over60": "ISPA lansia (>60 th)",
       "asthma_emergency_cases": "Darurat asma", "copd_admissions": "PPOK", "resp": "Pernapasan umum (semua umur)",
       "cvd": "Kardiovaskular", "death": "Kematian"}
EXPO = ["pm25"] + [f"pm25_lag{L}" for L in range(1, 8)] + ["pm25_ma02", "pm25_ma07"]
EXPO_LABEL = {"pm25": "lag 0"} | {f"pm25_lag{L}": f"lag {L}" for L in range(1, 8)} | \
             {"pm25_ma02": "rata-rata lag 0–2", "pm25_ma07": "rata-rata lag 0–7"}
M["dow"] = M["date"].dt.dayofweek
# The PM2.5-health curve flattens at extreme haze levels (see 4d), so a single log-linear slope fitted over
# 0-1000 ug/m3 is dominated by a few extreme days. Per-10 ug/m3 effects are therefore estimated on days
# where every lag 0-7 is <= 150.4 ug/m3 (ISPU <= Tidak Sehat; ~99% of hospital-days). Full range -> 4d bands.
LAGC = ["pm25"] + [f"pm25_lag{L}" for L in range(1, 8)]
M["in_range"] = ~(M[LAGC] > 150.4).any(axis=1)  # missing lags allowed here; the DLM itself needs all 8
MR = M[M.in_range]
BASE_F = "cr(day_index, df=12, constraints='center') + cr(temp_c, df=3, constraints='center') + rhum_pct + C(dow) + C(hospital_id)"

# ======================================================================================
# OBJECTIVE 4 - health
# ======================================================================================
# 4a. descriptive: admissions per 100 beds by ISPU category of the same day
desc = M.dropna(subset=["ispu_kategori"]).copy()
for o in OUT:
    desc[o + "_p100"] = desc[o] / desc.kapasitas_tempat_tidur * 100
by_ispu = desc.groupby("ispu_kategori")[[o + "_p100" for o in OUT]].mean()
by_ispu.columns = list(OUT)
by_ispu_rel = by_ispu / by_ispu.loc["2 Sedang"]
by_ispu["n_hari_rs"] = desc.groupby("ispu_kategori").size()
save(by_ispu.round(3), "o4_admissions_per100beds_by_ispu", index=True)
save(by_ispu_rel.round(3), "o4_admissions_relative_to_sedang", index=True)

# 4b. lag analysis: quasi-Poisson GLM, hospital fixed effects, smooth time trend & temperature
#     log E[y] = b*PM2.5(lag)/10 + cr(day, 12 df) + cr(temp, 3 df) + RH + DOW + hospital
#     Splines use constraints="center": an uncentred cr() basis sums to 1, duplicates the intercept and made
#     IRLS fail to converge (one model even returned dispersion ~1e70).
rows = []
for o in OUT:
    for e in EXPO:
        d = MR.dropna(subset=[o, e, "temp_c", "rhum_pct"]).copy()
        d["x10"] = d[e] / 10
        f = f"{o} ~ x10 + {BASE_F}"
        m = fit_qp(f, d)
        b, se = m.params["x10"], m.bse["x10"]
        rows.append({"outcome": o, "outcome_label": OUT[o], "exposure": e, "lag_label": EXPO_LABEL[e],
                     "beta": b, "se": se, "RR_per10": np.exp(b), "RR_low": np.exp(b - 1.96 * se),
                     "RR_high": np.exp(b + 1.96 * se), "pct_increase_per10": (np.exp(b) - 1) * 100,
                     "p_value": m.pvalues["x10"], "dispersion": m.scale, "n": int(m.nobs)})
lag = pd.DataFrame(rows)
save(lag.round(5), "o4_lag_rr_all_outcomes")
best = lag[lag.exposure.str.match(r"pm25(_lag\d)?$")].sort_values("RR_per10", ascending=False).groupby("outcome").head(1)
best = best.set_index("outcome")[["outcome_label", "lag_label", "RR_per10", "RR_low", "RR_high", "pct_increase_per10", "p_value"]]
save(best.round(4), "o4_peak_lag_by_outcome", index=True)

# 4b'. distributed-lag model: lags 0-7 entered jointly (unconstrained). Single-lag models cannot separate
#      lags because haze keeps PM2.5 high for weeks (corr lag0-lag1 = 0.99), but with ~24k hospital-days the
#      joint model is still precise (+/-1-1.5% per lag). A quadratic-constrained version was tested and
#      rejected: it forced a U-shape and created an artificial rise at lag 7.
dlm_rows = []
Ls = np.arange(8)
for o in OUT:
    d = MR.dropna(subset=[o, "temp_c", "rhum_pct"] + LAGC).copy()
    xs = []
    for c in LAGC:
        d[c + "_10"] = d[c] / 10
        xs.append(c + "_10")
    m = fit_qp(f"{o} ~ {' + '.join(xs)} + {BASE_F}", d)
    g, V = m.params[xs].values, m.cov_params().loc[xs, xs].values
    for L in list(Ls) + ["kumulatif 0-7"]:
        c = np.ones(8) if isinstance(L, str) else np.eye(8)[L]
        b, se = c @ g, np.sqrt(c @ V @ c)
        dlm_rows.append({"outcome": o, "outcome_label": OUT[o], "lag": L, "beta": b, "se": se,
                         "pct_increase_per10": (np.exp(b) - 1) * 100, "pct_low": (np.exp(b - 1.96 * se) - 1) * 100,
                         "pct_high": (np.exp(b + 1.96 * se) - 1) * 100, "p_value": 2 * (1 - __import__("scipy").stats.norm.cdf(abs(b / se))),
                         "n": int(m.nobs)})
dlm = pd.DataFrame(dlm_rows)
save(dlm.round(4), "o4_distributed_lag_model")
dl = dlm[dlm.lag != "kumulatif 0-7"].copy()
dl["lag"] = dl.lag.astype(int)
peak_dlm = dl.loc[dl.groupby("outcome").pct_increase_per10.idxmax(), ["outcome", "outcome_label", "lag", "pct_increase_per10"]]
peak_dlm = peak_dlm.merge(dlm[dlm.lag == "kumulatif 0-7"][["outcome", "pct_increase_per10", "pct_low", "pct_high"]]
                          .rename(columns={"pct_increase_per10": "cumulative_pct_0_7", "pct_low": "cum_low", "pct_high": "cum_high"}), on="outcome")
save(peak_dlm.round(3), "o4_dlm_peak_and_cumulative")

# sensitivity: fewer time df (6) and excluding extreme days (PM2.5 > 250)
sens = []
for o in ["resp_admissions_under5", "resp_admissions_over60", "resp", "death"]:
    for lab, df_t, cap in [("utama: rentang ≤150,4 (df waktu 12)", 12, 150.4), ("rentang ≤150,4, df waktu 6", 6, 150.4),
                           ("rentang ≤250,4", 12, 250.4), ("seluruh rentang (termasuk kabut ekstrem)", 12, None)]:
        d = M.dropna(subset=[o, "pm25_ma02", "temp_c", "rhum_pct"]).copy()
        if cap:
            d = d[d.pm25_ma02 <= cap]
        d["x10"] = d.pm25_ma02 / 10
        m = fit_qp(f"{o} ~ x10 + cr(day_index, df={df_t}, constraints='center') + cr(temp_c, df=3, constraints='center') + rhum_pct + C(dow) + C(hospital_id)", d)
        sens.append({"outcome": OUT[o], "model": lab, "RR_per10": np.exp(m.params.x10),
                     "RR_low": np.exp(m.params.x10 - 1.96 * m.bse.x10), "RR_high": np.exp(m.params.x10 + 1.96 * m.bse.x10)})
save(pd.DataFrame(sens).round(4), "o4_sensitivity")

# 4c. vulnerability: under-5 vs over-60 (ma 0-2), pooled + by island
vul = []
for scope, d0 in [("Semua RS", MR)] + [(i, MR[MR.island == i]) for i in ISLANDS]:
    rr = {}
    for o in ["resp_admissions_under5", "resp_admissions_over60"]:
        d = d0.dropna(subset=[o, "pm25_ma02", "temp_c", "rhum_pct"]).copy()
        if d.hospital_id.nunique() < 1 or len(d) < 300:
            continue
        d["x10"] = d.pm25_ma02 / 10
        fe = " + C(hospital_id)" if d.hospital_id.nunique() > 1 else ""
        m = fit_qp(f"{o} ~ x10 + cr(day_index, df=12, constraints='center') + cr(temp_c, df=3, constraints='center') + rhum_pct + C(dow){fe}", d)
        rr[o] = (m.params.x10, m.bse.x10)
        vul.append({"scope": scope, "group": OUT[o], "RR_per10": np.exp(m.params.x10),
                    "RR_low": np.exp(m.params.x10 - 1.96 * m.bse.x10), "RR_high": np.exp(m.params.x10 + 1.96 * m.bse.x10),
                    "pct_increase_per10": (np.exp(m.params.x10) - 1) * 100, "n_hospitals": d.hospital_id.nunique(),
                    "pm25_ma02_mean": d.pm25_ma02.mean()})
    if len(rr) == 2:
        (b1, s1), (b2, s2) = rr["resp_admissions_under5"], rr["resp_admissions_over60"]
        z = (b1 - b2) / np.sqrt(s1 ** 2 + s2 ** 2)
        vul.append({"scope": scope, "group": "Rasio RR balita/lansia", "RR_per10": np.exp(b1 - b2),
                    "pct_increase_per10": (np.exp(b1 - b2) - 1) * 100, "z_diff": z})
vul = pd.DataFrame(vul)
save(vul.round(4), "o4_vulnerability_under5_vs_over60")

# 4d. exposure-response by ISPU PM2.5 band (ma 0-2) relative to 'Baik' band
bands = [0, 15.5, 55.4, 150.4, 250.4, 1e9]
blab = ["Baik (≤15,5)", "Sedang (15,5–55,4)", "Tidak Sehat (55,4–150,4)", "Sangat Tidak Sehat (150,4–250,4)", "Berbahaya (>250,4)"]
er = []
Mb = M.dropna(subset=["pm25_ma02", "temp_c", "rhum_pct"]).copy()
Mb["band"] = pd.cut(Mb.pm25_ma02, bands, labels=blab)
for o in OUT:
    m = fit_qp(f"{o} ~ C(band, Treatment(reference='{blab[0]}')) + cr(day_index, df=12, constraints='center') + cr(temp_c, df=3, constraints='center') + rhum_pct + C(dow) + C(hospital_id)", Mb.dropna(subset=[o]))
    er.append({"outcome": OUT[o], "band": blab[0], "RR": 1.0, "RR_low": 1.0, "RR_high": 1.0,
               "n_days": int((Mb.band == blab[0]).sum())})
    for b_ in blab[1:]:
        k = f"C(band, Treatment(reference='{blab[0]}'))[T.{b_}]"
        if k in m.params:
            er.append({"outcome": OUT[o], "band": b_, "RR": np.exp(m.params[k]),
                       "RR_low": np.exp(m.params[k] - 1.96 * m.bse[k]), "RR_high": np.exp(m.params[k] + 1.96 * m.bse[k]),
                       "n_days": int((Mb.band == b_).sum())})
er = pd.DataFrame(er)
save(er.round(4), "o4_exposure_response_ispu_band")

# 4e. haze episode days vs normal days (same hospital), and attributable cases above WHO 24h guideline
hz = []
for o in OUT:
    g = M.dropna(subset=["haze_episode_day"]).groupby(["hospital_id", "haze_episode_day"])[o].mean().unstack()
    g = g.dropna()
    hz.append({"outcome": OUT[o], "n_hospitals_with_haze": len(g), "mean_normal": g[False].mean(),
               "mean_haze": g[True].mean(), "pct_increase": (g[True].sum() / g[False].sum() - 1) * 100})
hz = pd.DataFrame(hz)
save(hz.round(3), "o4_haze_vs_normal_days")

# attributable cases vs a 'Baik' day (PM2.5 3-day mean <= 15.5, ~WHO 24h guideline), using the band RRs of 4d
# (non-parametric, so it stays valid across the whole exposure range): AF_day = 1 - 1/RR_band
attr = []
for o in OUT:
    rr_map = er[er.outcome == OUT[o]].set_index("band").RR
    d = Mb.dropna(subset=[o, "band"]).copy()
    rr_d = d.band.astype(str).map(rr_map).clip(lower=1.0)
    d["attr"] = d[o] * (1 - 1 / rr_d)
    by = d.groupby("island").agg(total_cases=(o, "sum"), attributable=("attr", "sum"))
    by.loc["Total"] = by.sum()
    by["attributable_pct"] = by.attributable / by.total_cases * 100
    by["outcome"] = OUT[o]
    attr.append(by.reset_index())
attr = pd.concat(attr)
save(attr.round(2), "o4_attributable_cases_above_who")

# per-hospital burden table for dashboard
hb = M.groupby(["hospital_id", "nama_rumah_sakit", "station", "exposure_station", "island", "provinsi",
                "kelas_faskes", "kapasitas_tempat_tidur"]).agg(
    pm25_mean=("pm25", "mean"), resp_u5_daily=("resp_admissions_under5", "mean"),
    resp_o60_daily=("resp_admissions_over60", "mean"), resp_daily=("resp", "mean"),
    cvd_daily=("cvd", "mean"), death_daily=("death", "mean"), resp_per100beds=("resp_per100beds", "mean")).reset_index()
save(hb.round(2), "o4_hospital_burden")

# ---- figures objective 4 ----
fig, axes = plt.subplots(2, 4, figsize=(13, 6.2), sharex=True)
for ax, o in zip(axes.flat, OUT):
    g = dl[dl.outcome == o].sort_values("lag")
    ax.fill_between(g.lag, g.pct_low, g.pct_high, color="#cde2fb", lw=0)
    ax.plot(g.lag, g.pct_increase_per10, color=SERIES[0], marker="o", ms=4)
    ax.axhline(0, color=INK2, lw=1)
    l0 = g[g.lag == 0].pct_increase_per10.iat[0]
    cum = dlm[(dlm.outcome == o) & (dlm.lag == "kumulatif 0-7")].iloc[0]
    ax.set_title(f"{OUT[o]}\nlag 0: +{l0:.1f}%  ·  kumulatif 0–7: +{cum.pct_increase_per10:.1f}%", fontsize=9)
    ax.set_xticks(range(8))
axes.flat[-1].set_visible(False)
for a in axes[1]:
    a.set_xlabel("Jeda setelah paparan (hari)")
for a in axes[:, 0]:
    a.set_ylabel("% kenaikan kasus\nper +10 µg/m³ PM2.5")
fig.suptitle("Efek PM2.5 terkonsentrasi pada hari yang sama (lag 0); jeda 1–7 hari tidak menambah risiko", x=0.01, y=1.04, ha="left", fontweight="bold", color=INK)
savefig(fig, "o4_lag_response", "Hari dengan PM2.5 lag 0–7 ≤150,4 µg/m³ (≈99% data). Kontrol: tren waktu, suhu, kelembapan, hari, efek tetap RS.")

fig, ax = plt.subplots(figsize=(9.5, 4.6))
sub = er[er.outcome.isin([OUT["resp_admissions_under5"], OUT["resp_admissions_over60"]])]
xs = np.arange(len(blab))
for k, (grp, col) in enumerate([(OUT["resp_admissions_under5"], SERIES[1]), (OUT["resp_admissions_over60"], SERIES[0])]):
    g = sub[sub.outcome == grp].set_index("band").reindex(blab)
    off = (k - 0.5) * 0.28
    ax.bar(xs + off, g.RR - 1, width=0.26, bottom=1, color=col, label=grp)
    ax.errorbar(xs + off, g.RR, yerr=[g.RR - g.RR_low, g.RR_high - g.RR], fmt="none", ecolor=INK2, lw=1, capsize=2)
ax.axhline(1, color=INK2, lw=1)
ax.set_xticks(xs, [b.replace(" (", "\n(") for b in blab], fontsize=8)
ax.set_ylabel("Risiko relatif vs hari 'Baik'")
ax.set_title("Kasus ISPA naik bertahap mengikuti kategori ISPU PM2.5 (rata-rata 3 hari)")
ax.legend(loc="upper left")
ax.grid(axis="x", visible=False)
savefig(fig, "o4_exposure_response_band")

# ======================================================================================
# OBJECTIVE 5 - monitoring network adequacy
# ======================================================================================
allst = dim.set_index("station")
lat, lon = allst.latitude_dd.values, allst.longitude_dd.values
dist = haversine_km(lat[:, None], lon[:, None], lat[None, :], lon[None, :])
np.fill_diagonal(dist, np.inf)
nn = pd.DataFrame({"nearest_station": allst.index[dist.argmin(axis=1)], "nn_distance_km": dist.min(axis=1)}, index=allst.index)

log = pd.read_csv(CLEAN / "cleaning_log.csv")
issues = log[log.station != "HLT-01"].copy()
issues["issue"] = issues.rule.str.extract(r"^(Konversi satuan|Flatline|QC flag bukan VALID|Token non-numerik|Nilai sentinel|Jam tanpa rekaman|Timestamp invalid|Jendela 15 menit)")[0]
iss = issues.dropna(subset=["issue"]).groupby(["station", "issue"]).n_affected.max().unstack().fillna(0)

net = allst[["island", "provinsi", "kota_kabupaten", "site_category", "status_operasional", "tanggal_instalasi",
             "model_sensor", "latitude_dd", "longitude_dd"]].join(nn).join(
    q[["completeness_pm25_pct", "used_in_analysis"]]).join(prof[["pm25_mean", "pct_days_exceed_bm24h_pm25"]])
net["haze_days"] = D[D.haze_episode_day].groupby("station").size().reindex(net.index).fillna(0)
# no data is borrowed from other stations: where a station has too few valid days (JMB-02 defective,
# MER-01 intermittent) its pollution/haze indicators stay missing instead of being filled in
valid_days_share = D.groupby("station").pm25.apply(lambda s: s.notna().mean()).reindex(net.index)
net.loc[valid_days_share.fillna(0) < 0.5, ["haze_days", "pct_days_exceed_bm24h_pm25"]] = np.nan
net = net.join(iss.add_prefix("issue_"))
net["n_stasiun_provinsi"] = net.groupby("provinsi").provinsi.transform("size")
net["n_stasiun_pulau"] = net.groupby("island").island.transform("size")
hb2 = hb.set_index("station")
net["resp_per100beds"] = hb2.resp_per100beds
net["resp_u5_daily"] = hb2.resp_u5_daily

# reliability flag
def reliability(r):
    if r.status_operasional == "Defective" or r.completeness_pm25_pct < 50:
        return "Kritis - ganti/perbaiki"
    if r.completeness_pm25_pct < 75 or r.get("issue_Flatline", 0) > 0:
        return "Buruk - perlu kalibrasi/perawatan"
    if r.status_operasional == "Intermittent" or r.get("issue_Konversi satuan", 0) > 0:
        return "Perlu standardisasi"
    return "Baik"


net["reliability"] = net.apply(reliability, axis=1)
ACTION = {"Kritis - ganti/perbaiki": "Ganti/perbaiki sensor segera", "Buruk - perlu kalibrasi/perawatan": "Kalibrasi & perawatan, audit QC",
          "Perlu standardisasi": "Standardisasi satuan/resolusi logger", "Baik": "Pertahankan"}
net["aksi_alat"] = net.reliability.map(ACTION)

# priority score (0-100) for strengthening monitoring around each station area
# min-max scaling of actual values (ranks would exaggerate tiny gaps such as 97% vs 99% completeness)
mm = lambda x: (x - x.min()) / (x.max() - x.min())
comp = pd.DataFrame(index=net.index)
comp["polusi"] = mm(net.pm25_mean)
comp["kabut_asap"] = mm(net.haze_days)
comp["beban_kesehatan"] = mm(net.resp_per100beds)
comp["defisit_data"] = (100 - net.completeness_pm25_pct) / 100
comp["keterisolasian"] = mm(np.log(net.nn_distance_km))
W = {"polusi": 0.25, "kabut_asap": 0.20, "beban_kesehatan": 0.20, "defisit_data": 0.20, "keterisolasian": 0.15}
# missing components are NOT imputed: the score is the weighted mean of the components that exist
wsum = sum(comp[k].notna() * w for k, w in W.items())
net["priority_score"] = sum(comp[k].fillna(0) * w for k, w in W.items()) / wsum * 100
net["komponen_tidak_tersedia"] = comp.apply(lambda r: ", ".join(k for k in W if pd.isna(r[k])), axis=1)
net = net.join(comp.add_prefix("komp_"))
net["_wsum"] = wsum
net = net.sort_values("priority_score", ascending=False)
save(net.drop(columns="_wsum").round(3), "o5_network_station_assessment", index=True)

# island coverage
cov = net.groupby("island").agg(n_stasiun=("provinsi", "size"), n_provinsi_tercakup=("provinsi", "nunique"),
                                n_stasiun_andal=("reliability", lambda s: (s == "Baik").sum()),
                                kelengkapan_rata2_pct=("completeness_pm25_pct", "mean"),
                                jarak_tetangga_median_km=("nn_distance_km", "median"),
                                pm25_mean=("pm25_mean", "mean"), hari_kabut_asap=("haze_days", "sum"))
cov["tipe_lokasi"] = net.groupby("island").site_category.agg(lambda s: ", ".join(f"{k} {v}" for k, v in s.value_counts().items()))
# coverage gaps derived ONLY from the station coordinates in the dataset (no external map/province list):
# minimum spanning tree (MST) of each island's stations -> its longest edges are the widest stretches
# between neighbouring stations, i.e. corridors without monitoring.
from scipy.sparse.csgraph import minimum_spanning_tree
gap_rows = []
for isl_ in ISLANDS:
    sub_ = allst[allst.island == isl_]
    if len(sub_) < 2:
        continue
    la, lo = sub_.latitude_dd.values, sub_.longitude_dd.values
    dm = haversine_km(la[:, None], lo[:, None], la[None, :], lo[None, :])
    mst = minimum_spanning_tree(dm).tocoo()
    for i_, j_, d_ in zip(mst.row, mst.col, mst.data):
        a_, b_ = sub_.index[i_], sub_.index[j_]
        gap_rows.append({"island": isl_, "station_a": a_, "station_b": b_, "jarak_km": d_,
                         "kab_kota_a": sub_.loc[a_, "kota_kabupaten"], "kab_kota_b": sub_.loc[b_, "kota_kabupaten"],
                         "titik_tengah_lat": (la[i_] + la[j_]) / 2, "titik_tengah_lon": (lo[i_] + lo[j_]) / 2})
gaps = pd.DataFrame(gap_rows).sort_values("jarak_km", ascending=False)
save(gaps.round(3), "o5_monitoring_gap_corridors")
cov["celah_terlebar_km"] = gaps.groupby("island").jarak_km.max()
cov["celah_terlebar_antara"] = gaps.loc[gaps.groupby("island").jarak_km.idxmax()].set_index("island").apply(
    lambda r: f"{r.station_a} – {r.station_b}", axis=1)
cov = cov.reindex(ISLANDS)
save(cov.round(2), "o5_island_coverage", index=True)

# ---- figures objective 5 ----
fig, ax = plt.subplots(figsize=(12, 5.2))
REL = {"Baik": SERIES[0], "Perlu standardisasi": SERIES[3], "Buruk - perlu kalibrasi/perawatan": SERIES[1],
       "Kritis - ganti/perbaiki": CRITICAL}
for rel, col in REL.items():
    g = net[net.reliability == rel]
    ax.scatter(g.longitude_dd, g.latitude_dd, s=np.nan_to_num(g.pm25_mean, nan=20) * 6, color=col, alpha=0.85,
               edgecolor=SURFACE, linewidth=1.5, label=rel)
for _, gr in gaps.iterrows():
    pa, pb = allst.loc[gr.station_a], allst.loc[gr.station_b]
    wide = gr.jarak_km >= 300
    ax.plot([pa.longitude_dd, pb.longitude_dd], [pa.latitude_dd, pb.latitude_dd], color=CRITICAL if wide else AXIS,
            lw=1.4 if wide else 0.8, ls="--" if wide else "-", zorder=0)
    if gr.jarak_km >= 350:
        ax.text(gr.titik_tengah_lon, gr.titik_tengah_lat, f"{gr.jarak_km:.0f} km", fontsize=7, color=CRITICAL,
                ha="center", va="bottom")
GROUPED = {"JKT-01", "JKT-02", "JKT-03", "BGR-01", "BGR-02", "JMB-02", "KTG-02"}
for s_, r in net.iterrows():
    if s_ not in GROUPED:
        lab_ = {"JMB-01": "JMB-01/02", "KTG-01": "KTG-01/02"}.get(s_, s_)
        ax.annotate(lab_, (r.longitude_dd, r.latitude_dd), xytext=(5, 4), textcoords="offset points", fontsize=7, color=INK2)
ax.annotate("JKT-01/02/03,\nBGR-01/02", (106.8, -6.4), xytext=(-62, -26), textcoords="offset points", fontsize=7, color=INK2,
            arrowprops={"arrowstyle": "-", "color": AXIS, "lw": 0.8})
for isl_, (x_, y_) in {"SUMATERA": (95, 1.6), "JAWA": (108, -8.8), "KALIMANTAN": (114.5, 1.8),
                       "SULAWESI": (121.5, -3.0), "PAPUA": (134, -5.5)}.items():
    ax.text(x_, y_, isl_, fontsize=11, color=AXIS, fontweight="bold")
ax.set_xlim(94, 142)
ax.set_ylim(-10, 7)
ax.set_aspect("equal")
ax.set_xlabel("Bujur")
ax.set_ylabel("Lintang")
ax.set_title("Sebaran 27 stasiun: rapat di Jawa & Sumatera, jarang di Sulawesi & Papua")
from matplotlib.lines import Line2D
ax.legend(handles=[Line2D([], [], marker="o", ls="", color=c, markersize=8, label=l) for l, c in REL.items()],
          loc="upper right", fontsize=8, title="Keandalan data", title_fontsize=8)
savefig(fig, "o5_network_map", "Ukuran titik ∝ rata-rata PM2.5. Garis = pohon rentang minimum antarstasiun per pulau; merah putus-putus = celah ≥300 km. Tanpa garis pantai (dataset tidak menyertakan peta dasar).")

fig, ax = plt.subplots(figsize=(10, 7))
nn_ = net.sort_values("priority_score")
left = np.zeros(len(nn_))
CW = {"polusi": SERIES[0], "kabut_asap": SERIES[1], "beban_kesehatan": SERIES[2], "defisit_data": SERIES[3], "keterisolasian": SERIES[4]}
for k, col in CW.items():
    v = nn_[f"komp_{k}"].fillna(0) * W[k] / nn_["_wsum"] * 100
    ax.barh(nn_.index, v, left=left, color=col, height=0.72, edgecolor=SURFACE, linewidth=1,
            label=f"{k.replace('_', ' ').title()} ({int(W[k] * 100)}%)")
    left += v
ax.set_xlabel("Skor prioritas penguatan pemantauan (0–100)")
ax.set_title("Prioritas penguatan jaringan pemantauan per wilayah stasiun")
for k_, (s_, r_) in enumerate(nn_.iterrows()):
    if r_.komponen_tidak_tersedia:
        ax.text(r_.priority_score + 0.8, k_, "tanpa komponen: " + r_.komponen_tidak_tersedia.replace("_", " "),
                va="center", fontsize=7, color=MUTED)
ax.legend(loc="lower right", fontsize=8)
ax.grid(axis="y", visible=False)
savefig(fig, "o5_priority_score")

print(peak_dlm.round(3).to_string())
print(best.round(3).to_string())
print(vul.round(3).to_string())
print(hz.round(2).to_string())
print(net[["island", "provinsi", "reliability", "completeness_pm25_pct", "nn_distance_km", "priority_score"]].round(1).head(12).to_string())
print("done objectives 4-5")
