// Palette: validated categorical/sequential/diverging reference palette (light + dark steps) + Gelar Rasa accents.
// Theme-dependent values are live bindings: applyTheme() swaps them and the views re-render.
export const NAVY = '#1b2550';
export const YELLOW = '#fde03a';
// chart / map font (Poppins); interface font is Helvetica (see styles.css)
export const FONT = '"Helvetica Neue", Helvetica, Arial, sans-serif';

// Text is pure black (light) or pure white (dark); lines and data colours are the only greys/colours.
const THEMES = {
  light: {
    ink: '#000000', ink2: '#000000', muted: '#000000', grid: '#eceef2', axis: '#d3d6de', crit: '#d03b3b', surf: '#ffffff', tip: '#ffffff', stroke: '#ffffff',
    series: ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6', '#e34948'],
    ispu: ['#2a78d6', '#c9ccd4', '#f0a3a0', '#e34948', '#9e2323'],
    seq: ['#f3f7fe', '#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5'],
    div: ['#6da7ec', '#cde2fb', '#f3f4f6', '#f6c3c1', '#ec8a8a'],
    years: ['#9ec5f4', '#3987e5', '#0d366b'],
    // islands and site types: no blue (blue = Baik) and no red (red = buruk)
    nominal: ['#6250d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4'],
    // intensity (heatmap): light to dark warm, higher = worse
    heat: ['#fdf6ec', '#fbe1b8', '#f6bd7f', '#ee9150', '#da5f31', '#ad3423'],
  },
  dark: {
    ink: '#ffffff', ink2: '#ffffff', muted: '#ffffff', grid: 'rgba(255,255,255,0.07)', axis: 'rgba(255,255,255,0.18)', crit: '#ef6b6b', surf: '#18191c', tip: '#222327', stroke: '#ffffff',
    series: ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181', '#008300', '#9085e9', '#e66767'],
    ispu: ['#3987e5', '#5c606b', '#e88b8b', '#e66767', '#b33a3a'],
    seq: ['#1f2330', '#1b2d52', '#1d3f7a', '#1c5cab', '#2a78d6'],
    div: ['#1c5cab', '#22355a', '#2a2c33', '#5e2f37', '#a33a3a'],
    years: ['#25406e', '#2a78d6', '#9ec5f4'],
    nominal: ['#9085e9', '#d95926', '#199e70', '#c98500', '#d55181'],
    heat: ['#26231f', '#4a3424', '#7a4626', '#b0592a', '#e0793c', '#f7ad6f'],
  },
};

export let THEME = 'light';
export let INK, INK2, MUTED, GRID, AXIS, CRIT, SURF, TIPBG, STROKE;
export const SERIES = [], ISPU_C = [], SEQ = [], DIV = [], YEARS = [], NOMINAL = [], HEAT = [];
export const ISL = ['Sumatera', 'Jawa', 'Kalimantan', 'Sulawesi', 'Papua'];
export const CATS = ['Perkotaan', 'Tepi Jalan (Lalu Lintas)', 'Industri', 'Gambut / Karhutla', 'Latar Bersih'];
export const CAT_S = { 'Perkotaan': 'Perkotaan', 'Tepi Jalan (Lalu Lintas)': 'Tepi jalan', 'Industri': 'Industri', 'Gambut / Karhutla': 'Tepi lahan gambut', 'Latar Bersih': 'Latar regional' };
export const C_ISL = {}, C_CAT = {}, C_OUT = {}, REL_C = {};
export const ISPU_L = ['Baik', 'Sedang', 'Tidak Sehat', 'Sangat Tidak Sehat', 'Berbahaya'];
// IKU categories use the ISPU colours: good is blue, middle is grey, bad is red
export const IKU_IDX = { 'Sangat Baik': 0, 'Baik': 0, 'Sedang': 1, 'Kurang': 2, 'Sangat Kurang': 3 };

