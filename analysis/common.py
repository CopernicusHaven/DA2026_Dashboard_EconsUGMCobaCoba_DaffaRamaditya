"""Shared paths, loaders, reference values and chart style for the Gelar Rasa 2026 analysis."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

BASE = Path(__file__).resolve().parents[1]
CLEAN = BASE / "output" / "clean"
TAB = BASE / "output" / "analysis"
FIG = BASE / "output" / "figures"
TAB.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

POLL = ["pm25", "pm10", "so2", "co", "o3", "no2"]
PLABEL = {"pm25": "PM2.5", "pm10": "PM10", "so2": "SO2", "co": "CO", "o3": "O3", "no2": "NO2"}

# Baku mutu udara ambien nasional - PP 22/2021 Lampiran VII (ug/m3)
BM_24H = {"pm25": 55, "pm10": 75, "so2": 75, "no2": 65}
BM_YEAR = {"pm25": 15, "pm10": 40, "so2": 45, "no2": 50, "o3": 35}
# WHO Air Quality Guidelines 2021 (ug/m3)
WHO_24H = {"pm25": 15, "pm10": 45, "so2": 40, "no2": 25}
WHO_YEAR = {"pm25": 5, "pm10": 15, "no2": 10}

ISLANDS = ["Sumatera", "Jawa", "Kalimantan", "Sulawesi", "Papua"]
CATS = ["Perkotaan", "Tepi Jalan (Lalu Lintas)", "Industri", "Gambut / Karhutla", "Latar Bersih"]

# ---- palette (validated reference instance, light mode) ----
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
ISLAND_COLOR = dict(zip(ISLANDS, SERIES[:5]))
CAT_COLOR = dict(zip(CATS, SERIES[:5]))
SEQ = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6",
       "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]
# ISPU Baik -> Berbahaya as a diverging scale: good (blue) | neutral midpoint (Sedang, gray) | bad (red ramp)
ORDINAL5 = ["#2a78d6", "#d3d1c9", "#f0a3a0", "#e34948", "#9e2323"]
CRITICAL = "#d03b3b"
DIVERGING = ["#2a78d6", "#86b6ef", "#f0efec", "#ec8a8a", "#e34948"]

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.family": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 10, "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "axes.titlecolor": INK, "axes.labelcolor": INK2, "axes.edgecolor": AXIS,
    "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelcolor": INK2, "ytick.labelcolor": INK2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
    "legend.labelcolor": INK2, "lines.linewidth": 2, "figure.dpi": 110, "savefig.dpi": 160,
})


def patches(mapping):
    """Legend handles for a {label: color} mapping (empty bar containers don't carry their color)."""
    from matplotlib.patches import Patch
    return [Patch(facecolor=c, label=l) for l, c in mapping.items()]


def savefig(fig, name, note=None):
    if note:
        fig.text(0.01, -0.02, note, fontsize=7.5, color=MUTED, ha="left", va="top")
    fig.savefig(FIG / f"{name}.png", bbox_inches="tight")
    plt.close(fig)


def save(df, name, index=False):
    df.to_csv(TAB / f"{name}.csv", index=index)
    return df


def load_dim():
    return pd.read_csv(CLEAN / "dim_station.csv")


def load_hourly(valid_only=True):
    h = pd.read_parquet(CLEAN / "aqms_hourly_clean.parquet")
    return h[h.used_in_analysis] if valid_only else h


def load_daily(valid_only=True):
    d = pd.read_csv(CLEAN / "aqms_daily.csv", parse_dates=["date"])
    return d[d.used_in_analysis] if valid_only else d


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = p2 - p1
    dl = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))
