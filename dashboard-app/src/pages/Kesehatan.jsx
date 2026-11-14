import { useEffect, useMemo } from 'react';
import { useDash } from '../lib/DashContext.js';
import EChart from '../components/EChart.jsx';
import DataTable from '../components/DataTable.jsx';
import Row from '../components/Row.jsx';
import { CountUp, PageLayout, Seg, Tag } from '../components/ui.jsx';
import { ax, emptyOption, sparseLine, tipRow } from '../lib/chartBase.js';
import { nf, pct, inScope } from '../lib/engine.js';
import { ISL, C_ISL, INK2, MUTED, AXIS, GRID, THEME, SERIES, OUT, OUT_FULL, C_OUT, MONTHS, FONT } from '../lib/constants.js';

const HZ = () => THEME === 'dark' ? 'rgba(230,103,103,.14)' : 'rgba(227,73,72,.10)';
const BANDS = ['Baik (≤15,5)', 'Sedang (15,5–55,4)', 'Tidak Sehat (55,4–150,4)', 'Sangat Tidak Sehat (150,4–250,4)', 'Berbahaya (>250,4)'];

export default function Kesehatan() {
  const { E, F, agg, ui, setUi } = useDash();
  const out = ui.out;
  const hosps = useMemo(() => E.HOSP.filter(h => E.SM[h.station] && inScope(F, E.SM[h.station], true)), [E, F]);
  useEffect(() => {
    if (F.st.size === 1) { const h = E.HOSP.find(x => x.station === [...F.st][0]); if (h && h.id !== ui.hosp) setUi('hosp', h.id); }
    else if (hosps.length && !hosps.some(h => h.id === ui.hosp)) setUi('hosp', hosps[0].id);
  }, [F, hosps, ui.hosp, E, setUi]);

  const [tsOpt, tsSub] = useMemo(() => {
    if (!hosps.length) return [emptyOption('Tidak ada RS pada filter ini'), ''];
    const h = ui.hosp, st = E.D.health[h].station, dd = E.D.daily[st] || {}, used = E.SM[st] && E.SM[st].used_in_analysis;
    // only the days inside the active filter; a spacer (-1) where the filter skips days (e.g. one season per year)
    const days = []; for (let i = F.d0; i <= F.d1; i++) if (agg.mask[i]) days.push(i);
    const seq = []; days.forEach((i, k) => { if (k && i - days[k - 1] > 1) seq.push(-1 - k); seq.push(i); });
    const lab = seq.map(i => (i < 0 ? '~' + i : E.DAY_S[i]));
    const pmRaw = seq.map(i => (i >= 0 && used && dd.pm25 && dd.pm25[i] != null ? dd.pm25[i] : null));
    const pm = sparseLine(pmRaw);
    const cs = seq.map(i => (i >= 0 ? E.D.health[h][out][i] : null));
    const ma = seq.map(i => { if (i < 0) return null; const w = []; for (let j = i - 6; j <= i; j++) if (j >= 0 && agg.mask[j] && E.D.health[h][out][j] != null) w.push(E.D.health[h][out][j]); return w.length >= 4 ? +(w.reduce((a, b) => a + b, 0) / w.length).toFixed(2) : null; });
    const areas = [];
    if (used) { let s0 = null; seq.forEach((i, k) => { const on = i >= 0 && dd.haze[i] === 1; if (on && s0 == null) s0 = k; if ((!on || k === seq.length - 1) && s0 != null) { areas.push([{ xAxis: lab[s0] }, { xAxis: lab[on ? k : k - 1] }]); s0 = null; } }); }
    const tc = cs.reduce((a, b) => a + (b || 0), 0), nPm = pmRaw.filter(v => v != null).length;
    const sub = `${nf(tc, 0)} kasus` + (used ? `; ${areas.length ? `${areas.length} episode kabut asap (area merah)` : 'tidak terdapat episode kabut asap'}; data PM2.5 tersedia pada ${nf(nPm, 0)} dari ${nf(days.length, 0)} hari.` : '; stasiun pasangannya (JMB-02) rusak.');
    return [{
      grid: [{ left: 66, right: 24, top: 40, height: '34%' }, { left: 66, right: 24, top: '56%', height: '26%' }],
      legend: { top: 0, left: 0, textStyle: { fontSize: 11, color: INK2 } },
      tooltip: { trigger: 'axis', axisPointer: { link: [{ xAxisIndex: 'all' }] }, formatter: ps => ps[0].axisValue[0] === '~' ? '' : `<b>${E.fmtDay(E.idxOf(ps[0].axisValue))}</b>` + ps.filter(p => p.value != null).map(p => tipRow(p.color, p.seriesName, nf(p.value, p.seriesName.startsWith('PM') || p.seriesName.includes('7 hari') ? 1 : 0))).join('') },
      axisPointer: { link: [{ xAxisIndex: 'all' }] },
      xAxis: [ax({ type: 'category', data: lab, gridIndex: 0, axisLabel: { show: false }, boundaryGap: false }),
        ax({ type: 'category', data: lab, gridIndex: 1, boundaryGap: false, name: 'Tanggal', axisLabel: { color: INK2, fontSize: 11, formatter: v => (v[0] === '~' ? '' : `${MONTHS[+v.slice(5, 7) - 1]} ${v.slice(0, 4)}`) } })],
      yAxis: [ax({ type: 'value', gridIndex: 0, name: 'PM2.5 harian (µg/m³)' }), ax({ type: 'value', gridIndex: 1, name: 'Kasus per hari' })],
      dataZoom: [{ type: 'inside', xAxisIndex: [0, 1] }, { type: 'slider', xAxisIndex: [0, 1], height: 18, bottom: 6, borderColor: GRID }],
      series: [
        { name: 'PM2.5 harian', type: 'line', xAxisIndex: 0, yAxisIndex: 0, symbol: 'none', showAllSymbol: true, lineStyle: { width: 1.5, color: SERIES[0] }, itemStyle: { color: SERIES[0] }, data: pm,
          markArea: { silent: true, itemStyle: { color: HZ() }, data: areas },
          markLine: { symbol: 'none', silent: true, lineStyle: { type: 'dashed', color: INK2 }, label: { formatter: 'Baku mutu 24 jam PM2.5 (55 µg/m³)' }, data: [{ yAxis: 55 }] } },
        { name: OUT[out] + ' (harian)', type: 'line', xAxisIndex: 1, yAxisIndex: 1, symbol: 'none', lineStyle: { width: 1, color: C_OUT[out], opacity: 0.4 }, itemStyle: { color: C_OUT[out] }, data: cs,
          markArea: { silent: true, itemStyle: { color: HZ() }, data: areas } },
        { name: OUT[out] + ' (rata-rata 7 hari)', type: 'line', xAxisIndex: 1, yAxisIndex: 1, symbol: 'none', lineStyle: { width: 2.4, color: C_OUT[out] }, itemStyle: { color: C_OUT[out] }, data: ma },
      ],
    }, sub];
  }, [E, F, agg, hosps, ui.hosp, out]);

  const [lagOpt, lagSub, lag0, cum] = useMemo(() => {
    const lg = E.D.dlm.filter(r => r.outcome === out);
    const lags = lg.filter(r => r.lag !== 'kumulatif 0-7').sort((a, b) => +a.lag - +b.lag), cum = lg.find(r => r.lag === 'kumulatif 0-7');
    return [{
      grid: { left: 56, right: 20, top: 20, bottom: 36 },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: ps => { const r = lags[ps[0].dataIndex]; return `<b>Lag ${r.lag} hari</b>` + tipRow(C_OUT[out], '% kenaikan', pct(r.pct_increase_per10, 2, true)) + tipRow(AXIS, '95% CI', `${nf(r.pct_low, 1)} s.d. ${nf(r.pct_high, 1)}%`) + tipRow(AXIS, 'p', r.p_value < 0.001 ? '< 0,001' : nf(r.p_value, 3)); } },
      xAxis: ax({ type: 'category', data: lags.map(r => 'Lag ' + r.lag), name: 'Hari setelah paparan' }), yAxis: ax({ type: 'value', name: 'Kenaikan kasus per +10 µg/m³ (%)' }),
      series: [{ type: 'bar', barWidth: '52%', data: lags.map((r, k) => ({ value: +r.pct_increase_per10.toFixed(2), itemStyle: { color: k === 0 ? C_OUT[out] : AXIS, borderRadius: 5 } })),
        label: { show: true, position: 'top', fontSize: 11, color: INK2, formatter: p => p.dataIndex === 0 ? pct(p.value, 1, true) : '' },
        markLine: { symbol: 'none', silent: true, lineStyle: { color: INK2 }, label: { show: false }, data: [{ yAxis: 0 }] } },
      { type: 'custom', name: '95% CI', encode: { x: 0, y: [1, 2] }, z: 10, data: lags.map((r, k) => [k, r.pct_low, r.pct_high]),
        renderItem: (p, api) => { const x = api.value(0), lo = api.coord([x, api.value(1)]), hi = api.coord([x, api.value(2)]), w = 5, st = { stroke: INK2, lineWidth: 1.2 };
          return { type: 'group', children: [{ type: 'line', shape: { x1: lo[0], y1: lo[1], x2: hi[0], y2: hi[1] }, style: st }, { type: 'line', shape: { x1: lo[0] - w, y1: lo[1], x2: lo[0] + w, y2: lo[1] }, style: st }, { type: 'line', shape: { x1: hi[0] - w, y1: hi[1], x2: hi[0] + w, y2: hi[1] }, style: st }] }; } }],
    }, '', lags[0], cum];
  }, [E, out]);

  const bandOpt = useMemo(() => {
    const showO = [...new Set([out, 'resp_admissions_under5', 'resp_admissions_over60', 'cvd', 'death'])];
    const get = (o, b) => E.D.band.find(x => x.outcome === OUT_FULL[o] && x.band === b);
    return {
      grid: { left: 50, right: 16, top: 34, bottom: 50 }, legend: { top: 0, left: 0, textStyle: { fontSize: 11, color: INK2 } },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: ps => `<b>${ps[0].axisValue.replace('\n', ' ')}</b>` + ps.map(p => { const r = get(showO[p.seriesIndex], BANDS[p.dataIndex]); return tipRow(p.color, p.seriesName, `${nf(p.value, 2)}× (${nf(r.RR_low, 2)}–${nf(r.RR_high, 2)})`); }).join('') },
      xAxis: ax({ type: 'category', data: BANDS.map(b => b.replace(' (', '\n(')), name: 'Kategori ISPU PM2.5 (µg/m³)', nameGap: 46, axisLabel: { color: INK2, fontSize: 11, interval: 0 } }),
      yAxis: ax({ type: 'value', name: 'Risiko relatif (×)', min: 0 }),
      series: showO.map((o, k) => ({ name: OUT[o], type: 'bar', barGap: '8%', itemStyle: { color: C_OUT[o], borderRadius: [4, 4, 0, 0] }, emphasis: { focus: 'series' },
        data: BANDS.map(b => { const r = get(o, b); return r ? +r.RR.toFixed(3) : null; }),
        markLine: k === 0 ? { symbol: 'none', silent: true, lineStyle: { type: 'dashed', color: INK2 }, label: { formatter: 'Risiko relatif 1 = sama dengan hari Baik' }, data: [{ yAxis: 1 }] } : undefined })),
    };
  }, [E, out]);

  const [hzOpt, hzSub, hzPct] = useMemo(() => {
    const hz = agg.hazeStats(hosps.map(h => h.id));
    const hv = Object.keys(OUT).map(o => ({ o, v: hz.pct[o] })).filter(x => x.v != null).sort((a, b) => a.v - b.v);
    if (!hv.length) return [emptyOption('Tidak ada episode kabut asap pada filter ini'), '', null];
    return [{
      grid: { left: 110, right: 50, top: 14, bottom: 30 },
      tooltip: { trigger: 'item', formatter: p => `<b>${p.name}</b>` + tipRow(p.color, 'Kenaikan saat kabut asap', pct(p.value, 1, true)) },
      xAxis: ax({ type: 'value', name: 'Kenaikan kasus saat berkabut (%)', axisLabel: { formatter: '{value}%', color: INK2, fontSize: 11 } }), yAxis: ax({ type: 'category', data: hv.map(x => OUT[x.o]), axisLine: { show: false } }),
      series: [{ type: 'bar', barWidth: '60%', data: hv.map(x => ({ value: +x.v.toFixed(1), itemStyle: { color: C_OUT[x.o], borderRadius: [0, 5, 5, 0], opacity: x.o === out ? 1 : 0.55 } })),
        label: { show: true, position: 'right', fontSize: 11.5, color: INK2, formatter: p => pct(p.value, 0, true) } }],
    }, `Perbandingan kasus harian saat kabut asap dengan hari biasa (${hz.n} rumah sakit).`, hz.pct[out]];
  }, [agg, hosps, out]);

  const [atOpt, atSub, atT] = useMemo(() => {
    const at = E.D.attr.filter(r => r.outcome === OUT_FULL[out] && r.island !== 'Total' && F.isl.has(r.island)).sort((a, b) => a.attributable - b.attributable);
    const t = E.D.attr.find(r => r.outcome === OUT_FULL[out] && r.island === 'Total');
    return [{
      grid: { left: 90, right: 96, top: 14, bottom: 30 },
      tooltip: { trigger: 'item', formatter: p => { const r = at[p.dataIndex]; return `<b>${r.island}</b>` + tipRow(C_ISL[r.island], 'Kasus teratribusi', nf(r.attributable, 0)) + tipRow(C_ISL[r.island], '% dari total kasus', pct(r.attributable_pct, 1)); } },
      xAxis: ax({ type: 'value', name: 'Kasus akibat polusi' }), yAxis: ax({ type: 'category', data: at.map(r => r.island), axisLine: { show: false } }),
      series: [{ type: 'bar', barWidth: '58%', data: at.map(r => ({ value: Math.round(r.attributable), itemStyle: { color: C_ISL[r.island], borderRadius: [0, 5, 5, 0] } })),
        label: { show: true, position: 'right', fontSize: 11.5, color: INK2, formatter: p => `${nf(p.value, 0)} (${pct(at[p.dataIndex].attributable_pct, 0)})` } }],
    }, '', t];
  }, [E, F, out]);

  const vuln = useMemo(() => ['Semua RS', ...ISL].map(sc => {
    const g = E.D.vuln.filter(r => r.scope === sc), b = g.find(r => r.group.startsWith('ISPA balita')), l = g.find(r => r.group.startsWith('ISPA lansia')), q = g.find(r => r.group.startsWith('Rasio'));
    return b && l ? { scope: sc, n: b.n_hospitals, b: b.pct_increase_per10, l: l.pct_increase_per10, d: b.pct_increase_per10 - l.pct_increase_per10, z: q ? q.z_diff : null } : null;
  }).filter(Boolean), [E]);

  const tiles = [
    { icon: 'heart', l: 'Kenaikan per 10 µg/m³', v: <CountUp value={lag0.pct_increase_per10} format={v => pct(v, 1, true)} />, tone: 'alert' },
    { icon: 'activity', l: 'Efek kumulatif 7 hari', v: <CountUp value={cum.pct_increase_per10} format={v => pct(v, 1, true)} /> },
    { icon: 'flame', l: 'Kasus saat berkabut', v: hzPct == null ? '–' : <CountUp value={hzPct} format={v => pct(v, 0, true)} />, tone: hzPct > 0 ? 'alert' : '' },
    { icon: 'users', l: 'Kasus akibat PM2.5', v: <CountUp value={atT.attributable} format={v => nf(v, 0)} />, ring: atT.attributable_pct / 100 },
  ];

  return (
    <PageLayout icon="heart" kicker="Tujuan 4" title="Dampak terhadap kesehatan" tiles={tiles}
      actions={<><span className="lbl">Jenis Kasus</span><Seg id="out" items={Object.entries(OUT)} value={out} onChange={v => setUi('out', v)} label="Jenis kasus" /></>}>
      <Row eager id="paparan" title="Paparan dan kasus harian" height={540} slides={[
        { key: 'deret', label: 'Paparan dan kasus harian', caption: tsSub,
          controls: <select className="hsel" value={ui.hosp} onChange={e => setUi('hosp', e.target.value)} aria-label="Pilih rumah sakit">
            {hosps.map(h => <option key={h.id} value={h.id}>{h.id}, {h.name} (stasiun {h.station})</option>)}
          </select>,
          content: () => <EChart option={tsOpt} height={540} ariaLabel="PM2.5 dan kasus harian" /> },
        { key: 'kabut', label: 'Kenaikan kasus saat berkabut', caption: hzSub,
          content: () => <EChart option={hzOpt} height={400} ariaLabel="Kenaikan kasus saat kabut asap" /> },
      ]} />
      <Row id="efek" title="Besar efek PM2.5" height={400} slides={[
        { key: 'lag', label: 'Efek per hari jeda', caption: lagSub,
          content: () => <EChart option={lagOpt} height={400} ariaLabel="Efek per hari jeda" /> },
        { key: 'band', label: 'Risiko per kategori ISPU', caption: '',
          content: () => <EChart option={bandOpt} height={420} ariaLabel="Risiko relatif per kategori ISPU" /> },
        { key: 'atribusi', label: 'Kasus akibat PM2.5', caption: atSub,
          content: () => <EChart option={atOpt} height={400} ariaLabel="Kasus teratribusi" /> },
        { key: 'rentan', label: 'Balita dan lansia', caption: '',
          content: () => <DataTable rows={vuln} rowKey={r => r.scope} cols={[
            { key: 'scope', label: 'Cakupan' }, { key: 'n', label: 'Jumlah RS', num: true },
            { key: 'b', label: 'ISPA balita', num: true, render: r => pct(r.b, 1, true) }, { key: 'l', label: 'ISPA lansia', num: true, render: r => pct(r.l, 1, true) },
            { key: 'd', label: 'Selisih (poin)', num: true, render: r => (r.d > 0 ? '+' : '') + nf(r.d, 2) },
            { key: 'z', label: 'Uji beda (z)', num: true, render: r => <span>{nf(r.z, 2)} {Math.abs(r.z) >= 1.96 ? <Tag kind="ok">signifikan</Tag> : <Tag>tidak signifikan</Tag>}</span> },
            { key: 'n', label: 'Catatan', render: r => r.n <= 2 ? 'Jumlah RS sedikit' : '' },
          ]} /> },
      ]} />
    </PageLayout>
  );
}
