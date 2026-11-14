import { memo, useMemo, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useDash } from '../lib/DashContext.js';
import { nf } from '../lib/engine.js';

// interactive station list (like a watchlist): ranked by PM2.5 on the active filter,
// checkbox = compare (max 6), click = open the station detail panel
export default memo(function StationPanel() {
  const { E, F, agg, openStation, toggleStation } = useDash();
  const [tab, setTab] = useState('top');
  const rows = useMemo(() => E.ST.filter(s => s.used_in_analysis && F.isl.has(s.island) && F.cat.has(s.site_category))
    .map(s => ({ s, v: agg.stMean(s.station, 'pm25') })).filter(x => x.v.ok).map(x => ({ s: x.s, v: x.v.mean })), [E, F, agg]);
  const max = Math.max(...rows.map(r => r.v), 1);
  const list = [...rows].sort((a, b) => tab === 'top' ? b.v - a.v : a.v - b.v);
  const TABS = [['top', 'Tertinggi'], ['low', 'Terbersih']];
  return (
    <section className="card stp">
      <h3 className="stp-title">Stasiun</h3>
      <div className="stp-tabs" role="tablist">
        {TABS.map(([k, l]) => (
          <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}>
            <span>{l}</span>
            {tab === k && <motion.span layoutId="stp-line" className="tab-line" transition={{ type: 'spring', stiffness: 520, damping: 42 }} />}
          </button>
        ))}
      </div>
      <div className="stp-list">
        {!list.length && <div className="empty">Tidak ada stasiun pada filter ini.</div>}
        <AnimatePresence initial={false}>
          {list.map(({ s, v }, i) => (
            <motion.div key={s.station} layout className={'st-item' + (F.st.has(s.station) ? ' sel' : '')} onClick={() => openStation(s.station)}
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }}>
              <input type="checkbox" checked={F.st.has(s.station)} aria-label={'Bandingkan ' + s.station}
                onClick={e => e.stopPropagation()} onChange={() => toggleStation(s.station)} />
              <span className="st-rank">{i + 1}</span>
              <div className="st-main"><b>{s.station}</b><small title={s.kota_kabupaten + ', ' + s.provinsi}><span>{s.kota_kabupaten.replace('Kabupaten ', 'Kab. ').replace('Kota Administrasi ', '').replace('Kota ', '')}</span></small></div>
              <div className="st-val">
                <b>{nf(v, 1)}</b>
                <div className="st-bar"><i style={{ width: `${(v / max) * 100}%` }} /></div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </section>
  );
});
