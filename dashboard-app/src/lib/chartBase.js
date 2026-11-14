import { FONT, INK, INK2, MUTED, GRID, AXIS, TIPBG, SURF, THEME } from './constants.js';

// axis style built at call time so it follows the active theme
export const ax = (o = {}) => Object.assign({
  axisLine: { lineStyle: { color: AXIS } }, axisTick: { show: false }, axisLabel: { color: INK2, fontSize: 11, fontFamily: FONT },
  splitLine: { lineStyle: { color: GRID, type: [4, 4] } }, nameTextStyle: { color: MUTED, fontSize: 11, fontFamily: FONT },
}, o);

export const tipRow = (color, label, value) =>
  `<div style="display:flex;gap:14px;align-items:center;justify-content:space-between;min-width:160px;line-height:18px;font-size:11px">` +
  `<span style="display:flex;gap:8px;align-items:center;color:${INK2}"><i style="width:7px;height:7px;border-radius:50%;background:${color};display:inline-block;flex:none"></i>${label}</span><span style="color:${INK}">${value}</span></div>`;

// reference lines (baku mutu, WHO, RR = 1) as a small legend under the chart
export function chartNotes(o) {
  const out = [], seen = new Set();
  [].concat((o && o.series) || []).forEach(x => {
    const ml = x && x.markLine; if (!ml) return;
    (ml.data || []).forEach(d => {
      const t = (d.label && d.label.formatter) || (ml.label && ml.label.formatter);
      if (typeof t !== 'string' || seen.has(t)) return;
      seen.add(t);
      const ls = { ...(ml.lineStyle || {}), ...(d.lineStyle || {}) };
      out.push({ text: t, type: ls.type || 'solid' });
    });
  });
  return out;
}

// Days without valid data stay empty (never filled). A valid day with empty neighbours would be
// invisible as a line, so it is drawn as a small dot.
export const sparseLine = vals => vals.map((v, i) => {
  if (v == null) return null;
  const lone = vals[i - 1] == null && vals[i + 1] == null;
  return lone ? { value: v, symbol: 'circle', symbolSize: 4 } : v;
});

export const emptyOption = msg => ({
  __empty: true,
  title: { text: msg, left: 'center', top: 'middle', textStyle: { color: MUTED, fontSize: 13, fontWeight: 400, fontFamily: FONT } },
  xAxis: [], yAxis: [], series: [],
});

// shared base: font, tooltip look, toolbox (table view + PNG), entry animation, layout guard
export function withBase(o, { narrow = false } = {}) {
  if (o.__empty) { const { __empty, ...rest } = o; return rest; }
  const dark = THEME === 'dark';
  const base = {
    backgroundColor: 'transparent',
    textStyle: { fontFamily: FONT, color: INK2 },
    animationDuration: 380, animationEasing: 'cubicOut', animationDurationUpdate: 320,
    toolbox: {
      right: 0, top: 0, itemSize: 15, itemGap: 10, iconStyle: { borderColor: AXIS }, emphasis: { iconStyle: { borderColor: INK } },
      feature: {
        dataView: { readOnly: true, title: 'Lihat tabel', lang: ['Data', 'Tutup', 'Muat ulang'], backgroundColor: SURF, textColor: INK,
          textareaColor: SURF, textareaBorderColor: GRID, buttonColor: '#2a78d6', buttonTextColor: '#ffffff' },
        saveAsImage: { title: 'Unduh PNG', pixelRatio: 2, backgroundColor: SURF },
      },
    },
    tooltip: {
      confine: true, backgroundColor: TIPBG, borderColor: dark ? 'rgba(255,255,255,.10)' : 'rgba(0,0,0,.08)',
      textStyle: { color: INK, fontSize: 11, fontFamily: FONT, lineHeight: 18 },
      extraCssText: `box-shadow:0 8px 24px rgba(0,0,0,${dark ? '.4' : '.10'});border-radius:10px;padding:10px 12px;`,
    },
  };
  const merged = Object.assign({}, base, o, { tooltip: Object.assign({}, base.tooltip, o.tooltip || {}) });
  if (o.toolbox === false || narrow) delete merged.toolbox;   // phones: no table/PNG icons crowding the legend
  const grids = Array.isArray(merged.grid) ? merged.grid : (merged.grid ? [merged.grid] : []);
  const yNamed = [].concat(merged.yAxis || []).some(y => y && y.name);
  if (grids[0] && typeof grids[0].top === 'number') {
    grids[0].top = Math.max(grids[0].top, merged.legend ? 40 : 16);
  }
  // nothing written on the plot itself: data labels off; reference-line labels are shown under the chart instead
  merged.series = [].concat(merged.series || []).map(x => {
    if (!x) return x;
    const c = { ...x };
    if (c.label) c.label = { ...c.label, show: false };
    if (c.markLine) c.markLine = { ...c.markLine, label: { show: false }, data: (c.markLine.data || []).map(d => ({ ...d, label: { show: false } })) };
    return c;
  });
  // axis names: x centred under its axis, both bold so they read as variable names
  const hasSlider = [].concat(merged.dataZoom || []).some(z => z && z.type === 'slider');
  const nameStyle = a => ({ ...(a.nameTextStyle || {}), color: INK, fontWeight: 600, fontSize: 11.5, fontFamily: FONT });
  const fixX = a => (a && a.name ? { ...a, nameLocation: 'middle', nameGap: a.nameGap ?? 30, nameTextStyle: nameStyle(a) } : a);
  // y names run vertically along the middle of the axis, mirroring the x names
  const fixY = a => (a && a.name ? { ...a, nameLocation: 'middle', nameRotate: 90, nameGap: a.nameGap ?? 46, nameTextStyle: nameStyle(a) } : a);
  // Indonesian number format on value axes (1.200 instead of 1,200)
  const idFmt = a => (a && a.type === 'value' && !(a.axisLabel && a.axisLabel.formatter) ? { ...a, axisLabel: { ...(a.axisLabel || {}), formatter: v => v.toLocaleString('id-ID') } } : a);
  merged.xAxis = Array.isArray(merged.xAxis) ? merged.xAxis.map(a => idFmt(fixX(a))) : idFmt(fixX(merged.xAxis));
  merged.yAxis = Array.isArray(merged.yAxis) ? merged.yAxis.map(a => idFmt(fixY(a))) : idFmt(fixY(merged.yAxis));
  const xNamed = [].concat(merged.xAxis || []).find(a => a && a.name);
  if (xNamed && grids.length === 1 && typeof grids[0].bottom === 'number') grids[0].bottom = Math.max(grids[0].bottom, xNamed.nameGap + 20 + (hasSlider ? 28 : 0));
  const yNamedAx = [].concat(merged.yAxis || []).find(a => a && a.name);
  if (yNamedAx) grids.forEach(g => { if (typeof g.left === 'number') g.left = Math.max(g.left, yNamedAx.nameGap + 18); });
  // y names no longer sit above the plot, so the top margin only needs room for the legend
  if (hasSlider) merged.dataZoom = [].concat(merged.dataZoom).map(z => (z && z.type === 'slider' ? { ...z, bottom: 4, height: 16 } : z));
  if (merged.legend && !Array.isArray(merged.legend)) merged.legend = Object.assign({ textStyle: { color: INK2, fontSize: 11, fontFamily: FONT }, inactiveColor: AXIS }, merged.legend, { textStyle: Object.assign({ color: INK2, fontSize: 11, fontFamily: FONT }, (merged.legend || {}).textStyle || {}, { color: INK2 }) });
  return merged;
}
