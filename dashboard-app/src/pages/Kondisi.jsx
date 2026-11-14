import { useMemo } from 'react';
import { useDash } from '../lib/DashContext.js';
import EChart from '../components/EChart.jsx';
import DataTable from '../components/DataTable.jsx';
import Row from '../components/Row.jsx';
import { CountUp, PageLayout, Seg, Tag } from '../components/ui.jsx';
import { ax, emptyOption, tipRow } from '../lib/chartBase.js';
import { nf, pct, scope } from '../lib/engine.js';
import { ISL, C_ISL, CAT_S, ISPU_C, ISPU_L, INK2, MUTED, AXIS, GRID, SURF, SERIES, YEARS, POL, BM_Y, WHO_Y, BM_24, MONTHS, IKU_IDX } from '../lib/constants.js';

const MONTH_F = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'];

export default function Kondisi() {
  const { E, F, agg, ui, setUi, openStation } = useDash();
  const pol = ui.pol;
  const sts = useMemo(() => scope(E, F), [E, F]);

  const [rankOpt, rankCap] = useMemo(() => {
    const arr = sts.map(s => ({ s, m: agg.stMean(s.station, pol) })).filter(x => x.m.ok).sort((a, b) => a.m.mean - b.m.mean);
    if (!arr.length) return [emptyOption('Tidak ada data untuk filter ini'), ''];
    const bm = BM_Y[pol], who = WHO_Y[pol], top = arr[arr.length - 1];
    const ml = [];
    if (bm) ml.push({ xAxis: bm, lineStyle: { type: 'dashed', color: INK2 }, label: { formatter: `Baku mutu tahunan (${bm} µg/m³)` } });
    if (who) ml.push({ xAxis: who, lineStyle: { type: 'dotted', color: MUTED }, label: { formatter: `Pedoman WHO 2021 (${who} µg/m³)` } });
    const cap = <><b>{top.s.station}</b> ({top.s.kota_kabupaten}) mencatat {POL[pol]} rata-rata tertinggi, yaitu {nf(top.m.mean, pol === 'co' ? 0 : 1)} µg/m³.{bm ? <> Sebanyak <b>{arr.filter(x => x.m.mean > bm).length} dari {arr.length} stasiun</b> melampaui baku mutu tahunan ({bm} µg/m³).</> : null}</>;
    return [{
      grid: { left: 70, right: 56, top: 30, bottom: 30 },
      legend: { top: 0, left: 0, data: ISL.filter(i => F.isl.has(i)), itemWidth: 12, itemHeight: 10, textStyle: { fontSize: 11, color: INK2 } },
      tooltip: { trigger: 'item', formatter: p => { const s = E.SM[p.name.replace(' *', '')]; const m = agg.stMean(s.station, pol); return `<b>${s.station}</b>, ${s.kota_kabupaten}` + tipRow(C_ISL[s.island], POL[pol], nf(m.mean, 1) + ' µg/m³') + `<div style="color:${MUTED};font-size:11px;margin-top:4px">${CAT_S[s.site_category]}</div>`; } },
      xAxis: ax({ type: 'value', name: `${POL[pol]} rata-rata (µg/m³)` }),
      yAxis: ax({ type: 'category', data: arr.map(x => x.s.station + (x.s.completeness_pm25_pct < 75 ? ' *' : '')), axisLine: { show: false } }),
      series: [
        ...ISL.filter(i => F.isl.has(i)).map(i => ({ name: i, type: 'bar', stack: 's', itemStyle: { color: C_ISL[i] }, data: [] })),
        { name: POL[pol], type: 'bar', barWidth: '64%', data: arr.map(x => ({ value: +x.m.mean.toFixed(2), itemStyle: { color: C_ISL[x.s.island], borderRadius: [0, 6, 6, 0], opacity: x.s.completeness_pm25_pct < 75 ? 0.55 : 1 } })),
          label: { show: true, position: 'right', fontSize: 11.5, color: INK2, formatter: p => nf(p.value, pol === 'co' ? 0 : 1) },
          markLine: ml.length ? { symbol: 'none', silent: true, data: ml } : undefined },
      ],
    }, cap];
  }, [sts, agg, pol, F, E]);

  const ispuOpt = useMemo(() => {
    const ip = sts.map(s => { const c = agg.catCounts(s.station), t = c.reduce((a, b) => a + b, 0); return { s, c: c.map(x => t ? x / t * 100 : 0), t }; })
      .filter(x => x.t >= 10).sort((a, b) => (b.c[0] - a.c[0]) || (b.c[1] - a.c[1]));
    if (!ip.length) return emptyOption('Tidak ada data untuk filter ini');
    return {
      grid: { left: 62, right: 14, top: 34, bottom: 30 }, legend: { top: 0, left: 0, itemWidth: 12, itemHeight: 10, textStyle: { fontSize: 11, color: INK2 } },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: ps => `<b>${ps[0].name}</b>` + ps.map(p => tipRow(p.color, p.seriesName, pct(p.value, 1))).join('') },
      xAxis: ax({ type: 'value', max: 100, name: 'Porsi hari (%)', axisLabel: { formatter: '{value}%', color: INK2, fontSize: 11 } }),
      yAxis: ax({ type: 'category', inverse: true, data: ip.map(x => x.s.station), axisLine: { show: false } }),
      series: ISPU_L.map((l, k) => ({ name: l, type: 'bar', stack: 'a', barWidth: '64%', itemStyle: { color: ISPU_C[k], borderColor: SURF, borderWidth: 1 }, data: ip.map(x => +x.c[k].toFixed(2)) })),
    };
  }, [sts, agg]);

  const [trendOpt, trendCap] = useMemo(() => {
    const months = [], mIdx = {}, key = i => `${E.DAY_Y[i]}-${String(E.DAY_M[i] + 1).padStart(2, '0')}`;
    for (let i = 0; i < E.NDAYS; i++) if (agg.mask[i]) { const k = key(i); if (!(k in mIdx)) { mIdx[k] = months.length; months.push(k); } }
    const per = F.st.size >= 1 && F.st.size <= 6;
    const groups = per ? sts.map((s, k) => ({ name: s.station, color: SERIES[k % 8], m: [s] }))
      : ISL.filter(i => F.isl.has(i)).map(i => ({ name: i, color: C_ISL[i], m: sts.filter(s => s.island === i) })).filter(g => g.m.length);
    const series = groups.map(g => {
      const sum = new Float64Array(months.length), n = new Int32Array(months.length);
      g.m.forEach(s => { const a = E.D.daily[s.station][pol]; for (let i = 0; i < E.NDAYS; i++) if (agg.mask[i] && a[i] != null) { const k = mIdx[key(i)]; sum[k] += a[i]; n[k]++; } });
      return { name: g.name, type: 'line', smooth: 0.2, symbol: 'circle', symbolSize: 5, showSymbol: false, lineStyle: { width: 2.4, color: g.color }, itemStyle: { color: g.color },
        emphasis: { focus: 'series' }, data: Array.from(sum, (v, k) => n[k] ? +(v / n[k]).toFixed(1) : null) };
    });
    if (!months.length || !series.length) return [emptyOption('Tidak ada data untuk filter ini'), ''];
    let best = null; series.forEach(s => s.data.forEach((v, k) => { if (v != null && (!best || v > best.v)) best = { v, n: s.name, m: months[k] }; }));
    if (BM_24[pol]) series[0].markLine = { symbol: 'none', silent: true, lineStyle: { type: 'dashed', color: INK2 }, label: { formatter: `Baku mutu 24 jam (${BM_24[pol]} µg/m³)`, color: INK2, fontSize: 11, position: 'insideEndTop' }, data: [{ yAxis: BM_24[pol] }] };
    return [{
      grid: { left: 54, right: 24, top: 34, bottom: 64 }, legend: { top: 0, left: 0, itemWidth: 18, itemHeight: 3, textStyle: { fontSize: 11, color: INK2 } },
      tooltip: { trigger: 'axis', formatter: ps => { const m = ps[0].axisValue; return `<b>${MONTHS[+m.slice(5) - 1]} ${m.slice(0, 4)}</b>` + ps.filter(p => p.value != null).sort((a, b) => b.value - a.value).map(p => tipRow(p.color, p.seriesName, nf(p.value, 1) + ' µg/m³')).join(''); } },
      xAxis: ax({ type: 'category', data: months, boundaryGap: false, name: 'Bulan', nameGap: 44, axisLabel: { color: INK2, fontSize: 11, formatter: m => `${MONTHS[+m.slice(5) - 1]}\n${m.slice(0, 4)}` } }),
      yAxis: ax({ type: 'value', name: `${POL[pol]} (µg/m³)` }),
      dataZoom: [{ type: 'slider', height: 18, bottom: 8, borderColor: GRID, fillerColor: 'rgba(57,135,229,.14)' }],
      series,
    }, <>Rata-rata bulanan {POL[pol]} tertinggi terjadi di <b>{best.n}</b> pada <b>{MONTH_F[+best.m.slice(5) - 1]} {best.m.slice(0, 4)}</b> ({nf(best.v, pol === 'co' ? 0 : 1)} µg/m³).</>];
  }, [sts, agg, pol, F, E]);

  const codes = useMemo(() => new Set(sts.map(s => s.station)), [sts]);
  const ann = useMemo(() => E.D.annual.filter(r => r.year === ui.year && codes.has(r.station)), [E, ui.year, codes]);
  // value with a red dot when it exceeds the annual standard (explained in the card header)
  const pv = k => r => <span className="nowrap">{r['lolos_bm_' + k] === false && <i className="dot-i over" />}{nf(r[k + '_tahunan'], 1)}</span>;

  const yoyOpt = useMemo(() => {
    const yo = sts.filter(s => s.pm25_2024_jan_14okt != null).sort((a, b) => a.pm25_2026_jan_14okt - b.pm25_2026_jan_14okt);
    if (!yo.length) return emptyOption('Tidak ada data untuk filter ini');
    const YC = { 2024: YEARS[0], 2025: YEARS[1], 2026: YEARS[2] }, v = (s, y) => s['pm25_' + y + '_jan_14okt'];
    return {
      grid: { left: 84, right: 20, top: 30, bottom: 30 }, legend: { top: 0, left: 0, data: ['2024', '2025', '2026'], textStyle: { fontSize: 11, color: INK2 } },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: ps => { const s = E.SM[ps[0].name]; return `<b>${s.station}</b>, ${s.trend_overall} (${pct(s.chg_2024_2026_pct, 0, true)})` + [2024, 2025, 2026].map(y => tipRow(YC[y], String(y), nf(v(s, y), 1) + ' µg/m³')).join(''); } },
      xAxis: ax({ type: 'value', name: 'PM2.5 rata-rata 1 Jan–14 Okt (µg/m³)' }),
      yAxis: ax({ type: 'category', data: yo.map(s => s.station), axisLine: { show: false } }),
      series: [
        { type: 'custom', name: 'rentang', silent: true, encode: { x: [1, 2], y: 0 },
          renderItem: (p, api) => { const a = api.coord([api.value(1), api.value(0)]), b = api.coord([api.value(2), api.value(0)]); return { type: 'line', shape: { x1: a[0], y1: a[1], x2: b[0], y2: b[1] }, style: { stroke: AXIS, lineWidth: 2 } }; },
          data: yo.map((s, k) => [k, Math.min(v(s, 2024), v(s, 2025), v(s, 2026)), Math.max(v(s, 2024), v(s, 2025), v(s, 2026))]) },
        ...[2024, 2025, 2026].map(y => ({ name: String(y), type: 'scatter', symbolSize: 10, itemStyle: { color: YC[y], borderColor: SURF, borderWidth: 1.2 }, data: yo.map(s => +v(s, y).toFixed(1)) })),
      ],
    };
  }, [sts, E]);

  const click = useMemo(() => ({ click: p => { const c = (p.name || '').replace(' *', '').split(' ')[0]; if (E.SM[c]) openStation(c); } }), [E, openStation]);
  const t = useMemo(() => {
    const pm = sts.map(s => ({ s, m: agg.stMean(s.station, 'pm25') })).filter(x => x.m.ok);
    const pv = sts.map(s => agg.stMean(s.station, pol)).filter(m => m.ok);
    const isl = ISL.filter(i => F.isl.has(i)).map(i => { const xs = pm.filter(x => x.s.island === i); return { i, v: xs.length ? xs.reduce((a, x) => a + x.m.mean, 0) / xs.length : null }; })
      .filter(x => x.v != null).sort((a, b) => b.v - a.v)[0];
    return { n: pm.length, over: pm.filter(x => x.m.mean > 15).length, isl, worse: sts.filter(s => s.trend_overall === 'Memburuk').length,
      pmean: pv.length ? pv.reduce((a, m) => a + m.mean, 0) / pv.length : null };
  }, [sts, agg, pol, F]);
  const tiles = [
    { icon: 'alert', l: 'Melampaui baku mutu', v: <><CountUp value={t.over} format={v => nf(v, 0)} /><small>/ {t.n} stasiun</small></>, ring: t.n ? t.over / t.n : null, tone: t.over ? 'alert' : 'ok' },
    { icon: 'map', l: 'Pulau paling tercemar', v: t.isl ? t.isl.i : '–' },
    { icon: 'trend', l: 'Stasiun PM2.5 naik', v: <><CountUp value={t.worse} format={v => nf(v, 0)} /><small>/ {sts.length} stasiun</small></>, ring: sts.length ? t.worse / sts.length : null, tone: t.worse ? 'alert' : '' },
    { icon: 'gauge', l: 'Rata-rata', v: <CountUp value={t.pmean} format={v => nf(v, pol === 'co' ? 0 : 1)} />, u: 'µg/m³' },
  ];

  const ikuGap = ann.filter(r => r.lolos_bm_pm25 === false && IKU_IDX[r.IKU_kategori] === 0).length;
  const findings = [
    rankCap || null,
    trendCap || null,
    sts.length ? <>Sebanyak <b>{t.worse} dari {sts.length} stasiun</b> mengalami kenaikan PM2.5 dari 2024 ke 2026 (periode yang sama, 1 Januari hingga 14 Oktober).</> : null,
    ann.length ? <>IKU hanya dihitung dari NO₂ dan SO₂. Karena itu, {ikuGap ? <><b>{ikuGap} stasiun</b> yang melampaui baku mutu PM2.5 pada {ui.year} tetap berkategori IKU Baik atau Sangat Baik.</> : <>kategori IKU tidak mencerminkan tingkat PM2.5.</>}</> : null,
  ];

  return (
    <PageLayout icon="wind" kicker="Tujuan 1" title="Kualitas udara" tiles={tiles} findings={findings}
      actions={<><span className="lbl">Polutan</span><Seg id="pol" items={Object.entries(POL)} value={pol} onChange={v => setUi('pol', v)} label="Polutan" /></>}>
      <Row eager id="tingkat" title="Tingkat pencemaran" height={620} slides={[
        { key: 'rank', label: 'Peringkat stasiun', caption: rankCap,
          content: () => <EChart option={rankOpt} height={620} onEvents={click} ariaLabel="Peringkat stasiun" /> },
        { key: 'ispu', label: 'Kategori ISPU per stasiun', caption: '',
          content: () => <EChart option={ispuOpt} height={620} onEvents={click} ariaLabel="Kategori ISPU per stasiun" /> },
        { key: 'bm', label: 'Baku mutu dan IKU', controls: <><span className="key-dot"><i className="dot-i over" />Melampaui baku mutu tahunan</span><Seg id="year" items={[[2024, '2024'], [2025, '2025'], [2026, '2026']]} value={ui.year} onChange={v => setUi('year', v)} label="Tahun" /></>,
          caption: '',
          content: () => <DataTable scroll rows={ann} sortKey="pm25_tahunan" dir={-1} rowKey={r => r.station + r.year} onRowClick={r => openStation(r.station)} cols={[
            { key: 'station', label: 'Stasiun' },
            { key: 'pm25_tahunan', label: 'PM2.5 (15)', num: true, render: pv('pm25') }, { key: 'pm10_tahunan', label: 'PM10 (40)', num: true, render: pv('pm10') },
            { key: 'no2_tahunan', label: 'NO₂ (50)', num: true, render: pv('no2') }, { key: 'o3_tahunan', label: 'O₃ (35)', num: true, render: pv('o3') },
            { key: 'IKU', label: 'IKU (NO₂, SO₂)', num: true, render: r => nf(r.IKU, 1) }, { key: 'IKU_kategori', label: 'Kategori IKU', render: r => <Tag color={ISPU_C[IKU_IDX[r.IKU_kategori] ?? 1]}>{r.IKU_kategori}</Tag> },
            { key: 'kelengkapan_pct', label: 'Data', num: true, render: r => <span>{nf(r.kelengkapan_pct, 0)}%</span> },
          ]} /> },
      ]} />
      <Row id="tren" title="Kecenderungan" height={460} slides={[
        { key: 'bulanan', label: 'Tren bulanan', caption: trendCap,
          content: () => <EChart option={trendOpt} height={460} ariaLabel="Tren bulanan" /> },
        { key: 'tahun', label: 'Perbandingan 2024–2026', caption: '',
          content: () => <EChart option={yoyOpt} height={620} onEvents={click} ariaLabel="Perubahan tahunan" /> },
      ]} />
    </PageLayout>
  );
}
