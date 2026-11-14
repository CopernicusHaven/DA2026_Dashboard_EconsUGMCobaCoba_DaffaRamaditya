import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import Icon from './Icon.jsx';

// small "i" button; method notes live here instead of on the page
export default function Info({ text, align = 'right' }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    if (!open) return;
    const close = e => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    const esc = e => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', close); document.addEventListener('keydown', esc);
    return () => { document.removeEventListener('mousedown', close); document.removeEventListener('keydown', esc); };
  }, [open]);
  return (
    <span className="info" ref={ref}>
      <button type="button" className="info-btn" aria-expanded={open} aria-label="Catatan" onClick={() => setOpen(o => !o)}><Icon name="info" size={16} /></button>
      <AnimatePresence>
        {open && (
          <motion.span className={'info-pop ' + align} role="note" initial={{ opacity: 0, y: 6, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 4 }} transition={{ duration: 0.15 }}>
            {text}
          </motion.span>
        )}
      </AnimatePresence>
    </span>
  );
}
