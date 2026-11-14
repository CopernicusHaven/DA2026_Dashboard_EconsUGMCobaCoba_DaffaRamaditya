// Minimal stroke icon set (24×24, currentColor)
const P = {
  home: <path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z" />,
  wind: <path d="M3 8h11a3 3 0 1 0-3-3M3 12h16a3 3 0 1 1-3 3M3 16h8" />,
  clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
  sliders: <><path d="M4 6h9M17 6h3M4 12h3M11 12h9M4 18h11M19 18h1" /><circle cx="15" cy="6" r="2" /><circle cx="9" cy="12" r="2" /><circle cx="17" cy="18" r="2" /></>,
  heart: <><path d="M20.8 8.6A5 5 0 0 0 12 5.4a5 5 0 0 0-8.8 3.2C3.2 14 12 20 12 20s8.8-6 8.8-11.4z" /><path d="M3.6 11.5h4l1.8-2.6 2.6 5 1.8-2.4h6.6" /></>,
  network: <><circle cx="12" cy="5" r="2.2" /><circle cx="5" cy="19" r="2.2" /><circle cx="19" cy="19" r="2.2" /><path d="M11 7 6 17M13 7l5 10M7.2 19h9.6" /></>,
  database: <><ellipse cx="12" cy="5" rx="8" ry="3" /><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3" /></>,
  sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>,
  moon: <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />,
  play: <path d="M7 4.5v15l12.5-7.5z" />,
  pause: <path d="M7 4h4v16H7zM13 4h4v16h-4z" />,
  pin: <><path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z" /><circle cx="12" cy="10" r="2.5" /></>,
  layers: <path d="M12 3 2 8l10 5 10-5zM2 13l10 5 10-5" />,
  tower: <><circle cx="12" cy="10" r="2" /><path d="M8.5 6.5a5 5 0 0 0 0 7M15.5 6.5a5 5 0 0 1 0 7M5.6 3.6a9 9 0 0 0 0 12.8M18.4 3.6a9 9 0 0 1 0 12.8M12 12v9" /></>,
  calendar: <><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M3 10h18M8 3v4M16 3v4" /></>,
  cloud: <path d="M7 18h10a4 4 0 0 0 .4-8A6 6 0 0 0 6 9.6 4.3 4.3 0 0 0 7 18z" />,
  refresh: <path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7" />,
  link: <path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1" />,
  chart: <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" />,
  alert: <path d="M12 3 2 20h20zM12 9v5M12 17h.01" />,
  gauge: <path d="M4 18a8 8 0 1 1 16 0M12 18l4-6" />,
  flame: <path d="M12 22c4 0 7-3 7-7 0-5-5-7-5-12-3 2-4 5-4 8-1-1-2-2-2-4-2 2-3 5-3 8 0 4 3 7 7 7z" />,
  trend: <path d="M3 17l6-6 4 4 8-8M14 7h7v7" />,
  check: <><circle cx="12" cy="12" r="9" /><path d="M8 12l3 3 5-6" /></>,
  users: <><circle cx="9" cy="8" r="3.5" /><path d="M2.5 20a6.5 6.5 0 0 1 13 0M16 4.5a3.5 3.5 0 0 1 0 7M18 14a6.5 6.5 0 0 1 3.5 6" /></>,
  map: <path d="M9 4 3 6v14l6-2 6 2 6-2V4l-6 2zM9 4v14M15 6v14" />,
  file: <><path d="M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8z" /><path d="M14 3v5h5M8 13h8M8 17h6" /></>,
  left: <path d="M15 5l-7 7 7 7" />,
  right: <path d="M9 5l7 7-7 7" />,
  down: <path d="M6 9l6 6 6-6" />,
  x: <path d="M6 6l12 12M18 6 6 18" />,
  filter: <path d="M3 5h18l-7 8.5V19l-4 2v-7.5z" />,
  hospital: <><rect x="4" y="3" width="16" height="18" rx="2" /><path d="M12 7v6M9 10h6M9 21v-4h6v4" /></>,
  shield: <><path d="M12 3 4 6v6c0 4.5 3.4 8.3 8 9 4.6-.7 8-4.5 8-9V6z" /><path d="M9 12l2 2 4-4" /></>,
  target: <><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="5" /><circle cx="12" cy="12" r="1" /></>,
  car: <><path d="M5 16V11l2-5h10l2 5v5M3 16h18v3H3z" /><circle cx="7.5" cy="16" r="1.5" /><circle cx="16.5" cy="16" r="1.5" /></>,
  activity: <path d="M3 12h4l3-8 4 16 3-8h4" />,
  tick: <path d="M5 12.5l4.5 4.5L19 7.5" />,
  info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v6M12 7.5h.01" /></>,
};

export default function Icon({ name, size = 18, className = '' }) {
  return (
    <svg className={'ic ' + className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{P[name] || P.chart}</svg>
  );
}
