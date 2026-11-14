import { useEffect, useRef, useState } from 'react';
import { tc } from '../lib/text.js';

// Renders its content only once it comes near the viewport, so switching pages does not
// build every chart, table and map at once. A placeholder keeps the layout stable until then.
function Lazy({ eager, minHeight, children }) {
  const ref = useRef(null);
  const [show, setShow] = useState(eager);
  useEffect(() => {
    if (show || !ref.current) return;
    const io = new IntersectionObserver(es => { if (es.some(e => e.isIntersecting)) { setShow(true); io.disconnect(); } }, { rootMargin: '500px 0px' });
    io.observe(ref.current);
    return () => io.disconnect();
  }, [show]);
  return <div ref={ref} style={show ? undefined : { minHeight }}>{show ? children() : null}</div>;
}

// Every chart, table or map in its own card. A card shows its title and controls in a header;
// a map card has no title (label left empty) so the map fills the card.
export default function Row({ id, slides, height = 380, eager = false }) {
  return slides.map((s, k) => {
    const head = s.label || s.controls;
    return (
      <section key={s.key} className={'card gcard' + (head ? '' : ' bare')} id={`sec-${id}-${s.key}`} aria-label={s.label || s.key}>
        {head && (
          <div className="gcard-h">
            {s.label && <h3>{tc(s.label)}</h3>}
            {s.controls && <div className="blk-ctrl">{s.controls}</div>}
          </div>
        )}
        <Lazy eager={eager && k === 0} minHeight={height}>
          {() => <div className="blk-body">{s.content()}</div>}
        </Lazy>
      </section>
    );
  });
}
