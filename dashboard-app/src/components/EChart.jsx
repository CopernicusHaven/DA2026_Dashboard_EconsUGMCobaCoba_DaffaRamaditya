import { useEffect, useMemo, useRef } from 'react';
import * as echarts from 'echarts';
import { chartNotes, withBase } from '../lib/chartBase.js';
import { THEME } from '../lib/constants.js';

// Chart updates are applied one per animation frame (a theme switch would otherwise repaint
// every chart in a single long task).
const queue = new Map(); let ticking = false;
function flush() {
  const first = queue.entries().next();
  if (first.done) { ticking = false; return; }
  const [key, fn] = first.value; queue.delete(key); fn();
  requestAnimationFrame(flush);
}
// When the legend wraps onto more lines (narrow screens), move the plot down so the legend
// never touches the top of the plot.
function fitLegend(c) {
  try {
    const m = c.getModel(); const lg = m.getComponent('legend'); const gr = m.getComponent('grid');
    if (!lg || !gr || m.getComponent('grid', 1) || lg.get('show') === false || lg.get('orient') === 'vertical') return;
    const top = gr.get('top');
    if (typeof top !== 'number' || !gr.coordinateSystem) return;
    const v = c.getViewOfComponentModel(lg); if (!v) return;
    const b = v.group.getBoundingRect(); const y0 = v.group.y + b.y, y1 = y0 + b.height;
    if (!b.height || y0 > c.getHeight() / 2) return;           // legend sits under the plot
    const gap = gr.coordinateSystem.getRect().y - 10 - y1;   // 10px: half of the top axis label
    if (gap < 6) c.setOption({ grid: { top: Math.ceil(top + 6 - gap) } });
  } catch { /* layout guard only */ }
}
const enqueue = (key, fn) => { queue.set(key, fn); if (!ticking) { ticking = true; requestAnimationFrame(flush); setTimeout(() => { if (ticking && queue.size) flush(); }, 200); } };

// Thin ECharts wrapper: init once, resize with its container, re-render on option change,
// forward events through a ref so handlers can change without re-binding.
export default function EChart({ option, height = 360, onEvents, className = '', ariaLabel }) {
  const el = useRef(null);
  const inst = useRef(null);
  const handlers = useRef(onEvents);
  handlers.current = onEvents;

  const opt = useRef(option);
  opt.current = option;
  const narrow = useRef(false);                     // narrow chart (phone): fewer controls
  const isNarrow = () => !!el.current && el.current.clientWidth < 520;

  // Create the chart only after the new page has been painted (next frame + task), so a page
  // switch shows the layout at once and the canvas work does not block the click.
  useEffect(() => {
    let c = null, ro = null, done = false, raf = 0, t1 = 0;
    const init = () => {
      if (done || !el.current) return;
      done = true; clearTimeout(t1); cancelAnimationFrame(raf);
      c = echarts.init(el.current, null, { renderer: 'canvas' });
      inst.current = c;
      el.current.__ec = c; // lets the final chart settings be inspected (verification)
      ['click', 'datazoom'].forEach(ev => c.on(ev, p => handlers.current && handlers.current[ev] && handlers.current[ev](p)));
      narrow.current = isNarrow();
      if (opt.current) { c.setOption(withBase(opt.current, { narrow: narrow.current }), true); fitLegend(c); }
      lastTheme.current = THEME;
      ro = new ResizeObserver(() => {
        c.resize();
        const n = isNarrow();   // e.g. a tablet turned from portrait to landscape
        if (n !== narrow.current && opt.current) { narrow.current = n; c.setOption(withBase({ ...opt.current, animation: false }, { narrow: n }), true); }
        fitLegend(c);
      });
      ro.observe(el.current);
    };
    let t2 = 0;
    const schedule = () => {
      raf = requestAnimationFrame(() => { t1 = setTimeout(init, 0); });
      t2 = setTimeout(init, 120); // fallback when frames are paused (background tab)
    };
    const io = new IntersectionObserver(es => { if (es.some(e => e.isIntersecting)) { io.disconnect(); schedule(); } }, { rootMargin: '300px 0px' });
    io.observe(el.current);
    return () => { done = true; io.disconnect(); cancelAnimationFrame(raf); clearTimeout(t1); clearTimeout(t2); if (ro) ro.disconnect(); if (c) c.dispose(); inst.current = null; };
  }, []);

  const lastTheme = useRef(THEME);
  useEffect(() => {
    if (!inst.current || !option) return;
    const themeOnly = lastTheme.current !== THEME;   // colour change only: redraw without animation
    lastTheme.current = THEME;
    const c = inst.current;
    enqueue(c, () => { if (!c.isDisposed()) { c.setOption(withBase(themeOnly ? { ...option, animation: false } : option, { narrow: narrow.current }), true); fitLegend(c); } });
  }, [option]);

  const notes = useMemo(() => chartNotes(option), [option]);
  return (
    <>
      <div ref={el} className={'chart ' + className} style={{ height }} role="img" aria-label={ariaLabel || 'grafik'} />
      {notes.length > 0 && (
        <div className="chart-notes">{notes.map(n => <span key={n.text}><i style={{ borderTopStyle: n.type }} />{n.text}</span>)}</div>
      )}
    </>
  );
}

export { echarts };
