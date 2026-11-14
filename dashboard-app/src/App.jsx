import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Dash } from './lib/DashContext.js';
import { buildEngine, buildMask, defaultFilters, makeAgg } from './lib/engine.js';
import { PAGES, applyTheme } from './lib/constants.js';
import StationDrawer from './components/StationDrawer.jsx';
import StationPanel from './components/StationPanel.jsx';
import Icon from './components/Icon.jsx';
import Opening from './components/Opening.jsx';
import Ringkasan from './pages/Ringkasan.jsx';
import Kondisi from './pages/Kondisi.jsx';
import Kritis from './pages/Kritis.jsx';
import Faktor from './pages/Faktor.jsx';
import Kesehatan from './pages/Kesehatan.jsx';
import Jaringan from './pages/Jaringan.jsx';
import Petunjuk from './pages/Petunjuk.jsx';

const VIEWS = { ringkasan: Ringkasan, kondisi: Kondisi, kritis: Kritis, faktor: Faktor, kesehatan: Kesehatan, jaringan: Jaringan, petunjuk: Petunjuk };
const GUIDE = { id: 'petunjuk', label: 'Petunjuk Pengukuran', short: 'Petunjuk Pengukuran', icon: 'file' };
const ALL = [...PAGES, GUIDE];
const inRow = el => el && el.closest && el.closest('.row');
// ?capture=1 (report screenshots only): skip the opening page and the slide-in animation, and
// record each card's position so the screenshot can be cut into single visuals
const CAPTURE = typeof location !== 'undefined' && new URLSearchParams(location.search).has('capture');

// Elements that slide down into place when they come into view (and again each time they come back).
const REVEAL = '.hdr-bar, .pfilters, .actbar, .pmain .card, .pside > .card, .wrap > footer';
function useReveal(active, pageKey) {
  const wasActive = useRef(false);
  useLayoutEffect(() => {
    if (!active || CAPTURE) { wasActive.current = false; return; }
    const fresh = !wasActive.current; wasActive.current = true;   // just entered from the opening page
    const els = [...document.querySelectorAll(REVEAL)];
    const root = document.documentElement;
    root.classList.add('rv-off');                                  // hide without animating
    els.forEach(el => { if (fresh || !el.dataset.rv) { el.dataset.rv = '0'; el.style.removeProperty('--rv-d'); } });
    void root.offsetHeight;
    root.classList.remove('rv-off');
    // shown once it is a little inside the viewport, hidden again only when it is fully out of view
    const show = new IntersectionObserver(entries => {
      const inView = entries.filter(e => e.isIntersecting && e.target.dataset.rv !== '1')
        .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top || a.boundingClientRect.left - b.boundingClientRect.left);
      inView.forEach((e, i) => { e.target.style.setProperty('--rv-d', Math.min(i, 6) * 80 + 'ms'); e.target.dataset.rv = '1'; });
    }, { rootMargin: '0px 0px -6% 0px' });
    const hide = new IntersectionObserver(entries => {
      entries.forEach(e => { if (!e.isIntersecting && e.target.dataset.rv === '1' && !e.target.classList.contains('hdr-bar')) { e.target.style.removeProperty('--rv-d'); e.target.dataset.rv = '0'; } });
    });
    els.forEach(el => { show.observe(el); hide.observe(el); });
    return () => { show.disconnect(); hide.disconnect(); };
  }, [active, pageKey]);
}

const loadTheme = () => { try { return localStorage.getItem('da2026-theme') || 'light'; } catch { return 'light'; } };
const saveTheme = t => { try { localStorage.setItem('da2026-theme', t); } catch { /* storage unavailable */ } };
const setThemeDom = t => {
  const html = document.documentElement;
  html.classList.add('theming');                 // no CSS transitions during the swap
  applyTheme(t); html.dataset.theme = t;
  setTimeout(() => html.classList.remove('theming'), 120);
};

// While the data loads nothing is shown (no logo flash on refresh); only a load error gets a message.
function Loader({ error }) {
  return error ? <div className="loader"><p>Data gagal dimuat ({error}).</p></div> : null;
}

