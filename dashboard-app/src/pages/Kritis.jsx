import { useMemo } from 'react';
import { useDash } from '../lib/DashContext.js';
import EChart, { echarts } from '../components/EChart.jsx';
import DataTable from '../components/DataTable.jsx';
import Row from '../components/Row.jsx';
import { CountUp, PageLayout, Seg } from '../components/ui.jsx';
import { ax, emptyOption, tipRow } from '../lib/chartBase.js';
import { nf, pct, scope } from '../lib/engine.js';
import { ISL, CATS, CAT_S, C_ISL, C_CAT, INK, INK2, GRID, SURF, THEME, SERIES, HEAT, POL, MONTHS } from '../lib/constants.js';

const H24 = [...Array(24).keys()];
const DOW = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu'];
const MONTH_F = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'];
const hh = h => String(h).padStart(2, '0') + '.00';
const joinId = a => a.length <= 1 ? a.join('') : a.slice(0, -1).join(', ') + ' dan ' + a[a.length - 1];

export default function Kritis() {
  const { E, F, agg, ui, setUi, openStation } = useDash();
  const sts = useMemo(() => scope(E, F), [E, F]);
  const per = F.st.size >= 1 && F.st.size <= 6;

  const [diurOpt, diurSub] = useMemo(() => {
    const groups = per ? sts.map((s, k) => ({ name: s.station, color: SERIES[k % 8], m: [s] }))
      : CATS.filter(c => F.cat.has(c)).map(c => ({ name: CAT_S[c], color: C_CAT[c], m: sts.filter(s => s.site_category === c) })).filter(g => g.m.length);
    const ser = groups.map(g => ({ name: g.name, type: 'line', symbol: 'none', smooth: 0.25, lineStyle: { width: 2.4, color: g.color }, itemStyle: { color: g.color }, emphasis: { focus: 'series' },
      data: H24.map(h => { const v = g.m.map(s => (E.D.diurnal[s.station] || {})[ui.diur]).filter(Boolean).map(a => a[h]).filter(x => x != null); return v.length ? +(v.reduce((a, b) => a + b, 0) / v.length).toFixed(2) : null; }) }));
    if (!ser.length) return [emptyOption('Tidak ada data untuk filter ini'), ''];
    // morning and evening peak of the average profile (same definition as the analysis: 00–11 and 12–23)
    const avgH = H24.map(h => { const v = ser.map(x => x.data[h]).filter(x => x != null); return v.length ? v.reduce((a, b) => a + b, 0) / v.length : -Infinity; });
    const argmax = (a, b) => { let k = a; for (let h = a; h <= b; h++) if (avgH[h] > avgH[k]) k = h; return k; };
    const pk = [argmax(0, 11), argmax(12, 23)];
    ser[0].markArea = { silent: true, itemStyle: { color: THEME === 'dark' ? 'rgba(253,224,58,.08)' : 'rgba(253,224,58,.22)' }, data: [[{ xAxis: 7 }, { xAxis: 8 }], [{ xAxis: 18 }, { xAxis: 19 }]] };
    return [{
      grid: { left: 50, right: 16, top: 34, bottom: 34 }, legend: { top: 0, left: 0, itemWidth: 18, itemHeight: 3, textStyle: { fontSize: 11, color: INK2 } },
      tooltip: { trigger: 'axis', formatter: ps => `<b>Pukul ${String(ps[0].axisValue).padStart(2, '0')}.00</b>` + ps.filter(p => p.value != null).sort((a, b) => b.value - a.value).map(p => tipRow(p.color, p.seriesName, nf(p.value, ui.diur === 'co' ? 0 : 1) + ' µg/m³')).join('') },
      xAxis: ax({ type: 'category', data: H24, boundaryGap: false, name: 'Jam (WIB)', axisLabel: { color: INK2, fontSize: 11, interval: 2 } }),
      yAxis: ax({ type: 'value', name: `${POL[ui.diur]} (µg/m³)`, scale: true }), series: ser,
    }, <>{POL[ui.diur]} memuncak pada <b>pukul {hh(pk[0])}</b> pagi dan <b>pukul {hh(pk[1])} WIB</b> sore, bertepatan dengan jam sibuk (pita kuning).</>];
  }, [sts, ui.diur, per, F, E]);

  const [weekOpt, weekSub] = useMemo(() => {
    if (!sts.length) return [emptyOption('Tidak ada data untuk filter ini'), null];
    // each station: mean of its daily values per day of the week, then the average over stations
    const per = sts.map(s => {
      const a = E.D.daily[s.station][ui.week], sum = new Float64Array(7), n = new Int32Array(7);
      if (!a) return null;
      for (let i = 0; i < E.NDAYS; i++) if (agg.mask[i] && a[i] != null) { const d = (new Date(E.T0 + i * 864e5).getUTCDay() + 6) % 7; sum[d] += a[i]; n[d]++; }
      return Array.from(sum, (v, d) => n[d] >= 4 ? v / n[d] : null);
    }).filter(Boolean);
    const dow = DOW.map((_, d) => { const v = per.map(p => p[d]).filter(x => x != null); return v.length ? v.reduce((x, y) => x + y, 0) / v.length : null; });
    if (dow.every(v => v == null)) return [emptyOption('Tidak ada data untuk filter ini'), null];
    const avg = xs => { const v = xs.filter(x => x != null); return v.length ? v.reduce((x, y) => x + y, 0) / v.length : null; };
    const mwd = avg(dow.slice(0, 5)), mwe = avg(dow.slice(5)), d = ui.week === 'co' ? 0 : 1;
    const bar = (keep, c) => dow.map((v, k) => (keep(k) && v != null ? { value: +v.toFixed(2), itemStyle: { color: c, borderRadius: [6, 6, 0, 0] } } : null));
    return [{
      grid: { left: 56, right: 16, top: 40, bottom: 34 }, legend: { top: 0, left: 0, itemWidth: 12, itemHeight: 10, textStyle: { fontSize: 11, color: INK2 } },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: ps => { const p = ps.find(x => x.value != null); return p ? `<b>${p.name}</b>` + tipRow(p.color, POL[ui.week], nf(p.value, d) + ' µg/m³') : ''; } },
      xAxis: ax({ type: 'category', data: DOW, name: 'Hari', axisLabel: { color: INK2, fontSize: 11.5, interval: 0 } }),
      yAxis: ax({ type: 'value', name: `${POL[ui.week]} rata-rata harian (µg/m³)`, min: 0 }),
      series: [
        { name: 'Hari kerja (Senin–Jumat)', type: 'bar', barWidth: '56%', barGap: '-100%', itemStyle: { color: SERIES[0] }, data: bar(k => k < 5, SERIES[0]),
          label: { show: true, position: 'top', fontSize: 11.5, color: INK2, formatter: p => nf(p.value, d) },
          markLine: { symbol: 'none', silent: true, lineStyle: { type: 'dashed', color: INK2 }, label: { formatter: `Rata-rata hari kerja (${nf(mwd, d)})`, color: INK2, fontSize: 11, position: 'insideEndTop' }, data: [{ yAxis: +mwd.toFixed(2) }] } },
        { name: 'Akhir pekan (Sabtu–Minggu)', type: 'bar', barWidth: '56%', barGap: '-100%', itemStyle: { color: SERIES[1] }, data: bar(k => k >= 5, SERIES[1]),
          label: { show: true, position: 'top', fontSize: 11.5, color: INK2, formatter: p => nf(p.value, d) } },
      ],
    }, mwd && mwe != null ? (Math.abs(mwe / mwd - 1) < 0.05
      ? <>Rata-rata {POL[ui.week]} pada akhir pekan hanya berselisih <b>{pct(Math.abs(mwe / mwd - 1) * 100, 1)}</b> dari hari kerja ({per.length} stasiun), sehingga tidak terdapat perbedaan berarti antara keduanya.</>
      : <>Rata-rata {POL[ui.week]} pada akhir pekan {mwe > mwd ? 'lebih tinggi' : 'lebih rendah'} <b>{pct(Math.abs(mwe / mwd - 1) * 100, 1)}</b> dibandingkan hari kerja ({per.length} stasiun).</>) : null];
  }, [sts, ui.week, agg, E]);

  const [heatOpt, heatSub, heatRows] = useMemo(() => {
    const hs = sts.map(s => ({ s, m: agg.stMean(s.station, ui.heat) })).filter(x => x.m.ok).sort((a, b) => b.m.mean - a.m.mean);
    const cells = [];
    hs.forEach((x, r) => {
      const d = E.D.daily[x.s.station], hsum = d['hs_' + ui.heat], hn = d['hn_' + ui.heat], sum = new Float64Array(12), n = new Int32Array(12);
      for (let i = 0; i < E.NDAYS; i++) if (agg.mask[i] && hn[i] > 0 && hsum[i] != null) { sum[E.DAY_M[i]] += hsum[i]; n[E.DAY_M[i]] += hn[i]; }
      for (let m = 0; m < 12; m++) if (n[m]) cells.push([m, r, +(sum[m] / n[m]).toFixed(1)]);
    });
    if (!cells.length) return [emptyOption('Tidak ada data untuk filter ini'), '', []];
    const hot = cells.reduce((b, c) => (!b || c[2] > b[2]) ? c : b, null);
    const sorted = cells.map(c => c[2]).sort((x, y) => x - y), top = Math.max(1, Math.ceil(sorted[Math.floor(0.95 * (sorted.length - 1))]));
    // stations whose highest month is August, September or October
    const peakAO = hs.filter((x, r) => { const mine = cells.filter(c => c[1] === r); const b = mine.reduce((p, c) => (!p || c[2] > p[2]) ? c : p, null); return b && b[0] >= 7 && b[0] <= 9; }).length;
    const lab = v => (v / top > 0.62) === (THEME !== 'dark') ? '#ffffff' : '#1b1b1b';
    return [{
      grid: { left: 70, right: 96, top: 20, bottom: 30 },
      tooltip: { trigger: 'item', formatter: p => `<b>${hs[p.value[1]].s.station}, ${MONTHS[p.value[0]]}</b><br>${tipRow(HEAT[HEAT.length - 2], POL[ui.heat], nf(p.value[2], 1) + ' µg/m³')}` },
      xAxis: ax({ type: 'category', data: MONTHS, name: 'Bulan', axisLine: { show: false } }),
      yAxis: ax({ type: 'category', data: hs.map(x => x.s.station), inverse: true, axisLine: { show: false } }),
      visualMap: { min: 0, max: top, dimension: 2, calculable: true, orient: 'vertical', right: 0, top: 'middle', itemHeight: 220, inRange: { color: HEAT }, textStyle: { color: INK2, fontSize: 11 }, text: ['µg/m³', ''], formatter: v => (v >= top ? '≥' : '') + nf(v, 0) },
      series: [{ type: 'heatmap', data: cells.map(c => ({ value: c, label: { color: lab(c[2]) } })), itemStyle: { borderColor: SURF, borderWidth: 1 },
        label: { show: true, fontSize: 11, formatter: p => nf(p.value[2], 0) }, emphasis: { itemStyle: { borderColor: INK, borderWidth: 1.5 } } }],
    }, <>Rata-rata bulanan {POL[ui.heat]} tertinggi tercatat di <b>{hs[hot[1]].s.station}</b> pada bulan <b>{MONTH_F[hot[0]]}</b> ({nf(hot[2], ui.heat === 'co' ? 0 : 1)} µg/m³).{peakAO ? <> Pada <b>{peakAO} dari {hs.length} stasiun</b>, bulan dengan rata-rata tertinggi jatuh pada Agustus hingga Oktober.</> : null}</>, hs];
  }, [sts, agg, ui.heat, E]);

  const codes = useMemo(() => new Set(sts.map(s => s.station)), [sts]);
  const [ganttOpt, ganttSub, eps, pk] = useMemo(() => {
    const eps = E.D.episodes.filter(e => codes.has(e.station) && E.idxOf(e.end) >= F.d0 && E.idxOf(e.start) <= F.d1);
    if (!eps.length) return [emptyOption('Tidak ada episode kabut asap pada filter ini'), '', [], null];
    const total = s => eps.filter(e => e.station === s).reduce((a, e) => a + e.days, 0);
    const rows = [...new Set(eps.map(e => e.station))].sort((a, b) => total(b) - total(a));
    const pk = eps.reduce((b, e) => (!b || e.pm25_peak_daily > b.pm25_peak_daily) ? e : b, null);
    return [{
      grid: { left: 70, right: 20, top: 30, bottom: 50 }, legend: { top: 0, left: 0, data: ISL.filter(i => eps.some(e => e.island === i)), textStyle: { fontSize: 11, color: INK2 } },
      tooltip: { trigger: 'item', formatter: p => { const e = p.data.e, c = C_ISL[e.island]; return `<b>${e.station}, ${e.start} s.d. ${e.end} (${e.days} hari)</b>` + tipRow(c, 'PM2.5 rata-rata', nf(e.pm25_mean, 0) + ' µg/m³') + tipRow(c, 'Puncak harian', nf(e.pm25_peak_daily, 0) + ' µg/m³') + tipRow(c, 'CO rata-rata', nf(e.co_mean, 0) + ' µg/m³') + tipRow(c, 'ISPU maksimum', nf(e.ispu_max, 0)); } },
      xAxis: ax({ type: 'time', name: 'Tanggal', min: E.T0 + F.d0 * 864e5, max: E.T0 + (F.d1 + 1) * 864e5, axisLabel: { color: INK2, fontSize: 11, formatter: v => { const d = new Date(v); return `${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`; } } }),
      yAxis: ax({ type: 'category', data: rows, axisLine: { show: false }, splitLine: { show: false } }),
      dataZoom: [{ type: 'inside', xAxisIndex: 0, filterMode: 'weakFilter' }, { type: 'slider', xAxisIndex: 0, height: 18, bottom: 8, filterMode: 'weakFilter', borderColor: GRID }],
      series: ISL.map(i => ({ name: i, type: 'custom', itemStyle: { color: C_ISL[i] }, encode: { x: [1, 2], y: 0 },
        renderItem: (params, api) => {
          const y = api.value(0), a = api.coord([api.value(1), y]), b = api.coord([api.value(2), y]), h = api.size([0, 1])[1] * 0.62;
          const shape = echarts.graphic.clipRectByRect({ x: a[0], y: a[1] - h / 2, width: Math.max(b[0] - a[0], 2), height: h }, { x: params.coordSys.x, y: params.coordSys.y, width: params.coordSys.width, height: params.coordSys.height });
          return shape && { type: 'rect', shape: Object.assign(shape, { r: 3 }), style: api.style() };
        },
        data: eps.filter(e => e.island === i).map(e => ({ value: [rows.indexOf(e.station), Date.parse(e.start + 'T00:00:00Z'), Date.parse(e.end + 'T00:00:00Z') + 864e5], e })) })),
    }, <>Terdapat <b>{eps.length} kejadian kabut asap</b> dengan total {nf(eps.reduce((a, e) => a + e.days, 0), 0)} hari-stasiun, seluruhnya di {joinId(ISL.filter(i => eps.some(e => e.island === i)))}. PM2.5 harian tertinggi mencapai <b>{nf(pk.pm25_peak_daily, 0)} µg/m³</b> di {pk.station} ({E.fmtDay(E.idxOf(pk.start))} hingga {E.fmtDay(E.idxOf(pk.end))}).</>, eps, pk];
  }, [codes, F, E]);

  const crit = useMemo(() => E.D.critical.map((r, i) => ({ ...r, rank: i + 1 })).filter(r => codes.has(r.station)), [E, codes]);
  const heatClick = useMemo(() => ({ click: p => { const r = heatRows[p.value?.[1] ?? p.data?.value?.[1]]; if (r) openStation(r.s.station); } }), [heatRows, openStation]);
  const ganttClick = useMemo(() => ({ click: p => p.data?.e && openStation(p.data.e.station) }), [openStation]);

  const days = eps.reduce((a, e) => a + e.days, 0);
  const tiles = [
    { icon: 'clock', l: 'Jam puncak', v: '07.00', u: 'WIB' },
    { icon: 'flame', l: 'Kejadian kabut asap', v: <CountUp value={eps.length} format={v => nf(v, 0)} />, tone: eps.length ? 'alert' : 'ok' },
    { icon: 'alert', l: 'PM2.5 harian tertinggi', v: pk ? <CountUp value={pk.pm25_peak_daily} format={v => nf(v, 0)} /> : '–', u: pk ? 'µg/m³' : '', tone: pk ? 'alert' : '' },
    { icon: 'calendar', l: 'Bulan kritis', v: 'Agu–Okt' },
  ];
  const sel = (id, items) => <Seg id={id} items={items} value={ui[id]} onChange={v => setUi(id, v)} label="Polutan" />;

  return (
    <PageLayout icon="clock" kicker="Tujuan 2" title="Identifikasi waktu dan wilayah" tiles={tiles} findings={[diurSub || null, weekSub, heatSub || null, ganttSub || null]}>
      <Row eager id="pola" title="Pola waktu" height={420} slides={[
        { key: 'jam', label: 'Pola per jam', controls: sel('diur', [['pm25', 'PM2.5'], ['no2', 'NO₂'], ['co', 'CO'], ['o3', 'O₃']]), caption: diurSub,
          content: () => <EChart option={diurOpt} height={420} ariaLabel="Pola per jam" /> },
        { key: 'pekan', label: 'Hari kerja dan akhir pekan', controls: sel('week', [['no2', 'NO₂'], ['pm25', 'PM2.5']]), caption: weekSub,
          content: () => <EChart option={weekOpt} height={420} ariaLabel="Hari kerja vs akhir pekan" /> },
        { key: 'bulan', label: 'Pola per bulan', controls: sel('heat', Object.entries(POL)), caption: heatSub,
          content: () => <EChart option={heatOpt} height={600} onEvents={heatClick} ariaLabel="Heatmap stasiun per bulan" /> },
      ]} />
      <Row id="wilayah" title="Wilayah kritis" height={440} slides={[
        { key: 'episode', label: 'Kejadian kabut asap', caption: ganttSub,
          content: () => <EChart option={ganttOpt} height={440} onEvents={ganttClick} ariaLabel="Linimasa episode kabut asap" /> },
        { key: 'kritis', label: 'Peringkat wilayah kritis', caption: '',
          content: () => <DataTable scroll rows={crit} sortKey="rank" dir={1} rowKey={r => r.station} onRowClick={r => openStation(r.station)} cols={[
            { key: 'rank', label: '#', num: true }, { key: 'station', label: 'Stasiun' }, { key: 'provinsi', label: 'Provinsi' },
            { key: 'critical_score', label: 'Skor', num: true, render: r => nf(r.critical_score, 0) }, { key: 'pm25_mean', label: 'PM2.5', num: true, render: r => nf(r.pm25_mean, 1) },
            { key: 'days_ispu_tidak_sehat_plus', label: 'Hari TS+', num: true, render: r => nf(r.days_ispu_tidak_sehat_plus, 0) },
          ]} /> },
        { key: 'kawasan', label: 'Karakteristik kawasan', caption: '',
          content: () => <DataTable rows={E.D.catprof.filter(r => F.cat.has(r.site_category))} sortKey="pm25" dir={-1} rowKey={r => r.site_category} cols={[
            { key: 'site_category', label: 'Tipe lokasi', render: r => <span className="nowrap"><i className="dot-i" style={{ background: C_CAT[r.site_category] }} />{CAT_S[r.site_category]}</span> },
            { key: 'n_stasiun', label: 'Stasiun', num: true }, { key: 'pm25', label: 'PM2.5', num: true, render: r => nf(r.pm25, 1) },
            { key: 'no2', label: 'NO₂', num: true, render: r => nf(r.no2, 1) }, { key: 'co', label: 'CO', num: true, render: r => nf(r.co, 0) },
            { key: 'pct_hari_lewat_bm24jam_pm25', label: '% hari > BM 24 jam', num: true, render: r => pct(r.pct_hari_lewat_bm24jam_pm25, 1) },
            { key: 'kemarau_vs_hujan_pm25_pct', label: 'Kemarau vs hujan', num: true, render: r => pct(r.kemarau_vs_hujan_pm25_pct, 0, true) },
            { key: 'hari_kabut_asap_per_stasiun', label: 'Hari kabut / stasiun', num: true, render: r => nf(r.hari_kabut_asap_per_stasiun, 0) },
          ]} /> },
      ]} />
    </PageLayout>
  );
}
