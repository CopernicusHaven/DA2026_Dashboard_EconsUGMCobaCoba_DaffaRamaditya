import { useMemo, useState } from 'react';

// sortable table; click a header to sort, click a row (if onRowClick) to open its station
export default function DataTable({ cols, rows, sortKey: sk0 = null, dir: d0 = -1, onRowClick, scroll = false, rowKey }) {
  const [sortKey, setSortKey] = useState(sk0);
  const [dir, setDir] = useState(d0);
  const sorted = useMemo(() => {
    const rs = [...rows];
    if (sortKey) rs.sort((a, b) => { const x = a[sortKey], y = b[sortKey]; if (x == null) return 1; if (y == null) return -1; return (x > y ? 1 : x < y ? -1 : 0) * dir; });
    return rs;
  }, [rows, sortKey, dir]);
  if (!rows.length) return <div className="empty">Tidak ada data pada filter ini.</div>;
  const click = c => { setDir(sortKey === c.key ? -dir : (c.num ? -1 : 1)); setSortKey(c.key); };
  return (
    <div className={'tbl-wrap' + (scroll ? ' tbl-scroll' : '')}>
      <table className="t">
        <thead>
          <tr>
            {cols.map((c, i) => (
              <th key={i} scope="col" tabIndex={0} aria-sort={c.key === sortKey ? (dir > 0 ? 'ascending' : 'descending') : 'none'}
                onClick={() => click(c)} onKeyDown={e => e.key === 'Enter' && click(c)}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((r, i) => (
            <tr key={rowKey ? rowKey(r) : i} className={onRowClick ? 'clickable' : ''} onClick={onRowClick ? () => onRowClick(r) : undefined}>
              {cols.map((c, j) => <td key={j} className={c.num ? 'num' : ''}>{c.render ? c.render(r) : (r[c.key] ?? '–')}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
