import { useEffect, useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { MapContainer, TileLayer } from 'react-leaflet';
import Icon from './Icon.jsx';

const WORDS = ['Sumatera', 'Jawa', 'Kalimantan', 'Sulawesi', 'Papua'];

// monochrome world map, blurred, purely decorative (not data)
function WorldBackdrop({ theme }) {
  const zoom = Math.max(1.6, Math.log2(window.innerWidth / 256) + 0.35);
  return (
    <div className="op-map" aria-hidden="true">
      <MapContainer center={[12, 105]} zoom={zoom} zoomSnap={0.05} zoomControl={false} attributionControl={false} dragging={false}
        scrollWheelZoom={false} doubleClickZoom={false} touchZoom={false} boxZoom={false} keyboard={false} worldCopyJump
        style={{ width: '100%', height: '100%' }}>
        <TileLayer key={theme} url={`https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_${theme === 'dark' ? 'Dark' : 'Light'}_Gray_Base/MapServer/tile/{z}/{y}/{x}`} />
      </MapContainer>
    </div>
  );
}

function Rotating() {
  const reduce = useReducedMotion();
  const [i, setI] = useState(0);
  useEffect(() => { if (reduce) return; const t = setInterval(() => setI(x => (x + 1) % WORDS.length), 2600); return () => clearInterval(t); }, [reduce]);
  return (
    <span className="op-rot">
      <AnimatePresence mode="popLayout" initial={false}>
        <motion.span key={WORDS[i]} className="op-word"
          initial={{ y: '0.45em', opacity: 0, filter: 'blur(10px)' }} animate={{ y: 0, opacity: 1, filter: 'blur(0px)' }}
          exit={{ y: '-0.45em', opacity: 0, filter: 'blur(10px)' }} transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}>
          {WORDS[i]}
        </motion.span>
      </AnimatePresence>
    </span>
  );
}

export default function Opening({ theme, toggleTheme, onEnter, onGuide }) {
  // nothing behind the opening can scroll while it is shown
  useEffect(() => { const o = document.body.style.overflow; document.body.style.overflow = 'hidden'; return () => { document.body.style.overflow = o; }; }, []);
  const rise = (d = 0) => ({ initial: { opacity: 0, y: 18, filter: 'blur(8px)' }, animate: { opacity: 1, y: 0, filter: 'blur(0px)' }, transition: { duration: 0.8, delay: d, ease: [0.22, 1, 0.36, 1] } });
  return (
    <motion.section className="opening" role="dialog" aria-label="Pembuka dashboard"
      initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <WorldBackdrop theme={theme} />
      <div className="op-veil" aria-hidden="true" />
      <header className="op-top">
        <span className="op-brand"><img src="./logo_gelar_rasa.png" alt="Gelar Rasa" /></span>
        <button className="theme-tg" role="switch" aria-checked={theme === 'dark'} onClick={toggleTheme} aria-label="Mode gelap" title={theme === 'dark' ? 'Mode terang' : 'Mode gelap'}>
          <span className="theme-tg-knob"><Icon name={theme === 'dark' ? 'moon' : 'sun'} size={14} /></span>
        </button>
      </header>
      <div className="op-center">
        <motion.h1 className="op-title" {...rise(0.15)}>
          Dari Emisi Kronis Hingga Kabut Asap Ekstrem: Analisis Spasio-Temporal Polusi Udara, Dampak Kesehatan Akut (Lag 0), dan Kesenjangan Jaringan Pemantauan di Indonesia (2024–2026)
        </motion.h1>
        <motion.div className="op-cta" {...rise(0.3)}>
          <p className="op-by">Made by Tim Econs UGM Coba-Coba, Universitas Gadjah Mada.</p>
          <button className="op-btn" onClick={onEnter}>Buka Dashboard</button>
          <button className="op-link" onClick={onGuide}>Petunjuk Pengukuran</button>
        </motion.div>
      </div>
      <footer className="op-foot">Econs UGM Coba-Coba, 2026.</footer>
    </motion.section>
  );
}