export function applyTheme(name) {
  const t = THEMES[name] || THEMES.dark;
  THEME = name in THEMES ? name : 'dark';
  ({ ink: INK, ink2: INK2, muted: MUTED, grid: GRID, axis: AXIS, crit: CRIT, surf: SURF, tip: TIPBG, stroke: STROKE } = t);
  SERIES.splice(0, SERIES.length, ...t.series); ISPU_C.splice(0, 5, ...t.ispu);
  SEQ.splice(0, SEQ.length, ...t.seq); DIV.splice(0, DIV.length, ...t.div); YEARS.splice(0, 3, ...t.years);
  NOMINAL.splice(0, NOMINAL.length, ...t.nominal); HEAT.splice(0, HEAT.length, ...t.heat);
  ISL.forEach((k, i) => { C_ISL[k] = NOMINAL[i]; });
  CATS.forEach((k, i) => { C_CAT[k] = NOMINAL[i]; });
  Object.assign(C_OUT, { resp_admissions_under5: SERIES[1], resp_admissions_over60: SERIES[0], asthma_emergency_cases: SERIES[2], copd_admissions: SERIES[3], resp: SERIES[6], cvd: SERIES[4], death: SERIES[7] });
  Object.assign(REL_C, { 'Baik': SERIES[0], 'Perlu standardisasi': SERIES[3], 'Buruk - perlu kalibrasi/perawatan': SERIES[1], 'Kritis - ganti/perbaiki': CRIT });
}
applyTheme('dark');

// reliability classes in the data and the words shown to users
export const REL_LABEL = { 'Baik': 'Baik', 'Perlu standardisasi': 'Perlu penyesuaian', 'Buruk - perlu kalibrasi/perawatan': 'Buruk', 'Kritis - ganti/perbaiki': 'Kritis' };
export const POL = { pm25: 'PM2.5', pm10: 'PM10', so2: 'SO₂', co: 'CO', o3: 'O₃', no2: 'NO₂' };
export const BM_Y = { pm25: 15, pm10: 40, so2: 45, no2: 50, o3: 35 };
export const WHO_Y = { pm25: 5, pm10: 15, no2: 10 };
export const BM_24 = { pm25: 55, pm10: 75, so2: 75, no2: 65 };

export const OUT = {
  resp_admissions_under5: 'ISPA balita', resp_admissions_over60: 'ISPA lansia', asthma_emergency_cases: 'Darurat asma',
  copd_admissions: 'PPOK', resp: 'Pernapasan umum', cvd: 'Kardiovaskular', death: 'Kematian',
};
export const OUT_FULL = {
  resp_admissions_under5: 'ISPA balita (<5 th)', resp_admissions_over60: 'ISPA lansia (>60 th)', asthma_emergency_cases: 'Darurat asma',
  copd_admissions: 'PPOK', resp: 'Pernapasan umum (semua umur)', cvd: 'Kardiovaskular', death: 'Kematian',
};
export const SEKTOR = { U: 'Utara', TL: 'Timur Laut', T: 'Timur', TG: 'Tenggara', S: 'Selatan', BD: 'Barat Daya', B: 'Barat', BL: 'Barat Laut' };
export const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'];
export const MIN_DAYS = 10;

export const PAGES = [
  { id: 'ringkasan', n: 0, label: 'Ringkasan', short: 'Ringkasan', icon: 'home', kicker: 'Gambaran besar' },
  { id: 'kondisi', n: 1, label: 'Kualitas Udara', short: 'Kualitas Udara', icon: 'wind', kicker: 'Tujuan 1' },
  { id: 'kritis', n: 2, label: 'Identifikasi Waktu dan Wilayah', short: 'Identifikasi', icon: 'clock', kicker: 'Tujuan 2' },
  { id: 'faktor', n: 3, label: 'Faktor Penyebab', short: 'Penyebab', icon: 'sliders', kicker: 'Tujuan 3' },
  { id: 'kesehatan', n: 4, label: 'Dampak Kesehatan', short: 'Kesehatan', icon: 'heart', kicker: 'Tujuan 4' },
  { id: 'jaringan', n: 5, label: 'Sebaran Stasiun', short: 'Sebaran Stasiun', icon: 'network', kicker: 'Tujuan 5' },
];