function Dashboard({ D, theme, toggleTheme, active, onHome }) {
  const E = useMemo(() => buildEngine(D), [D]);
  const [F, setF] = useState(() => defaultFilters(E));
  const mask = useMemo(() => buildMask(E, F), [E, F.d0, F.d1, F.season]); // eslint-disable-line react-hooks/exhaustive-deps
  const agg = useMemo(() => makeAgg(E, mask), [E, mask]);
  // Theme switch: give pages new E/agg references so their chart options rebuild with the new colours,
  // instead of remounting the whole page (maps and charts are updated in place).
  const Et = useMemo(() => ({ ...E }), [E, theme]); // eslint-disable-line react-hooks/exhaustive-deps
  const aggT = useMemo(() => ({ ...agg }), [agg, theme]); // eslint-disable-line react-hooks/exhaustive-deps
  const [hov, setHov] = useState(null); // menu item under the cursor (underline follows it)
  const [menu, setMenu] = useState(false); // small screens: the pages are listed in a panel under the bar
  const [ui, setUiState] = useState({ pol: 'pm25', diur: 'pm25', week: 'no2', heat: 'pm25', traf: 'pm25', year: 2025, out: 'resp_admissions_under5', hosp: 'RS-XXX-04' });
  const setUi = useCallback((k, v) => setUiState(u => ({ ...u, [k]: v })), []);
  const [drawer, setDrawer] = useState(null);
  const [toast, setToast] = useState(null);
  const toastT = useRef();
  const showToast = useCallback(msg => { setToast(msg); clearTimeout(toastT.current); toastT.current = setTimeout(() => setToast(null), 4000); }, []);

  // pi indexes ALL: the 6 analysis pages + the measurement guide (opened from its own button)
  const [pi, setPi] = useState(() => Math.max(0, ALL.findIndex(p => p.id === location.hash.slice(1))));
  const go = useCallback(i => setPi((i + PAGES.length) % PAGES.length), []);
  const openGuide = useCallback(() => setPi(ALL.length - 1), []);
  const page = ALL[pi];
  const isGuide = page.id === GUIDE.id;
  useReveal(active, page.id);
  useEffect(() => {
    if (!CAPTURE) return;
    const st = new URLSearchParams(location.search).get('station');
    const t0 = st ? setTimeout(() => setDrawer(st), 1500) : 0;
    const t = setTimeout(() => {
      const rect = el => { const r = el.getBoundingClientRect(); return [Math.round(r.left + scrollX), Math.round(r.top + scrollY), Math.round(r.width), Math.round(r.height)]; };
      const out = { page: page.id, full: rect(document.querySelector('.wrap')), hdr: rect(document.querySelector('.hdr-bar')), cards: [] };
      document.querySelectorAll('.pfilters, .tiles, .pmain .gcard, .pmain .sect, .pside > .card').forEach(el => {
        out.cards.push({ cls: el.className, title: (el.querySelector('h3') || {}).textContent || '', r: rect(el) });
      });
      let n = document.getElementById('capture-rects');
      if (!n) { n = document.createElement('script'); n.type = 'application/json'; n.id = 'capture-rects'; document.body.appendChild(n); }
      n.textContent = JSON.stringify(out);
    }, 6000);
    return () => { clearTimeout(t); clearTimeout(t0); };
  }, [page.id]);
  useEffect(() => {
    history.replaceState(null, '', '#' + page.id);
    document.title = `${page.label} — DA2026 Dashboard Gelar Rasa`;
    window.scrollTo({ top: 0, behavior: 'instant' });
    setDrawer(null);
    setMenu(false);
  }, [page]);
  useEffect(() => {
    if (!menu) return;
    const close = e => { if (!e.target.closest || !e.target.closest('.hdr-bar')) setMenu(false); };
    const esc = e => { if (e.key === 'Escape') setMenu(false); };
    document.addEventListener('pointerdown', close); document.addEventListener('keydown', esc);
    return () => { document.removeEventListener('pointerdown', close); document.removeEventListener('keydown', esc); };
  }, [menu]);
  useEffect(() => {
    const onHash = () => { const i = ALL.findIndex(p => p.id === location.hash.slice(1)); if (i >= 0) setPi(i); };
    window.addEventListener('hashchange', onHash); return () => window.removeEventListener('hashchange', onHash);
  }, [go]);

  // keep the active tab visible when the nav row scrolls (narrow screens)
  const tnav = useRef(null);
  useEffect(() => {
    const nav = tnav.current, b = nav && nav.querySelector('[aria-selected="true"]');
    if (!nav || !b || nav.scrollWidth <= nav.clientWidth) return;
    const nr = nav.getBoundingClientRect(), br = b.getBoundingClientRect();
    // scroll only as much as needed to show the active tab completely
    const d = br.left < nr.left ? br.left - nr.left - 8 : br.right > nr.right ? br.right - nr.right + 8 : 0;
    if (d) nav.scrollTo({ left: nav.scrollLeft + d, behavior: 'smooth' });
  }, [pi]);

  // header height → CSS var, so the sticky station column sits right under it
  const hdr = useRef(null);
  useEffect(() => {
    const el = hdr.current; if (!el) return;
    const set = () => document.documentElement.style.setProperty('--hdr-h', el.offsetHeight + 'px');
    const ro = new ResizeObserver(set); ro.observe(el); set();
    return () => ro.disconnect();
  }, []);

  // The top bar slides away once the bottom of the KPI cards has scrolled up past it,
  // and comes back as soon as that edge is scrolled back down to it.
  const [hdrOff, setHdrOff] = useState(false);
  useEffect(() => {
    if (!active) { setHdrOff(false); return; }
    let raf = 0;
    const check = () => {
      raf = 0;
      const mark = document.querySelector('.pmain .tiles') || document.querySelector('.pmain .phead') || document.querySelector('.pmain .pfilters');
      const h = hdr.current ? hdr.current.offsetHeight : 0;
      const off = !!mark && mark.getBoundingClientRect().bottom < h;
      setHdrOff(o => (o === off ? o : off));
      if (off) setMenu(false);
    };
    const on = () => { if (!raf) raf = requestAnimationFrame(check); };
    window.addEventListener('scroll', on, { passive: true });
    window.addEventListener('resize', on);
    check();
    return () => { cancelAnimationFrame(raf); window.removeEventListener('scroll', on); window.removeEventListener('resize', on); };
  }, [active, page.id]);

  // ← → switch pages unless a chart row has focus (there they switch charts)
  useEffect(() => {
    const onKey = e => {
      if (!active) return;
      if (e.key === 'Escape') { setDrawer(null); return; }
      const a = document.activeElement;
      if (['INPUT', 'SELECT', 'TEXTAREA'].includes(a?.tagName) || inRow(a) || drawer) return;
      if (isGuide) return;
      if (e.key === 'ArrowRight') go(pi + 1);
      if (e.key === 'ArrowLeft') go(pi - 1);
    };
    window.addEventListener('keydown', onKey); return () => window.removeEventListener('keydown', onKey);
  }, [pi, go, drawer, isGuide, active]);

  // memoized so switching pages does not re-render filter bar, station list or drawer
  const ctx = useMemo(() => ({
    E: Et, F, setF, agg: aggT, ui, setUi, go, theme, showToast, isGuide, openGuide,
    resetFilters: () => { setF(defaultFilters(E)); showToast('Filter direset'); },
    openStation: code => setDrawer(code), closeStation: () => setDrawer(null),
    focusStation: code => {
      setF(f => ({ ...f, st: new Set([code]) }));
      const h = E.HOSP.find(x => x.station === code); if (h) setUi('hosp', h.id);
      setDrawer(null); showToast(`Fokus: ${code}`);
    },
    toggleStation: code => setF(f => { const st = new Set(f.st); if (st.has(code)) st.delete(code); else if (st.size < 6) st.add(code); return { ...f, st }; }),
    addStation: code => { setF(f => (f.st.size >= 6 ? f : { ...f, st: new Set([...f.st, code]) })); showToast(`${code} ditambahkan`); },
  }), [Et, F, aggT, ui, setUi, go, theme, showToast, isGuide, openGuide]);
  const View = VIEWS[page.id];

  return (
    <Dash.Provider value={ctx}>
      {/* floating top bar: logo left, menu centred, theme toggle right; stays afloat while scrolling */}
      <header className={'hdr' + (hdrOff ? ' off' : '')} ref={hdr}>
        <div className="hdr-bar">
          <a className="brand" href="#" onClick={e => { e.preventDefault(); onHome(); }} aria-label="Gelar Rasa — halaman pembuka" title="Halaman pembuka">
            <img src="./logo_gelar_rasa.png" alt="Gelar Rasa" />
          </a>
          <nav className="tnav" role="tablist" aria-label="Halaman" ref={tnav} onMouseLeave={() => setHov(null)}>
            {ALL.map((p, i) => (
              <button key={p.id} className={'tnav-i' + (p.id === GUIDE.id ? ' tnav-guide' : '')} role="tab" aria-selected={i === pi}
                onMouseEnter={() => setHov(i)} onFocus={() => setHov(i)} onBlur={() => setHov(null)}
                onClick={() => (p.id === GUIDE.id ? openGuide() : go(i))} title={p.label}>
                <span>{p.short}</span>
                {i === (hov ?? pi) && <motion.span layoutId="navline" className="tnav-line" transition={{ type: 'spring', stiffness: 560, damping: 44 }} />}
              </button>
            ))}
          </nav>
          <button className={'mnav-btn' + (menu ? ' on' : '')} aria-expanded={menu} aria-controls="mnav" onClick={() => setMenu(m => !m)}>Menu</button>
          <button className="theme-tg" role="switch" aria-checked={theme === 'dark'} onClick={toggleTheme} title={theme === 'dark' ? 'Mode terang' : 'Mode gelap'} aria-label="Mode gelap">
            <span className="theme-tg-knob"><Icon name={theme === 'dark' ? 'moon' : 'sun'} size={14} /></span>
          </button>
          <AnimatePresence>
            {menu && (
              <motion.nav id="mnav" className="mnav" aria-label="Halaman" initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} transition={{ duration: 0.18 }}>
                {ALL.map((p, i) => (
                  <button key={p.id} className={'mnav-i' + (p.id === GUIDE.id ? ' mnav-guide' : '')} aria-current={i === pi ? 'page' : undefined}
                    onClick={() => { setMenu(false); if (p.id === GUIDE.id) openGuide(); else go(i); }}>{p.short}</button>
                ))}
              </motion.nav>
            )}
          </AnimatePresence>
        </div>
      </header>

      <div className={'wrap' + (hdrOff ? ' hdr-off' : '')}>
        <div className={'pgrid' + (isGuide ? ' full' : '')}>
          {!isGuide && <aside className="pside"><StationPanel /></aside>}
          <main className="pmain" key={page.id}>
            <View />
          </main>
        </div>
        <footer>Econs UGM Coba-Coba, 2026.</footer>
      </div>

      <StationDrawer code={drawer} />
      <AnimatePresence>
        {toast && (
          <motion.div className="toast" initial={{ opacity: 0, y: 20, x: '-50%' }} animate={{ opacity: 1, y: 0, x: '-50%' }} exit={{ opacity: 0, y: 20, x: '-50%' }}>
            <span>{toast}</span>
            {F.st.size > 0 && <button onClick={() => { setF(f => ({ ...f, st: new Set() })); setToast(null); }}>Semua stasiun</button>}
          </motion.div>
        )}
      </AnimatePresence>
    </Dash.Provider>
  );
}

