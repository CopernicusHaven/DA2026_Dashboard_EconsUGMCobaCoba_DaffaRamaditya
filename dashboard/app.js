/* DA2026 Dashboard — Gelar Rasa 2026. All numbers come from data/data.js (built from the panitia dataset only). */
(() => {
  'use strict';
  const D = window.DATA;
  const NDAYS = D.meta.ndays;
  const FONT = '"Plus Jakarta Sans", system-ui, -apple-system, "Segoe UI", sans-serif';

  // ---------------- constants & palette ----------------
  const ISL = ['Sumatera', 'Jawa', 'Kalimantan', 'Sulawesi', 'Papua'];
  const CATS = ['Perkotaan', 'Tepi Jalan (Lalu Lintas)', 'Industri', 'Gambut / Karhutla', 'Latar Bersih'];
  const CAT_S = { 'Perkotaan': 'Perkotaan', 'Tepi Jalan (Lalu Lintas)': 'Tepi jalan', 'Industri': 'Industri', 'Gambut / Karhutla': 'Gambut / karhutla', 'Latar Bersih': 'Latar bersih' };
  const SERIES = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6', '#e34948'];
  const C_ISL = Object.fromEntries(ISL.map((k, i) => [k, SERIES[i]]));
  const C_CAT = Object.fromEntries(CATS.map((k, i) => [k, SERIES[i]]));
  const ISPU_C = ['#2a78d6', '#d3d1c9', '#f0a3a0', '#e34948', '#9e2323'];
  const ISPU_L = ['Baik', 'Sedang', 'Tidak Sehat', 'Sangat Tidak Sehat', 'Berbahaya'];
  const SEQ = ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#2a78d6', '#1c5cab', '#104281', '#0d366b'];
  const DIV = ['#2a78d6', '#86b6ef', '#f0efec', '#ec8a8a', '#e34948'];
  const INK = '#0b0b0b', INK2 = '#52514e', MUTED = '#898781', GRID = '#e1e0d9', AXIS = '#c3c2b7', CRIT = '#d03b3b', NAVY = '#1b2550';
  const POL = { pm25: 'PM2.5', pm10: 'PM10', so2: 'SO₂', co: 'CO', o3: 'O₃', no2: 'NO₂' };
  const BM_Y = { pm25: 15, pm10: 40, so2: 45, no2: 50, o3: 35 };
  const WHO_Y = { pm25: 5, pm10: 15, no2: 10 };
  const BM_24 = { pm25: 55, pm10: 75, so2: 75, no2: 65 };
  const OUT = {
    resp_admissions_under5: 'ISPA balita', resp_admissions_over60: 'ISPA lansia', asthma_emergency_cases: 'Darurat asma',
    copd_admissions: 'PPOK', resp: 'Pernapasan umum', cvd: 'Kardiovaskular', death: 'Kematian'
  };
  const OUT_FULL = {
    resp_admissions_under5: 'ISPA balita (<5 th)', resp_admissions_over60: 'ISPA lansia (>60 th)', asthma_emergency_cases: 'Darurat asma',
    copd_admissions: 'PPOK', resp: 'Pernapasan umum (semua umur)', cvd: 'Kardiovaskular', death: 'Kematian'
  };
  const C_OUT = { resp_admissions_under5: '#eb6834', resp_admissions_over60: '#2a78d6', asthma_emergency_cases: '#1baf7a', copd_admissions: '#eda100', resp: '#6250d6', cvd: '#e87ba4', death: '#e34948' };
  const REL_C = { 'Baik': '#2a78d6', 'Perlu standardisasi': '#eda100', 'Buruk - perlu kalibrasi/perawatan': '#eb6834', 'Kritis - ganti/perbaiki': CRIT };
  const SEKTOR = { U: 'Utara', TL: 'Timur Laut', T: 'Timur', TG: 'Tenggara', S: 'Selatan', BD: 'Barat Daya', B: 'Barat', BL: 'Barat Laut' };
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'];
  const MIN_DAYS = 10;

  // ---------------- dates ----------------
  const T0 = Date.UTC(2024, 0, 1);
  const DAY_Y = new Int16Array(NDAYS), DAY_M = new Int8Array(NDAYS), DAY_S = [];
  for (let i = 0; i < NDAYS; i++) { const d = new Date(T0 + i * 864e5); DAY_Y[i] = d.getUTCFullYear(); DAY_M[i] = d.getUTCMonth(); DAY_S.push(d.toISOString().slice(0, 10)); }
  const idxOf = iso => Math.round((Date.parse(iso + 'T00:00:00Z') - T0) / 864e5);
  const fmtDay = i => `${new Date(T0 + i * 864e5).getUTCDate()} ${MONTHS[DAY_M[i]]} ${DAY_Y[i]}`;

  // ---------------- formatting ----------------
  const nf = (v, d = 1) => (v == null || Number.isNaN(v)) ? '–' : Number(v).toLocaleString('id-ID', { minimumFractionDigits: d, maximumFractionDigits: d });
  const pct = (v, d = 1, sign = false) => (v == null || Number.isNaN(v)) ? '–' : (sign && v > 0 ? '+' : '') + nf(v, d) + '%';
  const el = (tag, attrs = {}, ...kids) => {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === 'class') n.className = v; else if (k === 'style') n.style.cssText = v;
      else if (k.startsWith('on')) n.addEventListener(k.slice(2), v); else n.setAttribute(k, v);
    }
    for (const k of kids.flat()) if (k != null) n.append(k.nodeType ? k : document.createTextNode(String(k)));
    return n;
  };
  const $ = id => document.getElementById(id);

  // ---------------- data indexes ----------------
  const ST = D.stations;
  const SM = Object.fromEntries(ST.map(s => [s.station, s]));
  const HOSP = Object.entries(D.health).map(([h, v]) => ({ id: h, station: v.station, name: (SM[v.station] || {}).nama_rumah_sakit || h }))
    .sort((a, b) => a.id.localeCompare(b.id));

  // ---------------- filter state ----------------
  const F = {
    isl: new Set(ISL), cat: new Set(CATS), st: new Set(), period: 'all', d0: 0, d1: NDAYS - 1, season: 'all',
    pol: 'pm25', diur: 'pm25', week: 'no2', heat: 'pm25', traf: 'pm25', year: 2025, out: 'resp_admissions_under5', hosp: 'RS-XXX-04'
  };
  let MASK = new Uint8Array(NDAYS).fill(1);
  let cache = new Map();
  const seasonOk = m => F.season === 'all' || (F.season === 'wet' ? (m >= 10 || m <= 3) : F.season === 'dry' ? (m >= 4 && m <= 9) : (m >= 7 && m <= 9));
  function rebuildMask() {
    for (let i = 0; i < NDAYS; i++) MASK[i] = (i >= F.d0 && i <= F.d1 && seasonOk(DAY_M[i])) ? 1 : 0;
    cache = new Map();
  }
  const inScope = (s, incl = false) => F.isl.has(s.island) && F.cat.has(s.site_category) && (F.st.size === 0 || F.st.has(s.station)) && (incl || s.used_in_analysis);
  const scope = (incl = false) => ST.filter(s => inScope(s, incl));
  // Station mean = sum of valid hourly values / number of valid hours on the filtered days
  // (identical to the report's hourly-based means). n = number of days that contain valid hours.
  function stMean(code, pol) {
    const k = code + '|' + pol;
    if (cache.has(k)) return cache.get(k);
    const d = D.daily[code] || {}, hs = d['hs_' + pol] || [], hn = d['hn_' + pol] || [];
    let s = 0, h = 0, n = 0;
    for (let i = 0; i < NDAYS; i++) if (MASK[i] && hn[i] > 0 && hs[i] != null) { s += hs[i]; h += hn[i]; n++; }
    const r = { mean: h ? s / h : null, n, hours: h };
    cache.set(k, r);
    return r;
  }

  // ---------------- charts ----------------
  const charts = {};
  const getChart = id => charts[id] || (charts[id] = echarts.init($(id), null, { renderer: 'canvas' }));
  const AX = { axisLine: { lineStyle: { color: AXIS } }, axisTick: { show: false }, axisLabel: { color: INK2, fontSize: 11 }, splitLine: { lineStyle: { color: GRID } }, nameTextStyle: { color: INK2, fontSize: 11 } };
  const ax = (o = {}) => Object.assign({}, JSON.parse(JSON.stringify(AX)), o);
  function setOpt(id, o) {
    const c = getChart(id);
    const base = {
      textStyle: { fontFamily: FONT, color: INK2 }, animationDuration: 350,
      toolbox: { right: 4, top: 0, itemSize: 13, iconStyle: { borderColor: MUTED },
        feature: { dataView: { readOnly: true, title: 'Lihat tabel', lang: ['Data', 'Tutup', 'Muat ulang'] }, saveAsImage: { title: 'Unduh PNG', pixelRatio: 2, backgroundColor: '#ffffff' } } },
      tooltip: { confine: true, backgroundColor: '#fff', borderColor: 'rgba(11,11,11,.1)', textStyle: { color: INK, fontSize: 12, fontFamily: FONT }, extraCssText: 'box-shadow:0 6px 20px rgba(16,24,40,.12);border-radius:8px;' }
    };
    const merged = Object.assign({}, base, o, { tooltip: Object.assign({}, base.tooltip, o.tooltip || {}) });
    // keep the legend row and the y-axis unit label from overlapping
    const grids = Array.isArray(merged.grid) ? merged.grid : (merged.grid ? [merged.grid] : []);
    const yNamed = [].concat(merged.yAxis || []).some(y => y && y.name);
    if (grids[0] && typeof grids[0].top === 'number') grids[0].top = Math.max(grids[0].top, merged.legend ? (yNamed ? 62 : 40) : (yNamed ? 36 : grids[0].top));
    if (o.toolbox === false) delete merged.toolbox;
    c.setOption(merged, true);
    c.resize();
    return c;
  }
  function empty(id, msg) {
    const c = getChart(id);
    c.setOption({ title: { text: msg, left: 'center', top: 'middle', textStyle: { color: MUTED, fontSize: 13, fontWeight: 400, fontFamily: FONT } }, xAxis: [], yAxis: [], series: [] }, true);
  }
  const tipRow = (color, label, value) => `<div style="display:flex;gap:8px;align-items:center;justify-content:space-between;min-width:170px"><span style="display:flex;gap:6px;align-items:center;color:${INK2}"><i style="width:12px;height:0;border-top:2px solid ${color};display:inline-block"></i>${label}</span><b>${value}</b></div>`;

  // ---------------- tables ----------------
  function table(containerId, cols, rows, opts = {}) {
    const wrap = $(containerId); wrap.innerHTML = '';
    if (!rows.length) { wrap.append(el('div', { class: 'empty' }, 'Tidak ada data pada filter ini.')); return; }
    let sortKey = opts.sortKey || null, dir = opts.dir || -1;
    const t = el('table', { class: 't' });
    const thead = el('thead'), tbody = el('tbody');
    const tr = el('tr');
    cols.forEach(c => {
      const th = el('th', { scope: 'col', tabindex: '0' }, c.label);
      th.addEventListener('click', () => { dir = sortKey === c.key ? -dir : (c.num ? -1 : 1); sortKey = c.key; draw(); });
      th.addEventListener('keydown', e => { if (e.key === 'Enter') th.click(); });
      tr.append(th);
    });
    thead.append(tr); t.append(thead, tbody);
    function draw() {
      const rs = [...rows];
      if (sortKey) rs.sort((a, b) => { const x = a[sortKey], y = b[sortKey]; if (x == null) return 1; if (y == null) return -1; return (x > y ? 1 : x < y ? -1 : 0) * dir; });
      tbody.innerHTML = '';
      [...thead.querySelectorAll('th')].forEach((th, i) => th.setAttribute('aria-sort', cols[i].key === sortKey ? (dir > 0 ? 'ascending' : 'descending') : 'none'));
      rs.forEach(r => {
        const row = el('tr');
        cols.forEach(c => {
          const td = el('td', { class: c.num ? 'num' : '' });
          const v = c.render ? c.render(r) : r[c.key];
          if (v != null && v.nodeType) td.append(v); else td.textContent = v == null ? '–' : v;
          row.append(td);
        });
        tbody.append(row);
      });
    }
    draw();
    wrap.append(t);
  }
  const tag = (txt, kind) => el('span', { class: 'tag ' + kind }, txt);

  // ---------------- segmented controls ----------------
  function seg(id, items, key, onChange) {
    const box = $(id); box.innerHTML = '';
    items.forEach(([v, label]) => {
      const b = el('button', { 'aria-pressed': String(F[key] === v), type: 'button' }, label);
      b.addEventListener('click', () => { F[key] = v; [...box.children].forEach(x => x.setAttribute('aria-pressed', String(x === b))); onChange(); });
      box.append(b);
    });
  }

  // =========================================================================================
  // FILTER UI
  // =========================================================================================
  function chips(id, values, set, colors, short) {
    const box = $(id); box.innerHTML = '';
    values.forEach(v => {
      const b = el('button', { class: 'chip', type: 'button', 'aria-pressed': String(set.has(v)), title: 'Tampilkan/sembunyikan ' + v },
        el('span', { class: 'dot', style: `background:${colors[v]}` }), short ? short[v] : v);
      b.addEventListener('click', () => {
        if (set.has(v)) set.delete(v); else set.add(v);
        if (set.size === 0) values.forEach(x => set.add(x));
        chips(id, values, set, colors, short); onFilter();
      });
      box.append(b);
    });
  }
  function buildStationList() {
    const list = $('dd-list'), q = $('dd-search').value.trim().toLowerCase();
    list.innerHTML = '';
    ISL.forEach(isl => {
      const items = ST.filter(s => s.island === isl && s.used_in_analysis && F.isl.has(isl) && F.cat.has(s.site_category))
        .filter(s => !q || (s.station + ' ' + s.kota_kabupaten + ' ' + s.provinsi).toLowerCase().includes(q));
      if (!items.length) return;
      list.append(el('div', { class: 'grp' }, isl));
      items.forEach(s => {
        const cb = el('input', { type: 'checkbox' });
        cb.checked = F.st.has(s.station);
        cb.addEventListener('change', () => { if (cb.checked) F.st.add(s.station); else F.st.delete(s.station); onFilter(); });
        list.append(el('label', {}, cb, s.station, el('small', {}, s.kota_kabupaten.replace('Kabupaten ', 'Kab. ').replace('Kota Administrasi ', ''))));
      });
    });
  }
  function setPeriod(p) {
    F.period = p;
    const show = p === 'custom';
    $('f-d0').hidden = !show; $('f-d1').hidden = !show;
    if (p === 'all') { F.d0 = 0; F.d1 = NDAYS - 1; }
    else if (p === 'last12') { F.d0 = idxOf('2025-10-15'); F.d1 = NDAYS - 1; }
    else if (p !== 'custom') { F.d0 = Math.max(0, idxOf(p + '-01-01')); F.d1 = Math.min(NDAYS - 1, idxOf(p + '-12-31')); }
    $('f-d0').value = DAY_S[F.d0]; $('f-d1').value = DAY_S[F.d1];
  }
  function summary() {
    const box = $('f-summary'); box.innerHTML = '';
    const n = scope().length;
    box.append(el('span', { class: 'pill' }, `${n} stasiun dianalisis`));
    box.append(el('span', {}, `${fmtDay(F.d0)} – ${fmtDay(F.d1)}`));
    if (F.season !== 'all') box.append(el('span', { class: 'pill' }, $('f-season').selectedOptions[0].textContent));
    [...F.st].forEach(s => {
      const x = el('button', { type: 'button', 'aria-label': 'Hapus ' + s }, '×');
      x.addEventListener('click', () => { F.st.delete(s); onFilter(); });
      box.append(el('span', { class: 'pill' }, s, x));
    });
    $('dd-btn').textContent = F.st.size ? `${F.st.size} stasiun dipilih ▾` : 'Semua stasiun ▾';
  }
  function focusStation(code) {
    F.st = new Set([code]);
    const h = HOSP.find(x => x.station === code); if (h) F.hosp = h.id;
    onFilter();
    $('toast-msg').textContent = `Difokuskan ke ${code} — semua halaman kini menampilkan stasiun ini.`;
    $('toast').hidden = false; clearTimeout(focusStation.t); focusStation.t = setTimeout(() => { $('toast').hidden = true; }, 6000);
  }
  function resetAll() {
    F.isl = new Set(ISL); F.cat = new Set(CATS); F.st = new Set(); F.season = 'all'; $('f-season').value = 'all';
    $('f-period').value = 'all'; setPeriod('all');
    chips('f-island', ISL, F.isl, C_ISL); chips('f-cat', CATS, F.cat, C_CAT, CAT_S);
    $('toast').hidden = true; onFilter();
  }
  function onFilter() {
    rebuildMask(); summary(); buildStationList();
    Object.keys(dirty).forEach(k => { dirty[k] = true; });
    renderPage(current);
  }

  // =========================================================================================
  // PAGE: RINGKASAN
  // =========================================================================================
  let mapHome, homeLayer, mapNet, netLayer;
  function pmClass(v) { return v == null ? -1 : v <= 15.5 ? 0 : v <= 55.4 ? 1 : v <= 150.4 ? 2 : v <= 250.4 ? 3 : 4; }
  // Basemap = visual background only (not analysis data). Esri light gray canvas needs no API key;
  // if it fails to load, fall back to OpenStreetMap standard tiles shown in muted grayscale.
  function tiles(map) {
    let errors = 0, switched = false;
    const esri = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
      attribution: 'Peta dasar © Esri, © OpenStreetMap contributors', maxZoom: 12
    });
    esri.on('tileerror', () => {
      if (switched || ++errors < 4) return;
      switched = true; map.removeLayer(esri);
      L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OpenStreetMap contributors', maxZoom: 12, className: 'osm-muted' }).addTo(map);
    });
    esri.addTo(map);
  }
  function hazeStats(hospIds) {
    // per hospital mean cases on haze vs non-haze days (paired station's haze flag), within the date/season mask
    const res = {}; Object.keys(OUT).forEach(o => { res[o] = { haze: 0, norm: 0 }; });
    let nH = 0;
    hospIds.forEach(h => {
      const st = D.health[h].station, hz = (D.daily[st] || {}).haze;
      if (!hz) return;
      let ch = 0, cn = 0; const sh = {}, sn = {}; Object.keys(OUT).forEach(o => { sh[o] = 0; sn[o] = 0; });
      for (let i = 0; i < NDAYS; i++) {
        if (!MASK[i]) continue;
        const isH = hz[i] === 1;
        Object.keys(OUT).forEach(o => { const v = D.health[h][o][i]; if (v != null) { if (isH) sh[o] += v; else sn[o] += v; } });
        if (isH) ch++; else cn++;
      }
      if (ch && cn) { nH++; Object.keys(OUT).forEach(o => { res[o].haze += sh[o] / ch; res[o].norm += sn[o] / cn; }); }
    });
    const out = {}; Object.keys(OUT).forEach(o => { out[o] = res[o].norm ? (res[o].haze / res[o].norm - 1) * 100 : null; });
    return { pct: out, n: nH };
  }
  const hospInScope = () => HOSP.filter(h => { const s = SM[h.station]; return s && inScope(s, true); });

  function renderRingkasan() {
    const sts = scope();
    const means = sts.map(s => ({ s, m: stMean(s.station, 'pm25') })).filter(x => x.m.n >= MIN_DAYS);
    const avg = means.length ? means.reduce((a, x) => a + x.m.mean, 0) / means.length : null;
    let cnt = [0, 0, 0, 0, 0], haze = 0, peak = { v: -1 };
    sts.forEach(s => {
      const d = D.daily[s.station];
      for (let i = 0; i < NDAYS; i++) {
        if (!MASK[i]) continue;
        if (d.cat[i] != null) cnt[d.cat[i]]++;
        haze += d.haze[i];
        if (d.pm25[i] != null && d.pm25[i] > peak.v) peak = { v: d.pm25[i], s: s.station, i };
      }
    });
    const tot = cnt.reduce((a, b) => a + b, 0);
    const unhealthy = tot ? (cnt[2] + cnt[3] + cnt[4]) / tot * 100 : null;
    const ok = means.filter(x => x.m.mean <= 15).length;
    const hosp = hospInScope().map(h => h.id);
    let u5 = 0; hosp.forEach(h => { const a = D.health[h].resp_admissions_under5; for (let i = 0; i < NDAYS; i++) if (MASK[i] && a[i] != null) u5 += a[i]; });
    const hz = hazeStats(hosp);
    const eps = D.episodes.filter(e => sts.some(s => s.station === e.station) && idxOf(e.end) >= F.d0 && idxOf(e.start) <= F.d1);
    const K = [
      { k: 'Rata-rata PM2.5', v: nf(avg, 1), u: 'µg/m³', d: avg ? `${nf(avg / 15, 1)}× baku mutu tahunan (15) · WHO 5` : '', alert: avg > 15 },
      { k: 'Hari ISPU Tidak Sehat+', v: pct(unhealthy, 1), u: '', d: `${nf(cnt[3] + cnt[4], 0)} hari-stasiun Sangat Tidak Sehat/Berbahaya`, alert: unhealthy > 10 },
      { k: 'Hari-stasiun kabut asap', v: nf(haze, 0), u: '', d: `${eps.length} episode dalam filter` },
      { k: 'Stasiun ≤ baku mutu PM2.5', v: `${ok}`, u: `dari ${means.length}`, d: 'rata-rata periode terpilih ≤ 15 µg/m³' },
      { k: 'Kasus ISPA balita', v: nf(u5, 0), u: '', d: hz.pct.resp_admissions_under5 != null ? `${pct(hz.pct.resp_admissions_under5, 0, true)} saat kabut asap` : `${hosp.length} RS dalam filter` },
      { k: 'PM2.5 harian tertinggi', v: peak.v >= 0 ? nf(peak.v, 0) : '–', u: 'µg/m³', d: peak.v >= 0 ? `${peak.s} · ${fmtDay(peak.i)}` : '', alert: peak.v > 250.4 }
    ];
    const box = $('kpis'); box.innerHTML = '';
    K.forEach(x => box.append(el('div', { class: 'kpi' + (x.alert ? ' alert' : '') }, el('div', { class: 'k' }, x.k),
      el('div', { class: 'v' }, x.v, x.u ? el('small', {}, x.u) : null), el('div', { class: 'd' }, x.d))));

    // map
    if (!mapHome) {
      mapHome = L.map('map-home', { scrollWheelZoom: false, zoomSnap: 0.25 }).fitBounds(ST.map(s => [s.latitude_dd, s.longitude_dd]), { padding: [24, 24] });
      tiles(mapHome); homeLayer = L.layerGroup().addTo(mapHome);
      const lg = $('legend-home');
      ISPU_L.forEach((l, i) => lg.append(el('span', {}, el('i', { style: `background:${ISPU_C[i]};border:1px solid #52514e` }), l)));
    }
    mapHome.invalidateSize();
    homeLayer.clearLayers();
    ST.filter(s => inScope(s)).forEach(s => {
      const m = stMean(s.station, 'pm25');
      const v = m.n >= MIN_DAYS ? m.mean : null, c = pmClass(v);
      const mk = L.circleMarker([s.latitude_dd, s.longitude_dd], {
        radius: v == null ? 5 : 5 + Math.sqrt(v) * 1.6, color: '#52514e', weight: 1, fillColor: c < 0 ? '#ffffff' : ISPU_C[c], fillOpacity: .9
      }).addTo(homeLayer);
      mk.bindTooltip(`${s.station} · ${v == null ? 'data terbatas' : nf(v, 1) + ' µg/m³'}`);
      const pop = el('div', {}, el('b', {}, `${s.station} — ${s.kota_kabupaten}`), el('br'), `${s.provinsi} · ${CAT_S[s.site_category]}`, el('br'),
        `PM2.5 rata-rata: ${v == null ? 'data terbatas' : nf(v, 1) + ' µg/m³'} (${m.n} hari valid)`, el('br'),
        `Status alat: ${s.status_operasional} · kelengkapan ${nf(s.completeness_pm25_pct, 1)}%`, el('br'), `RS pasangan: ${s.nama_rumah_sakit}`,
        el('div', { class: 'pop-btn' }, el('button', { class: 'btn primary', type: 'button', onclick: () => focusStation(s.station) }, 'Fokus ke stasiun ini')));
      mk.bindPopup(pop);
    });

    // island chart
    const isl = ISL.filter(i => F.isl.has(i)).map(i => {
      const xs = means.filter(x => x.s.island === i);
      return { i, v: xs.length ? xs.reduce((a, x) => a + x.m.mean, 0) / xs.length : null, n: xs.length };
    }).filter(x => x.v != null).sort((a, b) => a.v - b.v);
    $('sub-island').textContent = isl.length ? `Tertinggi: ${isl[isl.length - 1].i} (${nf(isl[isl.length - 1].v)} µg/m³); terendah: ${isl[0].i} (${nf(isl[0].v)}).` : '';
    if (!isl.length) empty('ch-island', 'Tidak ada data pada filter ini'); else setOpt('ch-island', {
      grid: { left: 90, right: 60, top: 26, bottom: 24 },
      tooltip: { trigger: 'item', formatter: p => `${tipRow(C_ISL[p.name], p.name, nf(p.value, 1) + ' µg/m³')}<div style="color:${MUTED};font-size:11px;margin-top:4px">rata-rata ${isl.find(x => x.i === p.name).n} stasiun</div>` },
      xAxis: ax({ type: 'value', name: 'µg/m³' }), yAxis: ax({ type: 'category', data: isl.map(x => x.i), axisLine: { show: false } }),
      series: [{ type: 'bar', barWidth: '58%', data: isl.map(x => ({ value: +x.v.toFixed(1), itemStyle: { color: C_ISL[x.i], borderRadius: [0, 4, 4, 0] } })),
        label: { show: true, position: 'right', color: INK2, formatter: p => nf(p.value, 1) },
        markLine: { symbol: 'none', silent: true, lineStyle: { color: INK2, type: 'dashed' }, label: { formatter: 'Baku mutu tahunan 15', color: INK2, fontSize: 10, position: 'insideEndTop' }, data: [{ xAxis: 15 }] } }]
    });

    // ISPU composition per island
    const rows = ISL.filter(i => F.isl.has(i)).map(i => {
      const c = [0, 0, 0, 0, 0]; sts.filter(s => s.island === i).forEach(s => { const a = D.daily[s.station].cat; for (let k = 0; k < NDAYS; k++) if (MASK[k] && a[k] != null) c[a[k]]++; });
      const t = c.reduce((a, b) => a + b, 0); return { i, c: c.map(x => t ? x / t * 100 : 0), t };
    }).filter(r => r.t);
    rows.unshift({ i: 'Semua', c: cnt.map(x => tot ? x / tot * 100 : 0), t: tot });
    $('sub-ispu-all').textContent = tot ? `${pct(unhealthy, 1)} hari-stasiun berkategori Tidak Sehat atau lebih buruk (${nf(tot, 0)} hari-stasiun).` : '';
    if (!tot) empty('ch-ispu-all', 'Tidak ada data pada filter ini'); else setOpt('ch-ispu-all', {
      grid: { left: 90, right: 20, top: 34, bottom: 24 }, legend: { top: 0, left: 0, itemWidth: 12, itemHeight: 10, textStyle: { color: INK2, fontSize: 11 } },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: ps => `<b>${ps[0].name}</b>` + ps.map(p => tipRow(p.color, p.seriesName, pct(p.value, 1))).join('') },
      xAxis: ax({ type: 'value', max: 100, axisLabel: { formatter: '{value}%', color: INK2, fontSize: 11 } }),
      yAxis: ax({ type: 'category', data: rows.map(r => r.i).reverse(), axisLine: { show: false } }),
      series: ISPU_L.map((l, k) => ({ name: l, type: 'bar', stack: 'a', barWidth: '60%', itemStyle: { color: ISPU_C[k], borderColor: '#fff', borderWidth: 1 }, data: rows.map(r => +r.c[k].toFixed(2)).reverse() }))
    });
  }

  // =========================================================================================
  // PAGE: KONDISI
  // =========================================================================================
  function renderKondisi() {
    const pol = F.pol;
    seg('seg-pol', Object.entries(POL), 'pol', () => renderKondisi());
    const sts = scope();
    const arr = sts.map(s => ({ s, m: stMean(s.station, pol) })).filter(x => x.m.n >= MIN_DAYS).sort((a, b) => a.m.mean - b.m.mean);
    const dropped = sts.filter(s => stMean(s.station, pol).n < MIN_DAYS).map(s => s.station);
    const bm = BM_Y[pol], who = WHO_Y[pol];
    if (!arr.length) { empty('ch-rank', 'Tidak ada data pada filter ini'); $('sub-rank').textContent = ''; }
    else {
      const top = arr[arr.length - 1];
      const over = bm ? arr.filter(x => x.m.mean > bm).length : null;
      $('sub-rank').textContent = `Rata-rata ${POL[pol]} periode terpilih. Tertinggi: ${top.s.station} (${nf(top.m.mean, 1)} µg/m³)` +
        (bm ? ` · ${over} dari ${arr.length} stasiun di atas baku mutu tahunan (${bm}).` : '.') + (dropped.length ? ` Tidak tampil (hari valid <${MIN_DAYS}): ${dropped.join(', ')}.` : '');
      const ml = [];
      if (bm) ml.push({ xAxis: bm, lineStyle: { type: 'dashed', color: INK2 }, label: { formatter: `Baku mutu ${bm}`, color: INK2, fontSize: 10, position: 'insideEndTop' } });
      if (who) ml.push({ xAxis: who, lineStyle: { type: 'dotted', color: MUTED }, label: { formatter: `WHO ${who}`, color: MUTED, fontSize: 10, position: 'insideStartTop' } });
      setOpt('ch-rank', {
        grid: { left: 70, right: 56, top: 30, bottom: 30 },
        legend: { top: 0, left: 0, data: ISL.filter(i => F.isl.has(i)), itemWidth: 12, itemHeight: 10, textStyle: { fontSize: 11, color: INK2 } },
        tooltip: { trigger: 'item', formatter: p => { const s = SM[p.name.replace(' *', '')]; const m = stMean(s.station, pol); return `<b>${s.station}</b> · ${s.kota_kabupaten}<br>${tipRow(C_ISL[s.island], POL[pol], nf(m.mean, 1) + ' µg/m³')}<div style="color:${MUTED};font-size:11px;margin-top:4px">${m.n} hari valid · ${CAT_S[s.site_category]} · kelengkapan ${nf(s.completeness_pm25_pct, 0)}%</div>`; } },
        xAxis: ax({ type: 'value', name: 'µg/m³' }),
        yAxis: ax({ type: 'category', data: arr.map(x => x.s.station + (x.s.completeness_pm25_pct < 75 ? ' *' : '')), axisLine: { show: false } }),
        series: [
          ...ISL.filter(i => F.isl.has(i)).map(i => ({ name: i, type: 'bar', stack: 's', itemStyle: { color: C_ISL[i] }, data: [] })),
          { name: POL[pol], type: 'bar', barWidth: '64%', data: arr.map(x => ({ value: +x.m.mean.toFixed(2), itemStyle: { color: C_ISL[x.s.island], borderRadius: [0, 4, 4, 0], opacity: x.s.completeness_pm25_pct < 75 ? .55 : 1 } })),
            label: { show: true, position: 'right', fontSize: 10.5, color: INK2, formatter: p => nf(p.value, pol === 'co' ? 0 : 1) },
            markLine: ml.length ? { symbol: 'none', silent: true, data: ml } : undefined }
        ]
      }).off('click');
      getChart('ch-rank').on('click', p => { if (p.seriesName === POL[pol]) focusStation(p.name.replace(' *', '')); });
    }

    // ISPU per station
    const ip = sts.map(s => { const a = D.daily[s.station].cat, c = [0, 0, 0, 0, 0]; let t = 0; for (let i = 0; i < NDAYS; i++) if (MASK[i] && a[i] != null) { c[a[i]]++; t++; } return { s, c: c.map(x => t ? x / t * 100 : 0), t }; })
      .filter(x => x.t >= MIN_DAYS).sort((a, b) => (b.c[0] - a.c[0]) || (b.c[1] - a.c[1]));
    if (!ip.length) empty('ch-ispu-st', 'Tidak ada data pada filter ini'); else setOpt('ch-ispu-st', {
      grid: { left: 62, right: 14, top: 48, bottom: 30 }, legend: { top: 0, left: 0, itemWidth: 12, itemHeight: 10, textStyle: { fontSize: 11, color: INK2 } },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: ps => `<b>${ps[0].name}</b>` + ps.map(p => tipRow(p.color, p.seriesName, pct(p.value, 1))).join('') },
      xAxis: ax({ type: 'value', max: 100, axisLabel: { formatter: '{value}%', color: INK2, fontSize: 11 } }),
      yAxis: ax({ type: 'category', inverse: true, data: ip.map(x => x.s.station), axisLine: { show: false } }),
      series: ISPU_L.map((l, k) => ({ name: l, type: 'bar', stack: 'a', barWidth: '66%', itemStyle: { color: ISPU_C[k], borderColor: '#fff', borderWidth: 1 }, data: ip.map(x => +x.c[k].toFixed(2)) }))
    });

    // monthly trend
    const months = []; const mIdx = {};
    for (let i = 0; i < NDAYS; i++) if (MASK[i]) { const k = `${DAY_Y[i]}-${String(DAY_M[i] + 1).padStart(2, '0')}`; if (!(k in mIdx)) { mIdx[k] = months.length; months.push(k); } }
    const perStation = F.st.size >= 1 && F.st.size <= 6;
    const groups = perStation ? sts.map((s, k) => ({ name: s.station, color: SERIES[k % 8], members: [s] }))
      : ISL.filter(i => F.isl.has(i)).map(i => ({ name: i, color: C_ISL[i], members: sts.filter(s => s.island === i) })).filter(g => g.members.length);
    const series = groups.map(g => {
      const sum = new Float64Array(months.length), n = new Int32Array(months.length);
      g.members.forEach(s => { const a = D.daily[s.station][pol]; for (let i = 0; i < NDAYS; i++) if (MASK[i] && a[i] != null) { const k = mIdx[`${DAY_Y[i]}-${String(DAY_M[i] + 1).padStart(2, '0')}`]; sum[k] += a[i]; n[k]++; } });
      return { name: g.name, type: 'line', smooth: false, symbol: 'circle', symbolSize: 5, showSymbol: months.length < 40, lineStyle: { width: 2, color: g.color }, itemStyle: { color: g.color },
        data: Array.from(sum, (v, k) => n[k] ? +(v / n[k]).toFixed(1) : null), connectNulls: false };
    });
    const peakTxt = (() => { let best = null; series.forEach(s => s.data.forEach((v, k) => { if (v != null && (!best || v > best.v)) best = { v, n: s.name, m: months[k] }; })); return best ? `Puncak bulanan: ${best.n}, ${MONTHS[+best.m.slice(5) - 1]} ${best.m.slice(0, 4)} (${nf(best.v, 1)} µg/m³).` : ''; })();
    $('sub-trend').textContent = `${POL[pol]} rata-rata bulanan ${perStation ? 'per stasiun terpilih' : 'per pulau'}. ${peakTxt}`;
    if (!months.length || !series.length) empty('ch-trend', 'Tidak ada data pada filter ini'); else setOpt('ch-trend', {
      grid: { left: 54, right: 24, top: 34, bottom: 64 }, legend: { top: 0, left: 0, itemWidth: 18, itemHeight: 3, textStyle: { fontSize: 11, color: INK2 } },
      tooltip: { trigger: 'axis', formatter: ps => { const m = ps[0].axisValue; return `<b>${MONTHS[+m.slice(5) - 1]} ${m.slice(0, 4)}</b>` + ps.filter(p => p.value != null).sort((a, b) => b.value - a.value).map(p => tipRow(p.color, p.seriesName, nf(p.value, 1) + ' µg/m³')).join(''); } },
      xAxis: ax({ type: 'category', data: months, boundaryGap: false, axisLabel: { color: INK2, fontSize: 11, formatter: m => `${MONTHS[+m.slice(5) - 1]}\n${m.slice(0, 4)}` } }),
      yAxis: ax({ type: 'value', name: 'µg/m³' }),
      dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18, bottom: 8, borderColor: GRID, fillerColor: 'rgba(42,120,214,.12)' }],
      series: series.map((s, k) => k === 0 && BM_24[pol] ? Object.assign(s, { markLine: { symbol: 'none', silent: true, lineStyle: { type: 'dashed', color: INK2 }, label: { formatter: `Baku mutu 24 jam ${BM_24[pol]}`, color: INK2, fontSize: 10, position: 'insideEndTop' }, data: [{ yAxis: BM_24[pol] }] } }) : s)
    });

    // annual compliance + IKU
    seg('seg-year', [[2024, '2024'], [2025, '2025'], [2026, '2026 (s.d. 14 Okt)']], 'year', () => renderKondisi());
    const codes = new Set(sts.map(s => s.station));
    const ann = D.annual.filter(r => r.year === F.year && codes.has(r.station));
    const pv = (k, lim) => r => { const v = r[k + '_tahunan']; const sp = el('span', {}, nf(v, 1) + ' '); if (r['lolos_bm_' + k] === false) sp.append(tag('lewat', 'bad')); return sp; };
    const ikuKind = c => c === 'Sangat Baik' || c === 'Baik' ? 'ok' : c === 'Sedang' ? 'warn' : 'bad';
    table('tb-annual', [
      { key: 'station', label: 'Stasiun' }, { key: 'island', label: 'Pulau' },
      { key: 'kelengkapan_pct', label: 'Kelengkapan', num: true, render: r => { const sp = el('span', {}, nf(r.kelengkapan_pct, 0) + '% '); if (r.kelengkapan_pct < 75) sp.append(tag('<75%', 'warn')); return sp; } },
      { key: 'pm25_tahunan', label: 'PM2.5 (15)', num: true, render: pv('pm25') }, { key: 'pm10_tahunan', label: 'PM10 (40)', num: true, render: pv('pm10') },
      { key: 'no2_tahunan', label: 'NO₂ (50)', num: true, render: pv('no2') }, { key: 'o3_tahunan', label: 'O₃ (35)', num: true, render: pv('o3') },
      { key: 'so2_tahunan', label: 'SO₂ (45)', num: true, render: pv('so2') },
      { key: 'IKU', label: 'IKU', num: true, render: r => nf(r.IKU, 1) }, { key: 'IKU_kategori', label: 'Kategori IKU', render: r => tag(r.IKU_kategori, ikuKind(r.IKU_kategori)) }
    ], ann, { sortKey: 'pm25_tahunan', dir: -1 });

    // year-over-year dumbbell
    const yo = sts.filter(s => s.pm25_2024_jan_14okt != null).sort((a, b) => a.pm25_2026_jan_14okt - b.pm25_2026_jan_14okt);
    const YC = { 2024: '#9ec5f4', 2025: '#3987e5', 2026: '#0d366b' };
    if (!yo.length) empty('ch-yoy', 'Tidak ada data pada filter ini'); else setOpt('ch-yoy', {
      grid: { left: 84, right: 20, top: 30, bottom: 30 }, legend: { top: 0, left: 0, data: ['2024', '2025', '2026'], textStyle: { fontSize: 11, color: INK2 } },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: ps => { const s = SM[ps[0].name.split(' ')[0]]; return `<b>${s.station}</b> · ${s.trend_overall} (${pct(s.chg_2024_2026_pct, 0, true)})` + [2024, 2025, 2026].map(y => tipRow(YC[y], String(y), nf(s['pm25_' + y + '_jan_14okt'], 1) + ' µg/m³')).join(''); } },
      xAxis: ax({ type: 'value', name: 'µg/m³' }),
      yAxis: ax({ type: 'category', data: yo.map(s => `${s.station} ${s.trend_overall === 'Memburuk' ? '▲' : s.trend_overall === 'Membaik' ? '▼' : '•'}`), axisLine: { show: false } }),
      series: [
        { type: 'custom', name: 'rentang', silent: true, renderItem: (p, api) => { const a = api.coord([api.value(1), api.value(0)]), b = api.coord([api.value(2), api.value(0)]); return { type: 'line', shape: { x1: a[0], y1: a[1], x2: b[0], y2: b[1] }, style: { stroke: AXIS, lineWidth: 2 } }; },
          data: yo.map((s, k) => [k, Math.min(s.pm25_2024_jan_14okt, s.pm25_2025_jan_14okt, s.pm25_2026_jan_14okt), Math.max(s.pm25_2024_jan_14okt, s.pm25_2025_jan_14okt, s.pm25_2026_jan_14okt)]), encode: { x: [1, 2], y: 0 } },
        ...[2024, 2025, 2026].map(y => ({ name: String(y), type: 'scatter', symbolSize: 9, itemStyle: { color: YC[y], borderColor: '#fff', borderWidth: 1.2 }, data: yo.map(s => +s['pm25_' + y + '_jan_14okt'].toFixed(1)) }))
      ]
    });
  }

  // =========================================================================================
  // PAGE: KRITIS
  // =========================================================================================
  function renderKritis() {
    const sts = scope();
    const perStation = F.st.size >= 1 && F.st.size <= 6;
    // diurnal
    seg('seg-diur', [['pm25', 'PM2.5'], ['no2', 'NO₂'], ['co', 'CO'], ['o3', 'O₃']], 'diur', () => renderKritis());
    const groups = perStation ? sts.map((s, k) => ({ name: s.station, color: SERIES[k % 8], m: [s] }))
      : CATS.filter(c => F.cat.has(c)).map(c => ({ name: CAT_S[c], color: C_CAT[c], m: sts.filter(s => s.site_category === c) })).filter(g => g.m.length);
    const dser = groups.map(g => ({ name: g.name, type: 'line', symbol: 'none', lineStyle: { width: 2, color: g.color }, itemStyle: { color: g.color },
      data: Array.from({ length: 24 }, (_, h) => { const v = g.m.map(s => (D.diurnal[s.station] || {})[F.diur]).filter(Boolean).map(a => a[h]).filter(x => x != null); return v.length ? +(v.reduce((a, b) => a + b, 0) / v.length).toFixed(2) : null; }) }));
    const pk = dser.map(s => { const m = Math.max(...s.data.filter(x => x != null)); return s.data.indexOf(m); });
    $('sub-diur').textContent = dser.length ? `${POL[F.diur]} rata-rata per jam (WIB). Jam puncak: ${[...new Set(pk)].sort((a, b) => a - b).map(h => String(h).padStart(2, '0') + ':00').join(', ')}.` : '';
    if (!dser.length) empty('ch-diur', 'Tidak ada data pada filter ini'); else setOpt('ch-diur', {
      grid: { left: 50, right: 16, top: 34, bottom: 34 }, legend: { top: 0, left: 0, itemWidth: 18, itemHeight: 3, textStyle: { fontSize: 11, color: INK2 } },
      tooltip: { trigger: 'axis', formatter: ps => `<b>Pukul ${String(ps[0].axisValue).padStart(2, '0')}:00</b>` + ps.filter(p => p.value != null).sort((a, b) => b.value - a.value).map(p => tipRow(p.color, p.seriesName, nf(p.value, F.diur === 'co' ? 0 : 1) + ' µg/m³')).join('') },
      xAxis: ax({ type: 'category', data: Array.from({ length: 24 }, (_, h) => h), boundaryGap: false, name: 'Jam', axisLabel: { color: INK2, fontSize: 11, interval: 2 } }),
      yAxis: ax({ type: 'value', name: 'µg/m³', scale: true }),
      series: dser.map((s, k) => k === 0 ? Object.assign(s, { markArea: { silent: true, itemStyle: { color: 'rgba(253,224,58,.18)' }, data: [[{ xAxis: 7 }, { xAxis: 8 }], [{ xAxis: 18 }, { xAxis: 19 }]] } }) : s)
    });

    // weekday vs weekend
    seg('seg-week', [['no2', 'NO₂'], ['pm25', 'PM2.5']], 'week', () => renderKritis());
    const avgProf = key => Array.from({ length: 24 }, (_, h) => { const v = sts.map(s => (D.diurnal[s.station] || {})[key]).filter(Boolean).map(a => a[h]).filter(x => x != null); return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null; });
    const wd = avgProf(F.week + '_wd'), we = avgProf(F.week + '_we');
    const mwd = wd.reduce((a, b) => a + (b || 0), 0) / 24, mwe = we.reduce((a, b) => a + (b || 0), 0) / 24;
    $('sub-week').textContent = sts.length ? `${POL[F.week]} rata-rata ${sts.length} stasiun. Selisih akhir pekan vs hari kerja: ${pct((mwe / mwd - 1) * 100, 2, true)} — praktis tidak ada efek akhir pekan.` : '';
    if (!sts.length) empty('ch-week', 'Tidak ada data pada filter ini'); else setOpt('ch-week', {
      grid: { left: 50, right: 16, top: 34, bottom: 34 }, legend: { top: 0, left: 0, itemWidth: 18, itemHeight: 3, textStyle: { fontSize: 11, color: INK2 } },
      tooltip: { trigger: 'axis', formatter: ps => `<b>Pukul ${String(ps[0].axisValue).padStart(2, '0')}:00</b>` + ps.map(p => tipRow(p.color, p.seriesName, nf(p.value, 1) + ' µg/m³')).join('') },
      xAxis: ax({ type: 'category', data: Array.from({ length: 24 }, (_, h) => h), boundaryGap: false, name: 'Jam', axisLabel: { color: INK2, fontSize: 11, interval: 2 } }),
      yAxis: ax({ type: 'value', name: 'µg/m³', scale: true }),
      series: [{ name: 'Hari kerja (Sen–Jum)', type: 'line', symbol: 'none', lineStyle: { width: 2.5, color: SERIES[0] }, itemStyle: { color: SERIES[0] }, data: wd.map(v => v == null ? null : +v.toFixed(2)) },
        { name: 'Akhir pekan (Sab–Min)', type: 'line', symbol: 'none', lineStyle: { width: 2, color: SERIES[1], type: 'dashed' }, itemStyle: { color: SERIES[1] }, data: we.map(v => v == null ? null : +v.toFixed(2)) }]
    });

    // heatmap station x month
    seg('seg-heat', Object.entries(POL), 'heat', () => renderKritis());
    const hs = sts.map(s => ({ s, m: stMean(s.station, F.heat) })).filter(x => x.m.n >= MIN_DAYS).sort((a, b) => b.m.mean - a.m.mean);
    const cells = []; let vmax = 0;
    hs.forEach((x, r) => {
      const d = D.daily[x.s.station], hs = d['hs_' + F.heat], hn = d['hn_' + F.heat], sum = new Float64Array(12), n = new Int32Array(12);
      for (let i = 0; i < NDAYS; i++) if (MASK[i] && hn[i] > 0 && hs[i] != null) { sum[DAY_M[i]] += hs[i]; n[DAY_M[i]] += hn[i]; }
      for (let m = 0; m < 12; m++) if (n[m]) { const v = sum[m] / n[m]; vmax = Math.max(vmax, v); cells.push([m, r, +v.toFixed(1)]); }
    });
    const hot = cells.reduce((b, c) => (!b || c[2] > b[2]) ? c : b, null);
    $('sub-heat').textContent = hot ? `${POL[F.heat]} rata-rata per bulan dalam setahun. Sel terpanas: ${hs[hot[1]].s.station}, ${MONTHS[hot[0]]} (${nf(hot[2], 1)} µg/m³).` : '';
    if (!cells.length) empty('ch-heat', 'Tidak ada data pada filter ini'); else setOpt('ch-heat', {
      grid: { left: 70, right: 80, top: 20, bottom: 30 },
      tooltip: { trigger: 'item', formatter: p => `<b>${hs[p.value[1]].s.station}</b> · ${MONTHS[p.value[0]]}<br>${tipRow(SEQ[5], POL[F.heat], nf(p.value[2], 1) + ' µg/m³')}` },
      xAxis: ax({ type: 'category', data: MONTHS, splitArea: { show: false }, axisLine: { show: false } }),
      yAxis: ax({ type: 'category', data: hs.map(x => x.s.station), inverse: true, axisLine: { show: false } }),
      visualMap: { min: 0, max: Math.ceil(vmax), calculable: true, orient: 'vertical', right: 0, top: 'middle', itemHeight: 160, inRange: { color: SEQ }, textStyle: { color: INK2, fontSize: 10 }, text: ['µg/m³', ''] },
      series: [{ type: 'heatmap', data: cells.map(c => ({ value: c, label: { color: c[2] > vmax * 0.5 ? '#ffffff' : INK } })), itemStyle: { borderColor: '#fff', borderWidth: 1 },
        label: { show: true, fontSize: 9, formatter: p => nf(p.value[2], 0) }, emphasis: { itemStyle: { borderColor: INK, borderWidth: 1 } } }]
    });

    // haze timeline (gantt)
    const codes = new Set(sts.map(s => s.station));
    const eps = D.episodes.filter(e => codes.has(e.station) && idxOf(e.end) >= F.d0 && idxOf(e.start) <= F.d1);
    const rowsSt = [...new Set(eps.map(e => e.station))].sort((a, b) => eps.filter(e => e.station === b).reduce((s, e) => s + e.days, 0) - eps.filter(e => e.station === a).reduce((s, e) => s + e.days, 0));
    const totDays = eps.reduce((s, e) => s + e.days, 0);
    const pk2 = eps.reduce((b, e) => (!b || e.pm25_peak_daily > b.pm25_peak_daily) ? e : b, null);
    $('sub-gantt').textContent = eps.length ? `${eps.length} episode, ${nf(totDays, 0)} hari-stasiun. Puncak harian: ${pk2.station} ${nf(pk2.pm25_peak_daily, 0)} µg/m³ (episode ${pk2.start} s.d. ${pk2.end}).` : 'Tidak ada episode kabut asap pada filter ini.';
    if (!eps.length) empty('ch-gantt', 'Tidak ada episode kabut asap pada filter ini'); else setOpt('ch-gantt', {
      grid: { left: 70, right: 20, top: 30, bottom: 50 }, legend: { top: 0, left: 0, data: ISL.filter(i => eps.some(e => e.island === i)), textStyle: { fontSize: 11, color: INK2 } },
      tooltip: { trigger: 'item', formatter: p => { const e = p.data.e; return `<b>${e.station}</b> · ${e.start} s.d. ${e.end} (${e.days} hari)` + tipRow(C_ISL[e.island], 'PM2.5 rata-rata', nf(e.pm25_mean, 0) + ' µg/m³') + tipRow(C_ISL[e.island], 'Puncak harian', nf(e.pm25_peak_daily, 0) + ' µg/m³') + tipRow(C_ISL[e.island], 'CO rata-rata', nf(e.co_mean, 0) + ' µg/m³') + tipRow(C_ISL[e.island], 'ISPU maksimum', nf(e.ispu_max, 0)); } },
      xAxis: ax({ type: 'time', min: T0 + F.d0 * 864e5, max: T0 + (F.d1 + 1) * 864e5, axisLabel: { color: INK2, fontSize: 11, formatter: v => { const d = new Date(v); return `${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`; } } }),
      yAxis: ax({ type: 'category', data: rowsSt, axisLine: { show: false }, splitLine: { show: false } }),
      dataZoom: [{ type: 'inside', xAxisIndex: 0, filterMode: 'weakFilter' }, { type: 'slider', xAxisIndex: 0, height: 18, bottom: 8, filterMode: 'weakFilter', borderColor: GRID }],
      series: [...ISL.map(i => ({ name: i, type: 'custom', itemStyle: { color: C_ISL[i] },
        renderItem: (params, api) => {
          const y = api.value(0), a = api.coord([api.value(1), y]), b = api.coord([api.value(2), y]), h = api.size([0, 1])[1] * 0.62;
          const shape = echarts.graphic.clipRectByRect({ x: a[0], y: a[1] - h / 2, width: Math.max(b[0] - a[0], 2), height: h }, { x: params.coordSys.x, y: params.coordSys.y, width: params.coordSys.width, height: params.coordSys.height });
          return shape && { type: 'rect', shape: Object.assign(shape, { r: 2 }), style: api.style() };
        },
        encode: { x: [1, 2], y: 0 },
        data: eps.filter(e => e.island === i).map(e => ({ value: [rowsSt.indexOf(e.station), Date.parse(e.start + 'T00:00:00Z'), Date.parse(e.end + 'T00:00:00Z') + 864e5], e })) }))]
    });

    // category profile table (static)
    table('tb-cat', [
      { key: 'site_category', label: 'Tipe lokasi', render: r => el('span', { style: 'white-space:nowrap' }, el('i', { style: `display:inline-block;width:9px;height:9px;border-radius:50%;background:${C_CAT[r.site_category]};margin-right:6px` }), CAT_S[r.site_category]) },
      { key: 'n_stasiun', label: 'Stasiun', num: true }, { key: 'pm25', label: 'PM2.5', num: true, render: r => nf(r.pm25, 1) },
      { key: 'no2', label: 'NO₂', num: true, render: r => nf(r.no2, 1) }, { key: 'co', label: 'CO', num: true, render: r => nf(r.co, 0) },
      { key: 'pct_hari_lewat_bm24jam_pm25', label: '% hari > BM 24 jam', num: true, render: r => pct(r.pct_hari_lewat_bm24jam_pm25, 1) },
      { key: 'kemarau_vs_hujan_pm25_pct', label: 'Kemarau vs hujan', num: true, render: r => pct(r.kemarau_vs_hujan_pm25_pct, 0, true) },
      { key: 'hari_kabut_asap_per_stasiun', label: 'Hari kabut / stasiun', num: true, render: r => nf(r.hari_kabut_asap_per_stasiun, 0) }
    ], D.catprof.filter(r => F.cat.has(r.site_category)), { sortKey: 'pm25', dir: -1 });

    // critical ranking (static, filtered)
    const crit = D.critical.filter(r => codes.has(r.station)).map((r, k) => Object.assign({ rank: D.critical.indexOf(r) + 1 }, r));
    table('tb-crit', [
      { key: 'rank', label: '#', num: true }, { key: 'station', label: 'Stasiun' }, { key: 'provinsi', label: 'Provinsi' },
      { key: 'critical_score', label: 'Skor', num: true, render: r => nf(r.critical_score, 0) },
      { key: 'pm25_mean', label: 'PM2.5', num: true, render: r => nf(r.pm25_mean, 1) },
      { key: 'days_ispu_tidak_sehat_plus', label: 'Hari TS+', num: true, render: r => nf(r.days_ispu_tidak_sehat_plus, 0) }
    ], crit, { sortKey: 'rank', dir: 1 });
  }

  // =========================================================================================
  // PAGE: FAKTOR
  // =========================================================================================
  function renderFaktor() {
    $('r2').textContent = nf(D.meta.rf_r2, 2);
    const imp = [...D.importance].sort((a, b) => a.importance - b.importance);
    setOpt('ch-imp', {
      grid: { left: 140, right: 50, top: 20, bottom: 30 },
      tooltip: { trigger: 'item', formatter: p => `<b>${p.name}</b>` + tipRow(SERIES[0], 'Porsi kepentingan', pct(imp[p.dataIndex].share_pct, 1)) + tipRow(SERIES[0], 'Penurunan R²', nf(p.value, 3)) },
      xAxis: ax({ type: 'value', name: 'Penurunan R²' }), yAxis: ax({ type: 'category', data: imp.map(r => r.group), axisLine: { show: false } }),
      series: [{ type: 'bar', barWidth: '60%', data: imp.map(r => ({ value: +r.importance.toFixed(4), itemStyle: { color: r.share_pct >= 10 ? SERIES[0] : '#86b6ef', borderRadius: [0, 4, 4, 0] } })),
        label: { show: true, position: 'right', fontSize: 10.5, color: INK2, formatter: p => pct(imp[p.dataIndex].share_pct, 0) } }]
    });

    // correlation heatmap
    const PO = ['pm25', 'pm10', 'so2', 'co', 'o3', 'no2'], FA = ['temperature_c', 'humidity_pct', 'wind_speed_ms'], FL = ['Suhu', 'Kelembapan', 'Kecepatan angin'];
    const cells = []; D.meteo.forEach(r => cells.push([FA.indexOf(r.factor), PO.indexOf(r.pollutant), +r.r_rata2.toFixed(2), r.n_stasiun_abs_r_gt_0_3, r.n_stasiun]));
    setOpt('ch-corr', {
      grid: { left: 60, right: 80, top: 20, bottom: 30 },
      tooltip: { trigger: 'item', formatter: p => `<b>${POL[PO[p.value[1]]]} × ${FL[p.value[0]]}</b>` + tipRow(p.color, 'r rata-rata', nf(p.value[2], 2)) + `<div style="color:${MUTED};font-size:11px;margin-top:4px">|r| &gt; 0,3 di ${p.value[3]} dari ${p.value[4]} stasiun</div>` },
      xAxis: ax({ type: 'category', data: FL, axisLine: { show: false } }), yAxis: ax({ type: 'category', data: PO.map(p => POL[p]), inverse: true, axisLine: { show: false } }),
      visualMap: { min: -0.5, max: 0.5, dimension: 2, calculable: true, right: 0, top: 'middle', itemHeight: 140, inRange: { color: DIV }, textStyle: { color: INK2, fontSize: 10 }, text: ['+', '−'] },
      series: [{ type: 'heatmap', data: cells, itemStyle: { borderColor: '#fff', borderWidth: 2 }, label: { show: true, color: INK, fontSize: 12, formatter: p => nf(p.value[2], 2) } }]
    });

    // traffic scatter
    seg('seg-traf', [['pm25', 'PM2.5'], ['pm10', 'PM10'], ['no2', 'NO₂'], ['co', 'CO']], 'traf', () => renderFaktor());
    const codes = new Set(scope().map(s => s.station));
    const pts = D.wet.filter(r => codes.has(r.station) && r[F.traf] != null);
    const rho = D.sitefac.find(r => r.pollutant === F.traf && r.factor === 'traffic_intensity_per_h');
    $('sub-traf').textContent = `Spearman ρ = ${nf(rho.spearman_r, 2)} (p ${rho.p_value < 0.001 ? '< 0,001' : '= ' + nf(rho.p_value, 3)}; ${rho.n_stasiun} stasiun). Titik yang tampil mengikuti filter.`;
    const sz = d => 8 + 16 * (1 - (Math.log(d) - Math.log(6)) / (Math.log(250) - Math.log(6)));
    // label only the stations that carry the story: highest values, heaviest traffic, cleanest
    const keep = new Set([...[...pts].sort((a, b) => b[F.traf] - a[F.traf]).slice(0, 5), ...[...pts].sort((a, b) => b.traffic_intensity_per_h - a.traffic_intensity_per_h).slice(0, 3),
      ...[...pts].sort((a, b) => a[F.traf] - b[F.traf]).slice(0, 2)].map(r => r.station));
    if (!pts.length) empty('ch-traf', 'Tidak ada data pada filter ini'); else setOpt('ch-traf', {
      grid: { left: 56, right: 24, top: 34, bottom: 44 }, legend: { top: 0, left: 0, textStyle: { fontSize: 11, color: INK2 } },
      tooltip: { trigger: 'item', formatter: p => { const r = p.data.r; return `<b>${r.station}</b> · ${CAT_S[r.site_category]}` + tipRow(p.color, POL[F.traf], nf(r[F.traf], 1) + ' µg/m³') + tipRow(p.color, 'Lalu lintas', nf(r.traffic_intensity_per_h, 0) + ' kend/jam') + tipRow(p.color, 'Jarak ke jalan', nf(r.distance_to_road_m, 0) + ' m'); } },
      xAxis: ax({ type: 'value', name: 'Kendaraan per jam', nameLocation: 'middle', nameGap: 28 }), yAxis: ax({ type: 'value', name: POL[F.traf] + ' (µg/m³)', scale: true }),
      series: CATS.map(c => ({ name: CAT_S[c], type: 'scatter', itemStyle: { color: C_CAT[c], borderColor: '#fff', borderWidth: 1.5, opacity: .95 },
        data: pts.filter(r => r.site_category === c).map(r => ({ value: [r.traffic_intensity_per_h, r[F.traf]], symbolSize: sz(r.distance_to_road_m), r })),
        label: { show: true, position: 'right', fontSize: 9.5, color: INK2, formatter: p => keep.has(p.data.r.station) ? p.data.r.station : '' } })).filter(s => s.data.length)
    });
    getChart('ch-traf').off('click'); getChart('ch-traf').on('click', p => p.data && focusStation(p.data.r.station));

    // wind direction effect
    const w = D.wind.filter(r => codes.has(r.station) && r.sector_ratio != null).map(r => ({ r, v: (r.sector_ratio - 1) * 100 })).sort((a, b) => a.v - b.v);
    if (!w.length) empty('ch-wind', 'Tidak ada data pada filter ini'); else setOpt('ch-wind', {
      grid: { left: 62, right: 90, top: 16, bottom: 30 },
      tooltip: { trigger: 'item', formatter: p => { const r = w[p.dataIndex].r; return `<b>${r.station}</b>` + tipRow(p.color, 'Terkotor: dari ' + SEKTOR[r.dirtiest_sector], nf(r.dirtiest_pm25, 1) + ' µg/m³') + tipRow(AXIS, 'Terbersih: dari ' + SEKTOR[r.cleanest_sector], nf(r.cleanest_pm25, 1) + ' µg/m³'); } },
      xAxis: ax({ type: 'value', axisLabel: { formatter: '{value}%', color: INK2, fontSize: 11 } }), yAxis: ax({ type: 'category', data: w.map(x => x.r.station), axisLine: { show: false }, axisLabel: { interval: 0, color: INK2, fontSize: 10.5 } }),
      series: [{ type: 'bar', barWidth: '64%', data: w.map(x => ({ value: +x.v.toFixed(1), itemStyle: { color: x.v >= 10 ? SERIES[0] : AXIS, borderRadius: [0, 4, 4, 0] } })),
        label: { show: true, position: 'right', fontSize: 9.5, color: INK2, formatter: p => `${pct(p.value, 0, true)} dari ${SEKTOR[w[p.dataIndex].r.dirtiest_sector]}` } }]
    });
  }

  // =========================================================================================
  // PAGE: KESEHATAN
  // =========================================================================================
  function renderKesehatan() {
    seg('seg-out', Object.entries(OUT), 'out', () => renderKesehatan());
    const hs = hospInScope();
    // hospital selector
    const sel = $('sel-hosp');
    if (F.st.size === 1) { const h = HOSP.find(x => x.station === [...F.st][0]); if (h) F.hosp = h.id; }
    if (!hs.some(h => h.id === F.hosp) && hs.length) F.hosp = hs[0].id;
    sel.innerHTML = '';
    hs.forEach(h => { const o = el('option', { value: h.id }, `${h.id} · ${h.name} (stasiun ${h.station})`); if (h.id === F.hosp) o.selected = true; sel.append(o); });
    sel.onchange = () => { F.hosp = sel.value; renderKesehatan(); };

    // time series: PM2.5 (top) + cases (bottom)
    if (!hs.length) { empty('ch-ts', 'Tidak ada RS pada filter ini'); $('sub-ts').textContent = ''; }
    else {
      const h = F.hosp, st = D.health[h].station, dd = D.daily[st] || {}, used = SM[st] && SM[st].used_in_analysis;
      const idx = []; for (let i = F.d0; i <= F.d1; i++) idx.push(i);
      const pm = idx.map(i => (used && MASK[i] && dd.pm25 && dd.pm25[i] != null) ? dd.pm25[i] : null);
      const cs = idx.map(i => MASK[i] ? D.health[h][F.out][i] : null);
      const ma = cs.map((_, k) => { const w = cs.slice(Math.max(0, k - 6), k + 1).filter(x => x != null); return w.length >= 4 ? +(w.reduce((a, b) => a + b, 0) / w.length).toFixed(2) : null; });
      const areas = []; if (used) { let s0 = null; idx.forEach((i, k) => { const on = dd.haze[i] === 1 && MASK[i]; if (on && s0 == null) s0 = k; if ((!on || k === idx.length - 1) && s0 != null) { areas.push([{ xAxis: DAY_S[idx[s0]] }, { xAxis: DAY_S[idx[on ? k : k - 1]] }]); s0 = null; } }); }
      const tc = cs.reduce((a, b) => a + (b || 0), 0);
      $('sub-ts').textContent = `${h} (${(SM[st] || {}).kota_kabupaten || ''}) — ${OUT_FULL[F.out]}: ${nf(tc, 0)} kasus pada periode terpilih.` + (used ? ` ${areas.length} episode kabut asap.` : ' Stasiun pasangan (JMB-02) rusak sehingga tidak ada data paparan.');
      setOpt('ch-ts', {
        grid: [{ left: 56, right: 24, top: 30, height: '36%' }, { left: 56, right: 24, top: '56%', height: '30%' }],
        legend: { top: 0, left: 0, textStyle: { fontSize: 11, color: INK2 } },
        tooltip: { trigger: 'axis', axisPointer: { link: [{ xAxisIndex: 'all' }] }, formatter: ps => `<b>${fmtDay(idxOf(ps[0].axisValue))}</b>` + ps.filter(p => p.value != null).map(p => tipRow(p.color, p.seriesName, nf(p.value, p.seriesName.startsWith('PM') ? 1 : p.seriesName.includes('7 hari') ? 1 : 0))).join('') },
        axisPointer: { link: [{ xAxisIndex: 'all' }] },
        xAxis: [ax({ type: 'category', data: idx.map(i => DAY_S[i]), gridIndex: 0, axisLabel: { show: false }, boundaryGap: false }),
          ax({ type: 'category', data: idx.map(i => DAY_S[i]), gridIndex: 1, boundaryGap: false, axisLabel: { color: INK2, fontSize: 11, formatter: v => `${MONTHS[+v.slice(5, 7) - 1]} ${v.slice(0, 4)}` } })],
        yAxis: [ax({ type: 'value', gridIndex: 0, name: 'PM2.5 µg/m³' }), ax({ type: 'value', gridIndex: 1, name: 'kasus/hari' })],
        dataZoom: [{ type: 'inside', xAxisIndex: [0, 1] }, { type: 'slider', xAxisIndex: [0, 1], height: 18, bottom: 6, borderColor: GRID }],
        series: [
          { name: 'PM2.5 harian', type: 'line', xAxisIndex: 0, yAxisIndex: 0, symbol: 'none', lineStyle: { width: 1.5, color: SERIES[0] }, itemStyle: { color: SERIES[0] }, data: pm,
            markArea: { silent: true, itemStyle: { color: 'rgba(227,73,72,.10)' }, data: areas },
            markLine: { symbol: 'none', silent: true, lineStyle: { type: 'dashed', color: INK2 }, label: { formatter: 'Baku mutu 24 jam 55', fontSize: 10, color: INK2, position: 'insideEndTop' }, data: [{ yAxis: 55 }] } },
          { name: OUT[F.out] + ' (harian)', type: 'line', xAxisIndex: 1, yAxisIndex: 1, symbol: 'none', lineStyle: { width: 1, color: C_OUT[F.out], opacity: .45 }, itemStyle: { color: C_OUT[F.out] }, data: cs,
            markArea: { silent: true, itemStyle: { color: 'rgba(227,73,72,.10)' }, data: areas } },
          { name: OUT[F.out] + ' (rata-rata 7 hari)', type: 'line', xAxisIndex: 1, yAxisIndex: 1, symbol: 'none', lineStyle: { width: 2.2, color: C_OUT[F.out] }, itemStyle: { color: C_OUT[F.out] }, data: ma }
        ]
      });
      if (!used) getChart('ch-ts').setOption({ graphic: [{ type: 'text', left: 'center', top: '18%', style: { text: 'Tidak ada data paparan: stasiun pasangan JMB-02 rusak (defective)', fill: MUTED, fontSize: 13, fontFamily: FONT } }] });
    }

    // lag chart
    const lg = D.dlm.filter(r => r.outcome === F.out);
    const lags = lg.filter(r => r.lag !== 'kumulatif 0-7').sort((a, b) => +a.lag - +b.lag), cum = lg.find(r => r.lag === 'kumulatif 0-7');
    $('sub-lag').textContent = `${OUT_FULL[F.out]} — lag 0: ${pct(lags[0].pct_increase_per10, 1, true)} per +10 µg/m³; kumulatif 0–7 hari: ${pct(cum.pct_increase_per10, 1, true)} (95% CI ${nf(cum.pct_low, 1)}–${nf(cum.pct_high, 1)}%).`;
    setOpt('ch-lag', {
      grid: { left: 56, right: 20, top: 20, bottom: 36 },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: ps => { const r = lags[ps[0].dataIndex]; return `<b>Lag ${r.lag} hari</b>` + tipRow(C_OUT[F.out], '% kenaikan', pct(r.pct_increase_per10, 2, true)) + tipRow(AXIS, '95% CI', `${nf(r.pct_low, 1)} s.d. ${nf(r.pct_high, 1)}%`) + tipRow(AXIS, 'p', r.p_value < 0.001 ? '< 0,001' : nf(r.p_value, 3)); } },
      xAxis: ax({ type: 'category', data: lags.map(r => 'Lag ' + r.lag), axisLine: { lineStyle: { color: AXIS } } }),
      yAxis: ax({ type: 'value', name: '% per +10 µg/m³' }),
      series: [{ type: 'bar', barWidth: '52%', data: lags.map((r, k) => ({ value: +r.pct_increase_per10.toFixed(2), itemStyle: { color: k === 0 ? C_OUT[F.out] : '#c9c7be', borderRadius: 4 } })),
        label: { show: true, position: 'top', fontSize: 10, color: INK2, formatter: p => p.dataIndex === 0 ? pct(p.value, 1, true) : '' },
        markLine: { symbol: 'none', silent: true, lineStyle: { color: INK2 }, label: { show: false }, data: [{ yAxis: 0 }] } },
        { type: 'custom', name: '95% CI', renderItem: (p, api) => { const x = api.value(0), lo = api.coord([x, api.value(1)]), hi = api.coord([x, api.value(2)]), w = 5, st = { stroke: INK2, lineWidth: 1.2 };
          return { type: 'group', children: [{ type: 'line', shape: { x1: lo[0], y1: lo[1], x2: hi[0], y2: hi[1] }, style: st }, { type: 'line', shape: { x1: lo[0] - w, y1: lo[1], x2: lo[0] + w, y2: lo[1] }, style: st }, { type: 'line', shape: { x1: hi[0] - w, y1: hi[1], x2: hi[0] + w, y2: hi[1] }, style: st }] }; },
          data: lags.map((r, k) => [k, r.pct_low, r.pct_high]), encode: { x: 0, y: [1, 2] }, z: 10 }]
    });

    // dose response by ISPU band
    const BANDS = ['Baik (≤15,5)', 'Sedang (15,5–55,4)', 'Tidak Sehat (55,4–150,4)', 'Sangat Tidak Sehat (150,4–250,4)', 'Berbahaya (>250,4)'];
    const showO = [...new Set([F.out, 'resp_admissions_under5', 'resp_admissions_over60', 'cvd', 'death'])];
    setOpt('ch-band', {
      grid: { left: 50, right: 16, top: 34, bottom: 50 }, legend: { top: 0, left: 0, textStyle: { fontSize: 11, color: INK2 } },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: ps => `<b>${ps[0].axisValue.replace('\n', ' ')}</b>` + ps.map(p => { const r = D.band.find(b => b.outcome === OUT_FULL[showO[p.seriesIndex]] && b.band === BANDS[p.dataIndex]); return tipRow(p.color, p.seriesName, `${nf(p.value, 2)}× (${nf(r.RR_low, 2)}–${nf(r.RR_high, 2)})`); }).join('') },
      xAxis: ax({ type: 'category', data: BANDS.map(b => b.replace(' (', '\n(')), axisLabel: { color: INK2, fontSize: 10, interval: 0 } }),
      yAxis: ax({ type: 'value', name: 'Risiko relatif (×)', min: 0 }),
      series: showO.map(o => ({ name: OUT[o], type: 'bar', barGap: '8%', itemStyle: { color: C_OUT[o], borderRadius: [3, 3, 0, 0] },
        data: BANDS.map(b => { const r = D.band.find(x => x.outcome === OUT_FULL[o] && x.band === b); return r ? +r.RR.toFixed(3) : null; }),
        markLine: o === showO[0] ? { symbol: 'none', silent: true, lineStyle: { type: 'dashed', color: INK2 }, label: { formatter: 'RR = 1', fontSize: 10, color: INK2, position: 'insideEndTop' }, data: [{ yAxis: 1 }] } : undefined }))
    });

    // haze vs normal (dynamic)
    const hz = hazeStats(hs.map(h => h.id));
    const hv = Object.keys(OUT).map(o => ({ o, v: hz.pct[o] })).filter(x => x.v != null).sort((a, b) => a.v - b.v);
    $('sub-hz').textContent = hv.length ? `Rata-rata kasus harian saat episode kabut asap vs hari biasa, ${hz.n} RS yang mengalami episode pada filter ini.` : 'Tidak ada RS dengan episode kabut asap pada filter ini.';
    if (!hv.length) empty('ch-hz', 'Tidak ada episode kabut asap pada filter ini'); else setOpt('ch-hz', {
      grid: { left: 110, right: 50, top: 14, bottom: 30 },
      tooltip: { trigger: 'item', formatter: p => `<b>${p.name}</b>` + tipRow(p.color, 'Kenaikan saat kabut asap', pct(p.value, 1, true)) },
      xAxis: ax({ type: 'value', axisLabel: { formatter: '{value}%', color: INK2, fontSize: 11 } }), yAxis: ax({ type: 'category', data: hv.map(x => OUT[x.o]), axisLine: { show: false } }),
      series: [{ type: 'bar', barWidth: '60%', data: hv.map(x => ({ value: +x.v.toFixed(1), itemStyle: { color: C_OUT[x.o], borderRadius: [0, 4, 4, 0] } })),
        label: { show: true, position: 'right', fontSize: 10.5, color: INK2, formatter: p => pct(p.value, 0, true) } }]
    });

    // attributable (static)
    const at = D.attr.filter(r => r.outcome === OUT_FULL[F.out] && r.island !== 'Total' && F.isl.has(r.island)).sort((a, b) => a.attributable - b.attributable);
    const atT = D.attr.find(r => r.outcome === OUT_FULL[F.out] && r.island === 'Total');
    $('sub-attr').textContent = `${OUT_FULL[F.out]}: ±${nf(atT.attributable, 0)} kasus (${pct(atT.attributable_pct, 1)}) di seluruh RS akan tidak terjadi bila PM2.5 berada di kategori Baik.`;
    setOpt('ch-attr', {
      grid: { left: 90, right: 90, top: 14, bottom: 30 },
      tooltip: { trigger: 'item', formatter: p => { const r = at[p.dataIndex]; return `<b>${r.island}</b>` + tipRow(C_ISL[r.island], 'Kasus teratribusi', nf(r.attributable, 0)) + tipRow(C_ISL[r.island], '% dari total kasus', pct(r.attributable_pct, 1)); } },
      xAxis: ax({ type: 'value', name: 'kasus' }), yAxis: ax({ type: 'category', data: at.map(r => r.island), axisLine: { show: false } }),
      series: [{ type: 'bar', barWidth: '58%', data: at.map(r => ({ value: Math.round(r.attributable), itemStyle: { color: C_ISL[r.island], borderRadius: [0, 4, 4, 0] } })),
        label: { show: true, position: 'right', fontSize: 10.5, color: INK2, formatter: p => `${nf(p.value, 0)} (${pct(at[p.dataIndex].attributable_pct, 0)})` } }]
    });

    // vulnerability table
    const scopes = ['Semua RS', ...ISL];
    const vr = scopes.map(sc => {
      const g = D.vuln.filter(r => r.scope === sc);
      const b = g.find(r => r.group.startsWith('ISPA balita')), l = g.find(r => r.group.startsWith('ISPA lansia')), q = g.find(r => r.group.startsWith('Rasio'));
      return b && l ? { scope: sc, n: b.n_hospitals, b: b.pct_increase_per10, l: l.pct_increase_per10, d: b.pct_increase_per10 - l.pct_increase_per10, z: q ? q.z_diff : null } : null;
    }).filter(Boolean);
    table('tb-vuln', [
      { key: 'scope', label: 'Cakupan' }, { key: 'n', label: 'Jumlah RS', num: true },
      { key: 'b', label: 'ISPA balita', num: true, render: r => pct(r.b, 1, true) }, { key: 'l', label: 'ISPA lansia', num: true, render: r => pct(r.l, 1, true) },
      { key: 'd', label: 'Selisih (poin)', num: true, render: r => (r.d > 0 ? '+' : '') + nf(r.d, 2) },
      { key: 'z', label: 'Uji beda (z)', num: true, render: r => { const sp = el('span', {}, nf(r.z, 2) + ' '); sp.append(Math.abs(r.z) >= 1.96 ? tag('signifikan', 'ok') : tag('tidak signifikan', 'neu')); return sp; } },
      { key: 'scope', label: 'Catatan', render: r => r.n <= 2 ? 'RS sedikit — tafsirkan hati-hati' : '' }
    ], vr);
  }

  // =========================================================================================
  // PAGE: JARINGAN
  // =========================================================================================
  const W = { polusi: .25, kabut_asap: .20, beban_kesehatan: .20, defisit_data: .20, keterisolasian: .15 };
  const WL = { polusi: 'Polusi', kabut_asap: 'Kabut asap', beban_kesehatan: 'Beban kesehatan', defisit_data: 'Defisit data', keterisolasian: 'Keterisolasian' };
  function renderJaringan() {
    const sts = scope(true);
    if (!mapNet) {
      mapNet = L.map('map-net', { scrollWheelZoom: false, zoomSnap: 0.25 }).fitBounds(ST.map(s => [s.latitude_dd, s.longitude_dd]), { padding: [24, 24] });
      tiles(mapNet); netLayer = L.layerGroup().addTo(mapNet);
      const lg = $('legend-net');
      Object.entries(REL_C).forEach(([k, c]) => lg.append(el('span', {}, el('i', { style: `background:${c}` }), k.replace(' - ', ': '))));
      lg.append(el('span', {}, el('i', { class: 'ln' }), 'celah ≥300 km'));
    }
    mapNet.invalidateSize();
    netLayer.clearLayers();
    D.gaps.filter(g => F.isl.has(g.island)).forEach(g => {
      const a = SM[g.station_a], b = SM[g.station_b], wide = g.jarak_km >= 300;
      L.polyline([[a.latitude_dd, a.longitude_dd], [b.latitude_dd, b.longitude_dd]], { color: wide ? CRIT : '#9a9890', weight: wide ? 2 : 1, dashArray: wide ? '6 6' : null, opacity: .9 })
        .bindTooltip(`${g.station_a} – ${g.station_b}: ${nf(g.jarak_km, 0)} km`).addTo(netLayer);
    });
    sts.forEach(s => {
      const r = s.pm25_mean == null ? 5 : 5 + Math.sqrt(s.pm25_mean) * 1.4;
      const mk = L.circleMarker([s.latitude_dd, s.longitude_dd], { radius: r, color: '#fff', weight: 1.5, fillColor: REL_C[s.reliability] || MUTED, fillOpacity: .92 }).addTo(netLayer);
      mk.bindTooltip(`${s.station} · ${s.reliability}`);
      mk.bindPopup(el('div', {}, el('b', {}, `${s.station} — ${s.kota_kabupaten}`), el('br'), `Status: ${s.status_operasional} · kelengkapan PM2.5 ${nf(s.completeness_pm25_pct, 1)}%`, el('br'),
        `Keandalan: ${s.reliability}`, el('br'), `Aksi: ${s.aksi_alat}`, el('br'), `Stasiun terdekat: ${s.nearest_station} (${nf(s.nn_distance_km, 0)} km)`, el('br'), `Skor prioritas: ${nf(s.priority_score, 1)}`));
    });

    // priority stacked bar
    const pr = sts.filter(s => s.priority_score != null).sort((a, b) => a.priority_score - b.priority_score);
    const comp = s => { const ks = Object.keys(W).filter(k => s['komp_' + k] != null); const ws = ks.reduce((a, k) => a + W[k], 0); return Object.fromEntries(Object.keys(W).map(k => [k, s['komp_' + k] == null ? 0 : s['komp_' + k] * W[k] / ws * 100])); };
    if (!pr.length) empty('ch-prio', 'Tidak ada stasiun pada filter ini'); else setOpt('ch-prio', {
      grid: { left: 62, right: 30, top: 48, bottom: 30 }, legend: { top: 0, left: 0, itemWidth: 12, itemHeight: 10, textStyle: { fontSize: 10.5, color: INK2 } },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: ps => { const s = SM[ps[0].name]; return `<b>${s.station}</b> · skor ${nf(s.priority_score, 1)}` + ps.map(p => tipRow(p.color, p.seriesName, nf(p.value, 1))).join('') + (s.komponen_tidak_tersedia ? `<div style="color:${MUTED};font-size:11px;margin-top:4px">Tanpa komponen: ${s.komponen_tidak_tersedia.replace(/_/g, ' ')}</div>` : ''); } },
      xAxis: ax({ type: 'value', max: 100, name: 'skor' }), yAxis: ax({ type: 'category', data: pr.map(s => s.station), axisLine: { show: false } }),
      series: Object.keys(W).map((k, i) => ({ name: `${WL[k]} (${W[k] * 100}%)`, type: 'bar', stack: 'p', barWidth: '64%', itemStyle: { color: SERIES[i], borderColor: '#fff', borderWidth: 1 }, data: pr.map(s => +comp(s)[k].toFixed(2)) }))
    });
    getChart('ch-prio').off('click'); getChart('ch-prio').on('click', p => focusStation(p.name));

    table('tb-cov', [
      { key: 'island', label: 'Pulau' }, { key: 'n_stasiun', label: 'Stasiun', num: true }, { key: 'n_stasiun_andal', label: 'Andal', num: true },
      { key: 'n_provinsi_tercakup', label: 'Provinsi', num: true }, { key: 'jarak_tetangga_median_km', label: 'Median jarak tetangga', num: true, render: r => nf(r.jarak_tetangga_median_km, 0) + ' km' },
      { key: 'celah_terlebar_km', label: 'Celah terlebar', num: true, render: r => `${nf(r.celah_terlebar_km, 0)} km (${r.celah_terlebar_antara})` },
      { key: 'pm25_mean', label: 'PM2.5', num: true, render: r => nf(r.pm25_mean, 1) }, { key: 'hari_kabut_asap', label: 'Hari kabut', num: true, render: r => nf(r.hari_kabut_asap, 0) }
    ], D.coverage.filter(r => F.isl.has(r.island)));
  }

  // =========================================================================================
  // PAGE: METODE
  // =========================================================================================
  function renderMetode() {
    table('tb-clean', [{ key: 'rule', label: 'Aturan / masalah' }, { key: 'n', label: 'Jumlah', num: true, render: r => nf(r.n, 0) }, { key: 'stasiun', label: 'Stasiun' }],
      D.cleaning, { sortKey: 'n', dir: -1 });
    table('tb-conv', [{ key: 'parameter', label: 'Parameter', render: r => POL[r.parameter] }, { key: 'basis_ppm', label: 'Basis ppm' },
      { key: 'massa_molar_g_per_mol', label: 'M (g/mol)', num: true, render: r => nf(r.massa_molar_g_per_mol, 3) },
      { key: 'faktor_ug_m3_per_ppm', label: 'Faktor', num: true, render: r => nf(r.faktor_ug_m3_per_ppm, 1) }], D.conversion);
    const relKind = r => r === 'Baik' ? 'ok' : r === 'Perlu standardisasi' ? 'warn' : 'bad';
    table('tb-quality', [
      { key: 'station', label: 'Stasiun' }, { key: 'island', label: 'Pulau' }, { key: 'provinsi', label: 'Provinsi' }, { key: 'site_type', label: 'Tipe lokasi (sites.csv)' },
      { key: 'status_operasional', label: 'Status alat' }, { key: 'completeness_pm25_pct', label: 'Kelengkapan PM2.5', num: true, render: r => pct(r.completeness_pm25_pct, 1) },
      { key: 'reliability', label: 'Keandalan', render: r => tag(r.reliability, relKind(r.reliability)) }, { key: 'aksi_alat', label: 'Aksi' }
    ], ST.filter(s => F.isl.has(s.island) && F.cat.has(s.site_category)), { sortKey: 'completeness_pm25_pct', dir: 1 });
  }

  // =========================================================================================
  // NAVIGATION
  // =========================================================================================
  const PAGES = ['ringkasan', 'kondisi', 'kritis', 'faktor', 'kesehatan', 'jaringan', 'metode'];
  const RENDER = { ringkasan: renderRingkasan, kondisi: renderKondisi, kritis: renderKritis, faktor: renderFaktor, kesehatan: renderKesehatan, jaringan: renderJaringan, metode: renderMetode };
  const dirty = Object.fromEntries(PAGES.map(p => [p, true]));
  let current = 'ringkasan';
  function renderPage(p) { if (!dirty[p]) return; dirty[p] = false; try { RENDER[p](); } catch (e) { console.error('render', p, e); } }
  function go(p, push = true) {
    if (!PAGES.includes(p)) p = 'ringkasan';
    current = p;
    PAGES.forEach(x => { $('p-' + x).hidden = x !== p; });
    document.querySelectorAll('.tab').forEach(t => t.setAttribute('aria-selected', String(t.dataset.page === p)));
    renderPage(p);
    requestAnimationFrame(() => { Object.values(charts).forEach(c => { if (c.getDom().offsetParent) c.resize(); }); if (p === 'ringkasan' && mapHome) mapHome.invalidateSize(); if (p === 'jaringan' && mapNet) mapNet.invalidateSize(); });
    if (push) history.replaceState(null, '', '#' + p);
    document.title = `${$('p-' + p).dataset.title} — DA2026 Dashboard Gelar Rasa`;
  }

  // =========================================================================================
  // INIT
  // =========================================================================================
  function init() {
    $('foot-team').textContent = `DA2026 Dashboard · Tim ${D.meta.team} · Ketua ${D.meta.leader} · Gelar Rasa 2026`;
    chips('f-island', ISL, F.isl, C_ISL);
    chips('f-cat', CATS, F.cat, C_CAT, CAT_S);
    setPeriod('all');
    $('f-period').addEventListener('change', e => { setPeriod(e.target.value); onFilter(); });
    const onDate = () => { let a = idxOf($('f-d0').value), b = idxOf($('f-d1').value); if (Number.isNaN(a) || Number.isNaN(b)) return; a = Math.max(0, Math.min(NDAYS - 1, a)); b = Math.max(0, Math.min(NDAYS - 1, b)); if (a > b) [a, b] = [b, a]; F.d0 = a; F.d1 = b; onFilter(); };
    $('f-d0').addEventListener('change', onDate); $('f-d1').addEventListener('change', onDate);
    $('f-season').addEventListener('change', e => { F.season = e.target.value; onFilter(); });
    $('f-reset').addEventListener('click', resetAll);
    $('toast-reset').addEventListener('click', () => { F.st = new Set(); $('toast').hidden = true; onFilter(); });
    const btn = $('dd-btn'), panel = $('dd-panel');
    btn.addEventListener('click', e => { e.stopPropagation(); panel.hidden = !panel.hidden; btn.setAttribute('aria-expanded', String(!panel.hidden)); if (!panel.hidden) $('dd-search').focus(); });
    panel.addEventListener('click', e => e.stopPropagation());
    document.addEventListener('click', () => { panel.hidden = true; btn.setAttribute('aria-expanded', 'false'); });
    document.addEventListener('keydown', e => { if (e.key === 'Escape') { panel.hidden = true; btn.setAttribute('aria-expanded', 'false'); } });
    $('dd-search').addEventListener('input', buildStationList);
    $('dd-all').addEventListener('click', () => { F.st = new Set(); onFilter(); });
    $('dd-none').addEventListener('click', () => { F.st = new Set(); onFilter(); });
    document.querySelectorAll('.tab').forEach(t => t.addEventListener('click', () => { go(t.dataset.page); window.scrollTo({ top: 0, behavior: 'smooth' }); }));
    document.querySelector('.tabs').addEventListener('keydown', e => {
      if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
      const i = PAGES.indexOf(current) + (e.key === 'ArrowRight' ? 1 : -1); const p = PAGES[(i + PAGES.length) % PAGES.length];
      go(p); document.querySelector(`.tab[data-page="${p}"]`).focus();
    });
    document.querySelectorAll('[data-go]').forEach(b => b.addEventListener('click', () => { go(b.dataset.go); window.scrollTo({ top: 0, behavior: 'smooth' }); }));
    let rt; window.addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(() => Object.values(charts).forEach(c => { if (c.getDom().offsetParent) c.resize(); }), 150); });
    window.addEventListener('hashchange', () => go(location.hash.slice(1), false));
    rebuildMask(); summary(); buildStationList();
    go(location.hash.slice(1) || 'ringkasan', false);
  }
  if (!window.echarts || !window.L) {
    document.querySelector('main').prepend(el('div', { class: 'answer' }, 'Pustaka grafik/peta gagal dimuat. Pastikan perangkat terhubung ke internet lalu muat ulang halaman.'));
  }
  init();
})();
