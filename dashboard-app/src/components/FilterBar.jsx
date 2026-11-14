import { memo } from 'react';
import { motion } from 'framer-motion';
import { useDash } from '../lib/DashContext.js';
import { ISL, CATS, CAT_S } from '../lib/constants.js';
import Dropdown from './Dropdown.jsx';
import Icon from './Icon.jsx';

const PERIODS = [['all', 'Semua tahun'], ['2024', '2024'], ['2025', '2025'], ['2026', '2026 (Hingga 14 Oktober)'], ['last12', '12 bulan terakhir'], ['custom', 'Pilih tanggal']];
const SEASONS = [['all', 'Semua musim'], ['wet', 'Hujan (Nov–Apr)'], ['dry', 'Kemarau (Mei–Okt)'], ['haze', 'Puncak PM2.5 (Agu–Okt)']];

function MultiList({ values, set, names, onToggle }) {
  return (
    <>
      {values.map(v => (
        <label key={v} className="dd-opt">
          <input type="checkbox" checked={set.has(v)} onChange={() => onToggle(v)} />
          {names ? names[v] : v}
        </label>
      ))}
    </>
  );
}

function SingleList({ items, value, onPick, close }) {
  return items.map(([v, l]) => (
    <button key={v} type="button" className={'dd-one' + (v === value ? ' on' : '')} onClick={() => { onPick(v); if (v !== 'custom') close(); }}>
      <span>{l}</span>{v === value && <Icon name="tick" size={16} />}
    </button>
  ));
}

export default memo(function FilterBar() {
  const { E, F, setF } = useDash();
  const setPeriod = p => setF(f => {
    let d0 = f.d0, d1 = f.d1;
    if (p === 'all') { d0 = 0; d1 = E.NDAYS - 1; }
    else if (p === 'last12') { d0 = E.idxOf('2025-10-15'); d1 = E.NDAYS - 1; }
    else if (p !== 'custom') { d0 = Math.max(0, E.idxOf(p + '-01-01')); d1 = Math.min(E.NDAYS - 1, E.idxOf(p + '-12-31')); }
    return { ...f, period: p, d0, d1 };
  });
  const setDate = (which, iso) => {
    const i = E.idxOf(iso); if (Number.isNaN(i)) return;
    setF(f => { let a = which === 0 ? i : f.d0, b = which === 1 ? i : f.d1; a = Math.max(0, Math.min(E.NDAYS - 1, a)); b = Math.max(0, Math.min(E.NDAYS - 1, b)); if (a > b) [a, b] = [b, a]; return { ...f, d0: a, d1: b }; });
  };
  const toggleSet = key => v => setF(f => { const s = new Set(f[key]); s.has(v) ? s.delete(v) : s.add(v); if (!s.size) (key === 'isl' ? ISL : CATS).forEach(x => s.add(x)); return { ...f, [key]: s }; });
  // the field name is shown until something is chosen; then the choice itself
  // multi-select buttons keep their name; the highlighted outline shows a filter is on
  const periodV = F.period === 'all' ? null : F.period === 'custom' ? `${E.fmtDay(F.d0)} – ${E.fmtDay(F.d1)}` : PERIODS.find(p => p[0] === F.period)[1];
  const seasonV = F.season === 'all' ? null : SEASONS.find(p => p[0] === F.season)[1].split(' (')[0];

  return (
    <div className="fbar">
      <div className="fbar-items">
        <Dropdown icon="map" label="Pulau" on={F.isl.size < ISL.length}>
          <MultiList values={ISL} set={F.isl} onToggle={toggleSet('isl')} />
        </Dropdown>
        <Dropdown icon="layers" label="Tipe lokasi" on={F.cat.size < CATS.length}>
          <MultiList values={CATS} set={F.cat} names={CAT_S} onToggle={toggleSet('cat')} />
        </Dropdown>
        <Dropdown icon="cloud" label="Musim" value={seasonV} on={F.season !== 'all'} width={260}>
          {close => <SingleList items={SEASONS} value={F.season} onPick={v => setF(f => ({ ...f, season: v }))} close={close} />}
        </Dropdown>
        <Dropdown icon="calendar" label="Tahun" value={periodV} on={F.period !== 'all'} width={260}>
          {close => (
            <>
              <SingleList items={PERIODS} value={F.period} onPick={setPeriod} close={close} />
              {F.period === 'custom' && (
                <div className="dd-dates">
                  <label>Dari<input type="date" min="2024-01-01" max="2026-10-14" value={E.DAY_S[F.d0]} onChange={e => setDate(0, e.target.value)} /></label>
                  <label>Sampai<input type="date" min="2024-01-01" max="2026-10-14" value={E.DAY_S[F.d1]} onChange={e => setDate(1, e.target.value)} /></label>
                </div>
              )}
            </>
          )}
        </Dropdown>
      </div>
    </div>
  );
});
