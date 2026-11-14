// Data engine: indexes, date helpers and filter-aware aggregations.
// Every number is computed from public/data/dashboard.json (built from the panitia dataset only).
import { ISL, CATS, OUT, MIN_DAYS } from './constants.js';

export const nf = (v, d = 1) => (v == null || Number.isNaN(v)) ? '–'
  : Number(v).toLocaleString('id-ID', { minimumFractionDigits: d, maximumFractionDigits: d });
export const pct = (v, d = 1, sign = false) => (v == null || Number.isNaN(v)) ? '–' : (sign && v > 0 ? '+' : '') + nf(v, d) + '%';

export function buildEngine(D) {
  const NDAYS = D.meta.ndays;
  const T0 = Date.UTC(2024, 0, 1);
  const DAY_Y = new Int16Array(NDAYS), DAY_M = new Int8Array(NDAYS), DAY_S = [];
  for (let i = 0; i < NDAYS; i++) {
    const d = new Date(T0 + i * 864e5);
    DAY_Y[i] = d.getUTCFullYear(); DAY_M[i] = d.getUTCMonth(); DAY_S.push(d.toISOString().slice(0, 10));
  }
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'];
  const idxOf = iso => Math.round((Date.parse(iso + 'T00:00:00Z') - T0) / 864e5);
  const fmtDay = i => `${new Date(T0 + i * 864e5).getUTCDate()} ${MONTHS[DAY_M[i]]} ${DAY_Y[i]}`;
  const ST = D.stations;
  const SM = Object.fromEntries(ST.map(s => [s.station, s]));
  const HOSP = Object.entries(D.health).map(([h, v]) => ({ id: h, station: v.station, name: (SM[v.station] || {}).nama_rumah_sakit || h }))
    .sort((a, b) => a.id.localeCompare(b.id));
  return { D, NDAYS, T0, DAY_Y, DAY_M, DAY_S, idxOf, fmtDay, ST, SM, HOSP };
}

export const defaultFilters = E => ({
  isl: new Set(ISL), cat: new Set(CATS), st: new Set(), period: 'all', d0: 0, d1: E.NDAYS - 1, season: 'all',
});

const seasonOk = (season, m) => season === 'all' || (season === 'wet' ? (m >= 10 || m <= 3) : season === 'dry' ? (m >= 4 && m <= 9) : (m >= 7 && m <= 9));

export function buildMask(E, F) {
  const M = new Uint8Array(E.NDAYS);
  for (let i = 0; i < E.NDAYS; i++) M[i] = (i >= F.d0 && i <= F.d1 && seasonOk(F.season, E.DAY_M[i])) ? 1 : 0;
  return M;
}

export const inScope = (F, s, incl = false) => F.isl.has(s.island) && F.cat.has(s.site_category)
  && (F.st.size === 0 || F.st.has(s.station)) && (incl || s.used_in_analysis);
export const scope = (E, F, incl = false) => E.ST.filter(s => inScope(F, s, incl));

export function makeAgg(E, mask) {
  const cache = new Map();
  const { D, NDAYS } = E;
  // Station mean = sum of valid hourly values / number of valid hours on the filtered days
  // (identical to the report's hourly-based means). n = days with valid hours.
  function stMean(code, pol) {
    const k = code + '|' + pol;
    if (cache.has(k)) return cache.get(k);
    const d = D.daily[code] || {}, hs = d['hs_' + pol] || [], hn = d['hn_' + pol] || [];
    let s = 0, h = 0, n = 0;
    for (let i = 0; i < NDAYS; i++) if (mask[i] && hn[i] > 0 && hs[i] != null) { s += hs[i]; h += hn[i]; n++; }
    const r = { mean: h ? s / h : null, n, hours: h, ok: n >= MIN_DAYS };
    cache.set(k, r);
    return r;
  }
  function catCounts(code) {
    const k = code + '|cat';
    if (cache.has(k)) return cache.get(k);
    const a = (D.daily[code] || {}).cat || [], c = [0, 0, 0, 0, 0];
    for (let i = 0; i < NDAYS; i++) if (mask[i] && a[i] != null) c[a[i]]++;
    cache.set(k, c);
    return c;
  }
  // per hospital mean cases on haze vs non-haze days (paired station's haze flag) within the mask
  function hazeStats(hospIds) {
    const ck = 'hz|' + hospIds.join(',');
    if (cache.has(ck)) return cache.get(ck);
    const r = hazeCalc(hospIds);
    cache.set(ck, r);
    return r;
  }
  function hazeCalc(hospIds) {
    const keys = Object.keys(OUT), res = Object.fromEntries(keys.map(o => [o, { haze: 0, norm: 0 }]));
    let nH = 0;
    hospIds.forEach(h => {
      const st = D.health[h].station, hz = (D.daily[st] || {}).haze;
      if (!hz) return;
      let ch = 0, cn = 0; const sh = {}, sn = {}; keys.forEach(o => { sh[o] = 0; sn[o] = 0; });
      for (let i = 0; i < NDAYS; i++) {
        if (!mask[i]) continue;
        const isH = hz[i] === 1;
        for (const o of keys) { const v = D.health[h][o][i]; if (v != null) { if (isH) sh[o] += v; else sn[o] += v; } }
        if (isH) ch++; else cn++;
      }
      if (ch && cn) { nH++; keys.forEach(o => { res[o].haze += sh[o] / ch; res[o].norm += sn[o] / cn; }); }
    });
    return { pct: Object.fromEntries(keys.map(o => [o, res[o].norm ? (res[o].haze / res[o].norm - 1) * 100 : null])), n: nH };
  }
  return { stMean, catCounts, hazeStats, mask };
}

export const pmClass = v => v == null ? -1 : v <= 15.5 ? 0 : v <= 55.4 ? 1 : v <= 150.4 ? 2 : v <= 250.4 ? 3 : 4;
