/* viewer.jsx — TimeHistoryResult floating window with a matplotlib-style hydrograph */

/* Deterministic placeholder soil-moisture series (365 daily values, 0–150 mm).
   Wet-season recharge + dry-season depletion with light texture.
   Swap this out for real data later. */
function generateHydrograph(n = 366) {
  const out = [];
  let s = 80;
  for (let i = 0; i < n; i++) {
    // seasonal forcing: wet in days ~300–80 (austral-ish year), dry mid-year
    const season = Math.cos((i / 365) * 2 * Math.PI);   // +1 around day 0/365, -1 mid
    const recharge = Math.max(0, season) * 1.7;
    const evap = 0.9 + Math.max(0, -season) * 1.4;
    // pseudo-random storm pulses (deterministic)
    const r = Math.sin(i * 12.9898) * 43758.5453;
    const storm = ((r - Math.floor(r)) > 0.86 ? (Math.abs(Math.sin(i)) * 9) : 0) * Math.max(0.15, season + 0.4);
    s += recharge + storm - evap;
    s = Math.max(6, Math.min(148, s));
    out.push(s);
  }
  return out;
}
window.generateHydrograph = generateHydrograph;

function Hydrograph({ data, width, height }) {
  const m = { l: 52, r: 18, t: 14, b: 40 };
  const iw = width - m.l - m.r;
  const ih = height - m.t - m.b;
  const xmax = data.length - 1;        // ~365
  const ymax = 150;

  const xToPx = (i) => m.l + (i / xmax) * iw;
  const yToPx = (v) => m.t + ih - (v / ymax) * ih;

  const yTicks = [0, 30, 60, 90, 120, 150];
  const xTicks = [0, 60, 120, 180, 240, 300, 365];

  const line = data.map((v, i) => `${i === 0 ? 'M' : 'L'}${xToPx(i).toFixed(1)},${yToPx(v).toFixed(1)}`).join(' ');
  const area = line + ` L${xToPx(xmax).toFixed(1)},${yToPx(0)} L${xToPx(0).toFixed(1)},${yToPx(0)} Z`;

  return (
    <svg width={width} height={height} style={{ display: 'block' }}>
      <defs>
        <linearGradient id="hg-fill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#2E86C1" stopOpacity="0.18" />
          <stop offset="1" stopColor="#2E86C1" stopOpacity="0" />
        </linearGradient>
      </defs>

      {/* plot frame */}
      <rect x={m.l} y={m.t} width={iw} height={ih} fill="#FFFFFF" stroke="#E5E7EB" />

      {/* horizontal grid + y labels */}
      {yTicks.map((t) => (
        <g key={'y' + t}>
          <line x1={m.l} y1={yToPx(t)} x2={m.l + iw} y2={yToPx(t)} stroke="#EEF0F4" strokeWidth="1" />
          <text x={m.l - 9} y={yToPx(t) + 3.5} textAnchor="end" fontSize="10.5" fill="#6B7280" fontFamily="Fira Code, monospace">{t}</text>
        </g>
      ))}
      {/* vertical grid + x labels */}
      {xTicks.map((t) => (
        <g key={'x' + t}>
          <line x1={xToPx(t)} y1={m.t} x2={xToPx(t)} y2={m.t + ih} stroke="#F3F4F7" strokeWidth="1" />
          <text x={xToPx(t)} y={m.t + ih + 16} textAnchor="middle" fontSize="10.5" fill="#6B7280" fontFamily="Fira Code, monospace">{t}</text>
        </g>
      ))}

      {/* axis titles */}
      <text x={m.l + iw / 2} y={height - 6} textAnchor="middle" fontSize="11.5" fill="#1A1A2E" fontWeight="600">Time (days)</text>
      <text x={14} y={m.t + ih / 2} textAnchor="middle" fontSize="11.5" fill="#1A1A2E" fontWeight="600"
        transform={`rotate(-90 14 ${m.t + ih / 2})`}>Storage (mm)</text>

      {/* data */}
      <path d={area} fill="url(#hg-fill)" />
      <path d={line} fill="none" stroke="#2E86C1" strokeWidth="1.8" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}

function ResultViewer({ data, onClose }) {
  const [pos, setPos] = React.useState({ x: Math.max(40, (window.innerWidth - 800) / 2), y: 110 });
  const drag = React.useRef(null);
  const W = 800, H = 500;

  const onTitleDown = (e) => {
    drag.current = { sx: e.clientX, sy: e.clientY, px: pos.x, py: pos.y };
    const move = (ev) => {
      if (!drag.current) return;
      setPos({
        x: Math.max(0, drag.current.px + ev.clientX - drag.current.sx),
        y: Math.max(0, drag.current.py + ev.clientY - drag.current.sy),
      });
    };
    const up = () => { drag.current = null; window.removeEventListener('mousemove', move); window.removeEventListener('mouseup', up); };
    window.addEventListener('mousemove', move);
    window.addEventListener('mouseup', up);
  };

  const chartH = H - 40 /*titlebar*/ - 46 /*toolbar*/ - 6;
  const chartW = W - 36;

  return (
    <div className="float-win" style={{ left: pos.x, top: pos.y, width: W, height: H }}>
      <div className="win-titlebar" onMouseDown={onTitleDown}>
        <span className="win-dot"></span>
        <span className="win-title">Storage_Plot — Results</span>
        <div className="win-actions">
          <button className="btn primary" style={{ padding: '5px 12px', fontSize: 12 }}>Export CSV</button>
          <button className="win-x" onClick={onClose}>✕</button>
        </div>
      </div>

      <div className="chart-wrap">
        <div className="chart-legend">
          <span className="swatch"></span>
          <span className="mono">SoilMoisture.storage</span>
        </div>
        <Hydrograph data={data} width={chartW} height={chartH} />
      </div>

      <div className="chart-toolbar">
        <button className="ctbtn" title="Home / reset view">
          <svg width="15" height="15" viewBox="0 0 16 16" fill="none"><path d="M2 7.5 8 2.5l6 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/><path d="M3.6 7v6.2h8.8V7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
        </button>
        <button className="ctbtn" title="Pan">
          <svg width="15" height="15" viewBox="0 0 16 16" fill="none"><path d="M8 1.5v13M1.5 8h13M5 4.5 8 1.5l3 3M5 11.5 8 14.5l3-3M4.5 5 1.5 8l3 3M11.5 5l3 3-3 3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/></svg>
        </button>
        <button className="ctbtn" title="Zoom to rectangle">
          <svg width="15" height="15" viewBox="0 0 16 16" fill="none"><circle cx="7" cy="7" r="4.5" stroke="currentColor" strokeWidth="1.5"/><path d="M10.5 10.5 14 14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
        </button>
        <span className="sep"></span>
        <button className="ctbtn" title="Save figure as PNG">
          <svg width="15" height="15" viewBox="0 0 16 16" fill="none"><path d="M3 2.5h7L13 5.5V13a.5.5 0 0 1-.5.5h-9A.5.5 0 0 1 3 13z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/><rect x="5.2" y="8.5" width="5.6" height="5" rx="0.5" stroke="currentColor" strokeWidth="1.3"/></svg>
        </button>
        <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-secondary)' }} className="mono">365 steps · Δt = 1 day</span>
      </div>
    </div>
  );
}
window.ResultViewer = ResultViewer;