export default function App() {
  const [D, setD] = useState(null);
  const [err, setErr] = useState(null);
  const [theme, setTheme] = useState(() => { const t = loadTheme(); setThemeDom(t); return t; });
  const toggleTheme = useCallback(() => setTheme(t => { const n = t === 'dark' ? 'light' : 'dark'; setThemeDom(n); saveTheme(n); return n; }), []);
  useEffect(() => {
    const data = fetch('./data/dashboard.json').then(r => { if (!r.ok) throw new Error(r.status); return r.json(); });
    data.then(d => setD(d)).catch(e => setErr(String(e)));
  }, []);
  // opening page first; entering is instant (the dashboard's own elements then slide in),
  // going back to the opening page fades the dashboard out
  // a link straight to a page (for example #kondisi) opens that page without the opening screen
  const [entered, setEntered] = useState(() => CAPTURE || ['ringkasan', 'kondisi', 'kritis', 'faktor', 'kesehatan', 'jaringan', 'petunjuk'].includes(location.hash.slice(1)));
  const enter = useCallback(() => setEntered(true), []);
  const enterGuide = useCallback(() => { location.hash = '#petunjuk'; setEntered(true); }, []);
  const home = useCallback(() => { window.scrollTo({ top: 0 }); setEntered(false); }, []);
  return (
    <>
      {D ? (
        <motion.div className="app" initial="out" animate={entered ? 'in' : 'out'} aria-hidden={!entered}
          variants={{
            out: { opacity: 0, y: '10vh', filter: 'blur(18px)', transition: { duration: 0.5 } },
            in: { opacity: 1, y: 0, filter: 'blur(0px)', transition: { duration: 0 }, transitionEnd: { filter: 'none' } },
          }}>
          <Dashboard D={D} theme={theme} toggleTheme={toggleTheme} active={entered} onHome={home} />
        </motion.div>
      ) : entered && <Loader error={err} />}
      <AnimatePresence>
        {!entered && <Opening key="opening" theme={theme} toggleTheme={toggleTheme} onEnter={enter} onGuide={enterGuide} />}
      </AnimatePresence>
    </>
  );
}
