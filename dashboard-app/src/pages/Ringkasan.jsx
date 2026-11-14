import { useMemo } from 'react';
import { useDash } from '../lib/DashContext.js';
import EChart from '../components/EChart.jsx';
import MapView from '../components/MapView.jsx';
import Row from '../components/Row.jsx';
import { CountUp, Legend, PageLayout } from '../components/ui.jsx';
import { ax, emptyOption, tipRow } from '../lib/chartBase.js';
import { nf, pct, pmClass, scope, inScope } from '../lib/engine.js';
import { ISL, C_ISL, ISPU_C, ISPU_L, INK2, MUTED, STROKE, SURF } from '../lib/constants.js';

export default function Ringkasan() {
  const { E, F, agg, openStation } = useDash();
  const sts = useMemo(() => scope(E, F), [E, F]);

  const k = useMemo(() => {
    const means = sts.map(s => ({ s, m: agg.stMean(s.station, 'pm25') })).filter(x => x.m.ok);
    const avg = means.length ? means.reduce((a, x) => a + x.m.mean, 0) / means.length : null;
    const cnt = [0, 0, 0, 0, 0]; let haze = 0;
    sts.forEach(s => { agg.catCounts(s.station).forEach((v, i) => { cnt[i] += v; }); const h = E.D.daily[s.station].haze; for (let i = 0; i < E.NDAYS; i++) if (agg.mask[i]) haze += h[i]; });
    const tot = cnt.reduce((a, b) => a + b, 0);
    const hosp = E.HOSP.filter(h => E.SM[h.station] && inScope(F, E.SM[h.station], true)).map(h => h.id);
    let u5 = 0; hosp.forEach(h => { const a = E.D.health[h].resp_admissions_under5; for (let i = 0; i < E.NDAYS; i++) if (agg.mask[i] && a[i] != null) u5 += a[i]; });
    return { means, avg, cnt, tot, haze, u5, hz: agg.hazeStats(hosp), unhealthy: tot ? (cnt[2] + cnt[3] + cnt[4]) / tot * 100 : null };
  }, [E, F, agg, sts]);

  const tiles = [
    { icon: 'gauge', l: 'Rata-rata PM2.5', v: <CountUp value={k.avg} format={v => nf(v, 1)} />, u: 'µg/m³', tone: k.avg > 15 ? 'alert' : 'ok' },
    { icon: 'alert', l: 'Persentase hari tidak sehat', v: <CountUp value={k.unhealthy} format={v => pct(v, 1)} />, ring: k.unhealthy / 100, tone: k.unhealthy > 10 ? 'alert' : '' },
    { icon: 'flame', l: 'Jumlah hari berkabut', v: <CountUp value={k.haze} format={v => nf(v, 0)} /> },
    { icon: 'hospital', l: 'Kasus ISPA balita', v: <CountUp value={k.u5} format={v => nf(v, 0)} /> },
  ];

  const markers = useMemo(() => sts.map(s => {
    const m = agg.stMean(s.station, 'pm25'), v = m.ok ? m.mean : null, c = pmClass(v);
    return { id: s.station, pos: [s.latitude_dd, s.longitude_dd], radius: v == null ? 5 : 5 + Math.sqrt(v) * 1.6,
      style: { color: STROKE, weight: 1, fillColor: c < 0 ? SURF : ISPU_C[c], fillOpacity: 0.9 },
      tip: `${s.station}, ${v == null ? '–' : nf(v, 1) + ' µg/m³'}`, onClick: () => openStation(s.station) };
  }), [sts, agg, openStation]);

  const [islOpt, islCap] = useMemo(() => {
    const isl = ISL.filter(i => F.isl.has(i)).map(i => { const xs = k.means.filter(x => x.s.island === i); return { i, v: xs.length ? xs.reduce((a, x) => a + x.m.mean, 0) / xs.length : null, n: xs.length }; })
      .filter(x => x.v != null).sort((a, b) => a.v - b.v);
    if (!isl.length) return [emptyOption('Tidak ada data untuk filter ini'), ''];
    return [{
      grid: { left: 96, right: 70, top: 20, bottom: 30 },
      tooltip: { trigger: 'item', formatter: p => tipRow(C_ISL[p.name], p.name, nf(p.value, 1) + ' µg/m³') + `<div style="color:${MUTED};font-size:11px;margin-top:4px">${isl.find(x => x.i === p.name).n} stasiun</div>` },
      xAxis: ax({ type: 'value', name: 'PM2.5 rata-rata (µg/m³)' }), yAxis: ax({ type: 'category', data: isl.map(x => x.i), axisLine: { show: false }, axisLabel: { color: INK2, fontSize: 12 } }),
      series: [{ type: 'bar', barWidth: '56%', data: isl.map(x => ({ value: +x.v.toFixed(1), itemStyle: { color: C_ISL[x.i], borderRadius: [0, 8, 8, 0] } })),
        label: { show: true, position: 'right', color: INK2, fontSize: 12, formatter: p => nf(p.value, 1) },
        markLine: { symbol: 'none', silent: true, lineStyle: { color: INK2, type: 'dashed' }, label: { formatter: 'Baku mutu tahunan PM2.5 (15 µg/m³)' }, data: [{ xAxis: 15 }] } }],
    }, isl.length > 1 ? <><b>{isl[isl.length - 1].i}</b> mencatat PM2.5 rata-rata tertinggi ({nf(isl[isl.length - 1].v, 1)} µg/m³), sedangkan <b>{isl[0].i}</b> terendah ({nf(isl[0].v, 1)} µg/m³).</> : null];
  }, [k, F]);

  const ispuOpt = useMemo(() => {
    if (!k.tot) return emptyOption('Tidak ada data untuk filter ini');
    const rows = ISL.filter(i => F.isl.has(i)).map(i => {
      const c = [0, 0, 0, 0, 0]; sts.filter(s => s.island === i).forEach(s => agg.catCounts(s.station).forEach((v, j) => { c[j] += v; }));
      const t = c.reduce((a, b) => a + b, 0); return { i, c: c.map(x => t ? x / t * 100 : 0), t };
    }).filter(r => r.t);
    rows.unshift({ i: 'Semua', c: k.cnt.map(x => x / k.tot * 100), t: k.tot });
    return {
      grid: { left: 96, right: 20, top: 34, bottom: 30 }, legend: { top: 0, left: 0, itemWidth: 12, itemHeight: 10, textStyle: { color: INK2, fontSize: 11 } },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: ps => `<b>${ps[0].name}</b>` + ps.map(p => tipRow(p.color, p.seriesName, pct(p.value, 1))).join('') },
      xAxis: ax({ type: 'value', max: 100, name: 'Porsi hari (%)', axisLabel: { formatter: '{value}%', color: INK2, fontSize: 11 } }),
      yAxis: ax({ type: 'category', data: rows.map(r => r.i).reverse(), axisLine: { show: false }, axisLabel: { color: INK2, fontSize: 12 } }),
      series: ISPU_L.map((l, j) => ({ name: l, type: 'bar', stack: 'a', barWidth: '58%', itemStyle: { color: ISPU_C[j], borderColor: SURF, borderWidth: 1 }, data: rows.map(r => +r.c[j].toFixed(2)).reverse() })),
    };
  }, [k, F, sts, agg]);

  const findings = k.avg == null ? [] : [
    <>Rata-rata PM2.5 seluruh stasiun <b>{nf(k.avg, 1)} µg/m³</b>, atau {nf(k.avg / 15, 1)} kali baku mutu tahunan (15 µg/m³). Sebanyak {k.means.filter(x => x.m.mean > 15).length} dari {k.means.length} stasiun berada di atas baku mutu tersebut.</>,
    islCap,
    <>Sebanyak <b>{pct(k.unhealthy, 1)}</b> hari-stasiun berada pada kategori ISPU Tidak Sehat atau lebih buruk, dan tercatat {nf(k.haze, 0)} hari-stasiun berkabut asap.</>,
  ];

  return (
    <PageLayout icon="home" kicker="Gambaran umum" title="Ringkasan kualitas udara" tiles={tiles} findings={findings}>
      <Row eager id="sebaran" title="Sebaran PM2.5" height={440} slides={[
        { key: 'peta', label: '', caption: '',
          content: () => <><MapView markers={markers} height={400} /><Legend items={ISPU_L.map((l, i) => [ISPU_C[i], l])} /></> },
        { key: 'pulau', label: 'PM2.5 per pulau', caption: islCap,
          content: () => <EChart option={islOpt} height={440} ariaLabel="PM2.5 per pulau" /> },
        { key: 'ispu', label: 'Kategori ISPU per pulau', caption: k.tot ? `${pct(k.unhealthy, 1)} hari-stasiun berada pada kategori Tidak Sehat atau lebih buruk.` : '',
          content: () => <EChart option={ispuOpt} height={440} ariaLabel="Komposisi kategori ISPU" /> },
      ]} />
    </PageLayout>
  );
}
