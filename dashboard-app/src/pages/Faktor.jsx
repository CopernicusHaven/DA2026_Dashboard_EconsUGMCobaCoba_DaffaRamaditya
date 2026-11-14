import { useMemo } from 'react';
import { useDash } from '../lib/DashContext.js';
import EChart from '../components/EChart.jsx';
import Row from '../components/Row.jsx';
import { PageLayout, Seg } from '../components/ui.jsx';
import { ax, emptyOption, tipRow } from '../lib/chartBase.js';
import { nf, pct, scope } from '../lib/engine.js';
import { CATS, CAT_S, C_CAT, INK, INK2, MUTED, AXIS, SURF, SERIES, DIV, POL, SEKTOR } from '../lib/constants.js';

const PO = ['pm25', 'pm10', 'so2', 'co', 'o3', 'no2'], FA = ['temperature_c', 'humidity_pct', 'wind_speed_ms'], FL = ['Suhu', 'Kelembapan', 'Kecepatan angin'];

export default function Faktor() {
  const { E, F, ui, setUi, openStation } = useDash();
  const codes = useMemo(() => new Set(scope(E, F).map(s => s.station)), [E, F]);

  const impOpt = useMemo(() => {
    const imp = [...E.D.importance].sort((a, b) => a.importance - b.importance);
    return {
      grid: { left: 140, right: 50, top: 20, bottom: 30 },
      tooltip: { trigger: 'item', formatter: p => `<b>${p.name}</b>` + tipRow(SERIES[0], 'Porsi kepentingan', pct(imp[p.dataIndex].share_pct, 1)) + tipRow(SERIES[0], 'Penurunan R²', nf(p.value, 3)) },
      xAxis: ax({ type: 'value', name: 'Penurunan R² saat faktor diacak' }), yAxis: ax({ type: 'category', data: imp.map(r => r.group), axisLine: { show: false } }),
      series: [{ type: 'bar', barWidth: '60%', data: imp.map(r => ({ value: +r.importance.toFixed(4), itemStyle: { color: SERIES[0], opacity: r.share_pct >= 10 ? 1 : 0.45, borderRadius: [0, 6, 6, 0] } })),
        label: { show: true, position: 'right', fontSize: 11.5, color: INK2, formatter: p => pct(imp[p.dataIndex].share_pct, 0) } }],
    };
  }, [E]);

  const corrOpt = useMemo(() => ({
    grid: { left: 60, right: 80, top: 20, bottom: 30 },
    tooltip: { trigger: 'item', formatter: p => `<b>${POL[PO[p.value[1]]]} × ${FL[p.value[0]]}</b>` + tipRow(p.color, 'r rata-rata', nf(p.value[2], 2)) + `<div style="color:${MUTED};font-size:11px;margin-top:4px">|r| &gt; 0,3 di ${p.value[3]} dari ${p.value[4]} stasiun</div>` },
    xAxis: ax({ type: 'category', data: FL, name: 'Faktor cuaca', axisLine: { show: false } }), yAxis: ax({ type: 'category', data: PO.map(p => POL[p]), inverse: true, axisLine: { show: false } }),
    visualMap: { min: -0.5, max: 0.5, dimension: 2, calculable: true, right: 0, top: 'middle', itemHeight: 140, inRange: { color: DIV }, textStyle: { color: INK2, fontSize: 11 }, text: ['+', '−'] },
    series: [{ type: 'heatmap', data: E.D.meteo.map(r => [FA.indexOf(r.factor), PO.indexOf(r.pollutant), +r.r_rata2.toFixed(2), r.n_stasiun_abs_r_gt_0_3, r.n_stasiun]),
      itemStyle: { borderColor: SURF, borderWidth: 2 }, label: { show: true, color: INK, fontSize: 12, formatter: p => nf(p.value[2], 2) }, emphasis: { itemStyle: { borderColor: INK, borderWidth: 1.5 } } }],
  }), [E]);

  const [trafOpt, trafSub] = useMemo(() => {
    const t = ui.traf, pts = E.D.wet.filter(r => codes.has(r.station) && r[t] != null);
    const rho = E.D.sitefac.find(r => r.pollutant === t && r.factor === 'traffic_intensity_per_h');
    const sub = (rho.p_value < 0.05 && rho.spearman_r >= 0.5 ? `Semakin padat lalu lintas, semakin tinggi ${POL[t]}` : rho.p_value < 0.05 ? `Lalu lintas berkorelasi lemah dengan ${POL[t]}` : `Tidak ditemukan hubungan yang bermakna antara lalu lintas dan ${POL[t]}`) + ` (ρ = ${nf(rho.spearman_r, 2)}; ${rho.n_stasiun} stasiun).`;
    if (!pts.length) return [emptyOption('Tidak ada data untuk filter ini'), sub];
    const sz = d => 8 + 18 * (1 - (Math.log(d) - Math.log(6)) / (Math.log(250) - Math.log(6)));
    const keep = new Set([...[...pts].sort((a, b) => b[t] - a[t]).slice(0, 5), ...[...pts].sort((a, b) => b.traffic_intensity_per_h - a.traffic_intensity_per_h).slice(0, 3), ...[...pts].sort((a, b) => a[t] - b[t]).slice(0, 2)].map(r => r.station));
    return [{
      grid: { left: 56, right: 24, top: 34, bottom: 44 }, legend: { top: 0, left: 0, textStyle: { fontSize: 11, color: INK2 } },
      tooltip: { trigger: 'item', formatter: p => { const r = p.data.r; return `<b>${r.station}, ${CAT_S[r.site_category]}</b>` + tipRow(p.color, POL[t], nf(r[t], 1) + ' µg/m³') + tipRow(p.color, 'Lalu lintas', nf(r.traffic_intensity_per_h, 0) + ' kend/jam') + tipRow(p.color, 'Jarak ke jalan', nf(r.distance_to_road_m, 0) + ' m'); } },
      xAxis: ax({ type: 'value', name: 'Lalu lintas (kendaraan per jam)' }), yAxis: ax({ type: 'value', name: POL[t] + ' (µg/m³)', scale: true }),
      series: CATS.map(c => ({ name: CAT_S[c], type: 'scatter', itemStyle: { color: C_CAT[c], borderColor: SURF, borderWidth: 1.5, opacity: 0.95 }, emphasis: { focus: 'series', scale: 1.4 },
        data: pts.filter(r => r.site_category === c).map(r => ({ value: [r.traffic_intensity_per_h, r[t]], symbolSize: sz(r.distance_to_road_m), r })),
        label: { show: true, position: 'right', fontSize: 11.5, color: INK2, formatter: p => keep.has(p.data.r.station) ? p.data.r.station : '' } })).filter(s => s.data.length),
    }, sub];
  }, [E, codes, ui.traf]);

  const [windOpt, windRows] = useMemo(() => {
    const w = E.D.wind.filter(r => codes.has(r.station) && r.sector_ratio != null).map(r => ({ r, v: (r.sector_ratio - 1) * 100 })).sort((a, b) => a.v - b.v);
    if (!w.length) return [emptyOption('Tidak ada data untuk filter ini'), []];
    return [{
      grid: { left: 62, right: 96, top: 16, bottom: 30 },
      tooltip: { trigger: 'item', formatter: p => { const r = w[p.dataIndex].r; return `<b>${r.station}</b>` + tipRow(p.color, 'Terkotor: dari ' + SEKTOR[r.dirtiest_sector], nf(r.dirtiest_pm25, 1) + ' µg/m³') + tipRow(AXIS, 'Terbersih: dari ' + SEKTOR[r.cleanest_sector], nf(r.cleanest_pm25, 1) + ' µg/m³'); } },
      xAxis: ax({ type: 'value', name: 'Selisih PM2.5 arah terkotor vs terbersih (%)', axisLabel: { formatter: '{value}%', color: INK2, fontSize: 11 } }),
      yAxis: ax({ type: 'category', data: w.map(x => x.r.station), axisLine: { show: false }, axisLabel: { interval: 0, color: INK2, fontSize: 11.5 } }),
      series: [{ type: 'bar', barWidth: '64%', data: w.map(x => ({ value: +x.v.toFixed(1), itemStyle: { color: x.v >= 10 ? SERIES[0] : AXIS, borderRadius: [0, 5, 5, 0] } })),
        label: { show: true, position: 'right', fontSize: 11.5, color: INK2, formatter: p => `${pct(p.value, 0, true)} dari ${SEKTOR[w[p.dataIndex].r.dirtiest_sector]}` } }],
    }, w];
  }, [E, codes]);

  const trafClick = useMemo(() => ({ click: p => p.data?.r && openStation(p.data.r.station) }), [openStation]);
  const windClick = useMemo(() => ({ click: p => windRows[p.dataIndex] && openStation(windRows[p.dataIndex].r.station) }), [windRows, openStation]);

  const top = useMemo(() => [...E.D.importance].sort((a, b) => b.importance - a.importance)[0], [E]);
  const rho = E.D.sitefac.find(r => r.pollutant === 'pm25' && r.factor === 'traffic_intensity_per_h');
  const nWind = E.D.wind.filter(r => codes.has(r.station) && r.sector_ratio != null);
  const tiles = [
    { icon: 'cloud', l: 'Faktor utama', v: top.group.replace(' (bulan)', ''), ring: top.share_pct / 100 },
    { icon: 'target', l: 'Akurasi model (R²)', v: nf(E.D.meta.rf_r2, 2) },
    { icon: 'car', l: 'Korelasi lalu lintas', v: nf(rho.spearman_r, 2), tone: 'alert' },
    { icon: 'wind', l: 'Pengaruh arah angin', v: <>{nWind.filter(r => r.sector_ratio >= 1.1).length}<small>/ {nWind.length}</small></>, ring: nWind.length ? nWind.filter(r => r.sector_ratio >= 1.1).length / nWind.length : null },
  ];

  return (
    <PageLayout icon="sliders" kicker="Tujuan 3" title="Faktor penyebab" tiles={tiles}>
      <Row eager id="dominan" title="Faktor dominan" height={420} slides={[
        { key: 'imp', label: 'Tingkat kepentingan faktor', caption: '',
          content: () => <EChart option={impOpt} height={420} ariaLabel="Kepentingan faktor" /> },
        { key: 'cuaca', label: 'Korelasi dengan cuaca', caption: '',
          content: () => <EChart option={corrOpt} height={420} ariaLabel="Korelasi polutan dan cuaca" /> },
      ]} />
      <Row id="lokasi" title="Lokasi dan angin" height={520} slides={[
        { key: 'lalin', label: 'Lalu lintas dan polutan', controls: <Seg id="traf" items={[['pm25', 'PM2.5'], ['pm10', 'PM10'], ['no2', 'NO₂'], ['co', 'CO']]} value={ui.traf} onChange={v => setUi('traf', v)} label="Polutan" />,
          caption: trafSub,
          content: () => <EChart option={trafOpt} height={520} onEvents={trafClick} ariaLabel="Lalu lintas vs polutan" /> },
        { key: 'angin', label: 'Pengaruh arah angin', caption: 'Perbandingan PM2.5 saat angin bertiup dari arah terkotor dan terbersih.',
          content: () => <EChart option={windOpt} height={576} onEvents={windClick} ariaLabel="Pengaruh arah angin" /> },
      ]} />
    </PageLayout>
  );
}
