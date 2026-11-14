import { useMemo } from 'react';
import { useDash } from '../lib/DashContext.js';
import EChart from '../components/EChart.jsx';
import MapView from '../components/MapView.jsx';
import DataTable from '../components/DataTable.jsx';
import Row from '../components/Row.jsx';
import { Legend, PageLayout } from '../components/ui.jsx';
import { ax, emptyOption, tipRow } from '../lib/chartBase.js';
import { nf, scope } from '../lib/engine.js';
import { INK2, MUTED, AXIS, SURF, STROKE, SERIES, REL_C, REL_LABEL, CRIT } from '../lib/constants.js';

const W = { polusi: 0.25, kabut_asap: 0.20, beban_kesehatan: 0.20, defisit_data: 0.20, keterisolasian: 0.15 };
const WL = { polusi: 'Polusi', kabut_asap: 'Kabut asap', beban_kesehatan: 'Beban rumah sakit', defisit_data: 'Defisit data', keterisolasian: 'Keterisolasian' };
export default function Jaringan() {
  const { E, F, openStation } = useDash();
  const sts = useMemo(() => scope(E, F, true), [E, F]);

  const markers = useMemo(() => sts.map(s => ({
    id: s.station, pos: [s.latitude_dd, s.longitude_dd], radius: s.pm25_mean == null ? 6 : 5 + Math.sqrt(s.pm25_mean) * 1.4,
    style: { color: STROKE, weight: 1, fillColor: REL_C[s.reliability] || MUTED, fillOpacity: 0.92 },
    tip: `${s.station}, ${REL_LABEL[s.reliability] || s.reliability}`, onClick: () => openStation(s.station),
  })), [sts, openStation]);
  const lines = useMemo(() => E.D.gaps.filter(g => F.isl.has(g.island)).map(g => {
    const a = E.SM[g.station_a], b = E.SM[g.station_b], wide = g.jarak_km >= 300;
    return { pos: [[a.latitude_dd, a.longitude_dd], [b.latitude_dd, b.longitude_dd]], style: { color: wide ? CRIT : AXIS, weight: wide ? 2.2 : 1, dashArray: wide ? '6 6' : null, opacity: 0.9 }, tip: `${g.station_a} – ${g.station_b}: ${nf(g.jarak_km, 0)} km` };
  }), [E, F]);

  const [prioOpt, prio] = useMemo(() => {
    const pr = sts.filter(s => s.priority_score != null).sort((a, b) => a.priority_score - b.priority_score);
    if (!pr.length) return [emptyOption('Tidak ada stasiun pada filter ini'), []];
    const comp = s => { const ks = Object.keys(W).filter(k => s['komp_' + k] != null), ws = ks.reduce((a, k) => a + W[k], 0); return Object.fromEntries(Object.keys(W).map(k => [k, s['komp_' + k] == null ? 0 : s['komp_' + k] * W[k] / ws * 100])); };
    return [{
      grid: { left: 62, right: 30, top: 48, bottom: 30 }, legend: { top: 0, left: 0, itemWidth: 12, itemHeight: 10, textStyle: { fontSize: 11.5, color: INK2 } },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: ps => { const s = E.SM[ps[0].name]; return `<b>${s.station}, skor ${nf(s.priority_score, 1)}` + ps.map(p => tipRow(p.color, p.seriesName, nf(p.value, 1))).join('') + (s.komponen_tidak_tersedia ? `<div style="color:${MUTED};font-size:11px;margin-top:4px">Tanpa komponen: ${s.komponen_tidak_tersedia.replace(/_/g, ' ')}</div>` : ''); } },
      xAxis: ax({ type: 'value', max: 100, name: 'Skor prioritas (0–100)' }), yAxis: ax({ type: 'category', data: pr.map(s => s.station), axisLine: { show: false }, axisLabel: { interval: 0, color: INK2, fontSize: 11.5 } }),
      series: Object.keys(W).map((k, i) => ({ name: `${WL[k]} (${W[k] * 100}%)`, type: 'bar', stack: 'p', barWidth: '64%', itemStyle: { color: SERIES[i], borderColor: SURF, borderWidth: 1 }, emphasis: { focus: 'series' }, data: pr.map(s => +comp(s)[k].toFixed(2)) })),
    }, pr];
  }, [sts, E]);
  const prioClick = useMemo(() => ({ click: p => prio[p.dataIndex] && openStation(prio[p.dataIndex].station) }), [prio, openStation]);

  const gaps = E.D.gaps.filter(g => F.isl.has(g.island)).sort((a, b) => b.jarak_km - a.jarak_km);
  const cov = E.D.coverage.filter(r => F.isl.has(r.island));
  const tiles = [
    { icon: 'shield', l: 'Alat berfungsi baik', v: <>{sts.filter(s => s.reliability === 'Baik').length}<small>/ {sts.length}</small></>, ring: sts.length ? sts.filter(s => s.reliability === 'Baik').length / sts.length : null, tone: 'ok' },
    { icon: 'map', l: 'Jarak stasiun terjauh', v: gaps[0] ? nf(gaps[0].jarak_km, 0) : '–', u: gaps[0] ? 'km' : '', tone: gaps[0] && gaps[0].jarak_km >= 300 ? 'alert' : '' },
    { icon: 'target', l: 'Prioritas utama', v: prio.length ? prio[prio.length - 1].station : '–' },
    { icon: 'pin', l: 'Provinsi terpantau', v: cov.reduce((a, r) => a + r.n_provinsi_tercakup, 0) },
  ];

  return (
    <PageLayout icon="network" kicker="Tujuan 5" title="Jaringan pemantauan" tiles={tiles}>
      <Row eager id="jaringan" title="Sebaran stasiun" height={520} slides={[
        { key: 'peta', label: '', caption: '',
          content: () => <><MapView markers={markers} lines={lines} height={480} />
            <Legend items={[...Object.entries(REL_C).map(([k, c]) => [c, REL_LABEL[k] || k]), [CRIT, 'jarak ≥300 km', 'ln']]} /></> },
        { key: 'prioritas', label: 'Skor prioritas stasiun', caption: '',
          content: () => <EChart option={prioOpt} height={580} onEvents={prioClick} ariaLabel="Skor prioritas" /> },
        { key: 'cakupan', label: 'Cakupan per pulau', caption: '',
          content: () => <DataTable rows={cov} rowKey={r => r.island} cols={[
            { key: 'island', label: 'Pulau' }, { key: 'n_stasiun', label: 'Stasiun', num: true }, { key: 'n_stasiun_andal', label: 'Andal', num: true },
            { key: 'n_provinsi_tercakup', label: 'Provinsi', num: true }, { key: 'jarak_tetangga_median_km', label: 'Median jarak tetangga', num: true, render: r => nf(r.jarak_tetangga_median_km, 0) + ' km' },
            { key: 'celah_terlebar_km', label: 'Jarak terjauh', num: true, render: r => `${nf(r.celah_terlebar_km, 0)} km (${r.celah_terlebar_antara})` },
            { key: 'pm25_mean', label: 'PM2.5', num: true, render: r => nf(r.pm25_mean, 1) }, { key: 'hari_kabut_asap', label: 'Hari kabut', num: true, render: r => nf(r.hari_kabut_asap, 0) },
          ]} /> },
      ]} />
    </PageLayout>
  );
}
