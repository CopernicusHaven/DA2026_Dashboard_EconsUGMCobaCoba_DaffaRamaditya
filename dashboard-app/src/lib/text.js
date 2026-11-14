// Title case for headings (Indonesian): every word starts with a capital, except conjunctions and
// prepositions such as "dan", "ke", "yang" (unless they open the title). Words that do not start with
// a plain lowercase letter (PM2.5, µg/m³, ISPU, (ρ), 2024–2026) are left as they are.
const UNITS = new Set(['ppm', 'km', 'm', 'g/mol', 'kendaraan/jam']);
const SMALL = new Set(['dan', 'atau', 'serta', 'yang', 'di', 'ke', 'dari', 'untuk', 'pada', 'dengan', 'dalam', 'per', 'oleh', 'terhadap', 'sebagai', 'antara', 's.d.']);

export function tc(str) {
  if (typeof str !== 'string') return str;
  let first = true;
  return str.split(/(\s+)/).map(tok => {
    if (!tok.trim()) return tok;
    const bare = tok.toLowerCase().replace(/[(),:;]/g, '');
    const keepLower = !first && SMALL.has(bare);
    first = false;
    if (keepLower || UNITS.has(bare)) return tok;
    return tok.split('-').map(p => (/^[a-z]/.test(p) ? p[0].toUpperCase() + p.slice(1) : p)).join('-');
  }).join('');
}
