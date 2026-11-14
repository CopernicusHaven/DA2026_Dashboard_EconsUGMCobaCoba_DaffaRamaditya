import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { motion, animate, useReducedMotion } from 'framer-motion';
import { useDash } from '../lib/DashContext.js';
import Icon from './Icon.jsx';
import FilterBar from './FilterBar.jsx';
import { tc } from '../lib/text.js';

const Tile = ({ t, free }) => (
  <div className={'card tile' + (free ? ' free' : '') + (t.tone ? ' ' + t.tone : '')}>
    <div className="tile-l" title={tc(t.l)}>{tc(t.l)}</div>
    <div className="tile-v">{t.v}{t.u && <small>{t.u}</small>}</div>
  </div>
);

function useWidth() {
  const ref = useRef(null);
  const [w, setW] = useState(0);
  useLayoutEffect(() => {
    const ro = new ResizeObserver(([e]) => setW(e.contentRect.width));
    ro.observe(ref.current); setW(ref.current.getBoundingClientRect().width);
    return () => ro.disconnect();
  }, []);
  return [ref, w];
}

// Looping slider (drag, swipe, click a side card or a dot): the last card is followed by the first
// again. Cards beside the centred one shrink and fade a little.
function Carousel({ items, cardWidth, render, names }) {
  const [box, w] = useWidth();
  const n = items.length, GAP = 16;
  const [i, setI] = useState(n);          // index in the tripled list, starts in the middle copy
  const [jump, setJump] = useState(false);
  useEffect(() => { setJump(true); setI(n); }, [n]);
  const cw = cardWidth(w), step = cw + GAP;
  const x = (w - cw) / 2 - i * step;
  const go = d => { setJump(false); setI(v => v + d); };
  const settle = () => { if (i < n || i >= 2 * n) { setJump(true); setI(((i % n) + n) % n + n); } };
  const list = [...items, ...items, ...items];
  const cur = ((i % n) + n) % n;
  return (
    <div ref={box} className="car-box">
      <div className="tiles-slider">
        <motion.div className="tiles-track" drag="x" dragElastic={0.18} dragMomentum={false}
          style={{ gap: GAP }} animate={{ x }} transition={jump ? { duration: 0 } : { type: 'spring', stiffness: 260, damping: 30 }}
          onAnimationComplete={settle}
          onDragEnd={(e, info) => { const d = Math.round(-(info.offset.x + info.velocity.x * 0.15) / step); go(Math.max(-n, Math.min(n, d)) || 0); }}>
          {list.map((t, k) => {
            const dist = Math.abs(k - i);
            return (
              <motion.div key={k} style={{ width: cw, flex: 'none' }}
                animate={{ scale: dist === 0 ? 1 : 0.9, opacity: dist === 0 ? 1 : dist === 1 ? 0.55 : 0.2 }}
                transition={jump ? { duration: 0 } : { type: 'spring', stiffness: 260, damping: 28 }}
                onClick={() => dist && go(k - i)}>
                {render(t, k % n)}
              </motion.div>
            );
          })}
        </motion.div>
      </div>
      <div className="tiles-dots">
        {items.map((t, k) => <button key={k} aria-label={names[k]} className={cur === k ? 'on' : ''} onClick={() => go(k - cur)} />)}
      </div>
    </div>
  );
}

// KPI cards: one row when they all fit, otherwise the looping slider.
function TileStrip({ tiles }) {
  const [box, w] = useWidth();
  const n = tiles.length, GAP = 16, MIN = 214;
  const fits = !w || w >= n * MIN + (n - 1) * GAP;
  return (
    <div ref={box} className="tiles-box">
      {fits ? (
        <div className={'tiles' + (n === 3 ? ' n3' : '')}>{tiles.map(t => <Tile key={t.l} t={t} />)}</div>
      ) : (
        <Carousel items={tiles} cardWidth={w => Math.min(260, Math.max(190, (w - 2 * GAP) / 2.3))}
          render={t => <Tile t={t} free />} names={tiles.map(t => tc(t.l))} />
      )}
    </div>
  );
}

// key findings of the page, one card per finding in the looping slider; written from the same
// filtered numbers as the cards and charts
export function Findings({ items }) {
  const list = items.filter(Boolean);
  if (!list.length) return null;
  const card = (t, k) => (
    <div className="card fd-card">
      <div className="fd-h">Temuan Utama {k + 1}</div>
      <div className="fd-t">{t}</div>
    </div>
  );
  return (
    <section className="findings" aria-label="Temuan utama">
      {list.length === 1 ? <div className="fd-one">{card(list[0], 0)}</div> : (
        <Carousel items={list} cardWidth={w => Math.max(240, Math.min(520, w * 0.56, w - 56))}
          render={card} names={list.map((_, k) => 'Temuan utama ' + (k + 1))} />
      )}
    </section>
  );
}

// page: title + period, optional page controls, KPI cards, key findings, chart cards
export function PageLayout({ title, actions, tiles = [], findings, children }) {
  return (
    <>
      <h1 className="sr-only">{title}</h1>
      <div className="pfilters"><FilterBar /></div>
      {actions && <div className="actbar">{actions}</div>}
      {tiles.length > 0 && <TileStrip tiles={tiles} />}
      {findings && <Findings items={findings} />}
      {children}
    </>
  );
}

// plain card section (non-carousel content)
export const Section = ({ title, children }) => (
  <section className="card sect">
    <h3 className="card-t">{tc(title)}</h3>
    <div className="sect-b">{children}</div>
  </section>
);

export function Seg({ id, items, value, onChange, label }) {
  return (
    <div className="seg" role="group" aria-label={label || 'pilihan'}>
      {items.map(([v, l]) => (
        <button key={v} type="button" aria-pressed={value === v} onClick={() => onChange(v)}>
          {value === v && <motion.span layoutId={'seg-' + id} className="seg-pill" transition={{ type: 'spring', stiffness: 420, damping: 34 }} />}
          <span className="seg-t">{l}</span>
        </button>
      ))}
    </div>
  );
}

export const Tag = ({ kind = 'neu', color, children }) => <span className={'tag ' + (color ? 'c' : kind)} style={color ? { '--dot': color } : undefined}>{children}</span>;

export function CountUp({ value, format }) {
  const reduce = useReducedMotion();
  const [shown, setShown] = useState(value);
  const prev = useRef(value);
  useEffect(() => {
    if (value == null || Number.isNaN(value) || reduce || prev.current == null || Number.isNaN(prev.current) || prev.current === value) { setShown(value); prev.current = value; return; }
    const from = prev.current;
    const ctl = animate(from, value, { duration: 0.6, ease: [0.16, 1, 0.3, 1], onUpdate: v => setShown(v) });
    prev.current = value;
    return () => ctl.stop();
  }, [value, reduce]);
  return <>{format(shown)}</>;
}

export const Legend = ({ items }) => (
  <div className="legend-inline">{items.map(([c, l, cls]) => <span key={l}><i className={cls || ''} style={cls ? undefined : { background: c }} />{l}</span>)}</div>
);
