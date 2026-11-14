import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import Icon from './Icon.jsx';
import { tc } from '../lib/text.js';

// filter button: shows the field name until a value is chosen, then the value
export default function Dropdown({ label, value, on, children, width = 240, icon }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    if (!open) return;
    const close = e => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    const esc = e => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', close); document.addEventListener('keydown', esc);
    return () => { document.removeEventListener('mousedown', close); document.removeEventListener('keydown', esc); };
  }, [open]);
  const set = value != null;
  const active = on ?? set;
  return (
    <div className="dd" ref={ref}>
      <button type="button" className={'fbtn' + (active ? ' active' : '')} aria-haspopup="true" aria-expanded={open} onClick={() => setOpen(o => !o)}
        title={set ? `${label}: ${value}` : label}>
        <span className="fbtn-v">{set ? value : tc(label)}</span>
      </button>
      <AnimatePresence>
        {open && (
          <motion.div className="dd-panel" style={{ minWidth: width }} initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }} transition={{ duration: 0.12 }}>
            {typeof children === 'function' ? children(() => setOpen(false)) : children}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
