/* elements.jsx — element data, icons, the ElementCard component, connection geometry */

const CAT = {
  input:  { color: 'var(--cat-input)',  hex: '#4CAF82', label: 'INPUT' },
  stock:  { color: 'var(--cat-stock)',  hex: '#2E86C1', label: 'STOCK' },
  expr:   { color: 'var(--cat-expr)',   hex: '#00897B', label: 'EXPRESSION' },
  result: { color: 'var(--cat-result)', hex: '#E8633A', label: 'RESULT' },
};

/* ---- Simple geometric icons (basic shapes only) ---- */
function Icon({ kind, size = 20, color = '#1A1A2E' }) {
  const s = size;
  if (kind === 'timeseries') {
    return (
      <svg width={s} height={s} viewBox="0 0 20 20" fill="none">
        <polyline points="2,13 6,8 9,11 13,4 18,7" stroke={color} strokeWidth="1.8"
          strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="2" cy="13" r="1.4" fill={color} />
        <circle cx="13" cy="4" r="1.4" fill={color} />
      </svg>
    );
  }
  if (kind === 'constant') {
    return (
      <svg width={s} height={s} viewBox="0 0 20 20" fill="none">
        <rect x="4" y="7.4" width="12" height="2" rx="1" fill={color} />
        <rect x="4" y="11" width="12" height="2" rx="1" fill={color} />
      </svg>
    );
  }
  if (kind === 'expression') {
    return (
      <svg width={s} height={s} viewBox="0 0 20 20" fill="none">
        <path d="M12 3.2c-2 0-2.4 1.2-2.7 3.1L7.6 16.2C7.3 18 6.7 18.8 5.2 18.4"
          stroke={color} strokeWidth="1.7" strokeLinecap="round" fill="none" />
        <rect x="6.2" y="8.1" width="6.2" height="1.7" rx="0.85" fill={color} />
      </svg>
    );
  }
  if (kind === 'waterstore') {
    return (
      <svg width={s} height={s} viewBox="0 0 20 20" fill="none">
        <rect x="4" y="3.5" width="12" height="13" rx="2.2" stroke={color} strokeWidth="1.7" />
        <path d="M4.9 10.5h10.2v4.1a1.9 1.9 0 0 1-1.9 1.9H6.8a1.9 1.9 0 0 1-1.9-1.9z" fill={color} opacity="0.85" />
      </svg>
    );
  }
  if (kind === 'result') {
    return (
      <svg width={s} height={s} viewBox="0 0 20 20" fill="none">
        <rect x="3"  y="11" width="3.2" height="6" rx="1" fill={color} />
        <rect x="8.4" y="7" width="3.2" height="10" rx="1" fill={color} />
        <rect x="13.8" y="3.5" width="3.2" height="13.5" rx="1" fill={color} />
      </svg>
    );
  }
  return null;
}
window.Icon = Icon;

/* ---- Palette item descriptors ---- */
const PALETTE = [
  {
    cat: 'input',
    items: [
      { type: 'Constant',   icon: 'constant',   name: 'Constant',   desc: 'A fixed scalar value' },
      { type: 'TimeSeries', icon: 'timeseries', name: 'TimeSeries', desc: 'Time-indexed input data' },
    ],
  },
  {
    cat: 'stock',
    items: [
      { type: 'WaterStore', icon: 'waterstore', name: 'WaterStore', desc: 'Integrates in/outflows' },
    ],
  },
  {
    cat: 'expr',
    items: [
      { type: 'Expression', icon: 'expression', name: 'Expression', desc: 'Evaluates a formula' },
    ],
  },
  {
    cat: 'result',
    items: [
      { type: 'TimeHistoryResult', icon: 'result', name: 'TimeHistoryResult', desc: 'Records a time history' },
    ],
  },
];
window.PALETTE = PALETTE;
window.CAT = CAT;

/* ---- Port metadata per element type ---- */
const PORTS = {
  Constant:          { in: [], out: ['value'] },
  TimeSeries:        { in: [], out: ['value'] },
  Expression:        { in: ['inputs'], out: ['value'] },
  WaterStore:        { in: ['inflow', 'outflow'], out: ['storage', 'overflow', 'deficit'] },
  TimeHistoryResult: { in: ['series_1'], out: [] },
};
window.PORTS = PORTS;

const CAT_OF_TYPE = {
  Constant: 'input', TimeSeries: 'input',
  WaterStore: 'stock', Expression: 'expr', TimeHistoryResult: 'result',
};
window.CAT_OF_TYPE = CAT_OF_TYPE;
const ICON_OF_TYPE = {
  Constant: 'constant', TimeSeries: 'timeseries',
  WaterStore: 'waterstore', Expression: 'expression', TimeHistoryResult: 'result',
};
window.ICON_OF_TYPE = ICON_OF_TYPE;

/* ---- Sparkline path generator (for the result preview card) ---- */
function sparkPath(data, w, h, pad = 2) {
  const min = Math.min(...data), max = Math.max(...data);
  const rng = (max - min) || 1;
  return data.map((v, i) => {
    const x = pad + (i / (data.length - 1)) * (w - pad * 2);
    const y = h - pad - ((v - min) / rng) * (h - pad * 2);
    return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
}
window.sparkPath = sparkPath;

/* ---- The element card ---- */
function ElementCard({ el, selected, simProgress, onSelect, onOpenDialog, onDragStart, registerPort, sparkData }) {
  const cat = CAT_OF_TYPE[el.type];
  const catColor = CAT[cat].hex;
  const ports = PORTS[el.type];

  const portRef = (port) => (node) => registerPort(el.eid, port, node);

  const renderInPort = (p) => (
    <div className="port-row in" key={'in-' + p} style={{ '--port-color': catColor }}>
      <span className="port in" ref={portRef(p)}></span>
      <span className="port-label">{p}</span>
    </div>
  );
  const renderOutPort = (p) => (
    <div className="port-row out" key={'out-' + p} style={{ '--port-color': catColor }}>
      <span className="port-label">{p}</span>
      <span className="port out" ref={portRef(p)}></span>
    </div>
  );

  return (
    <div
      className={'node' + (selected ? ' selected' : '') + (el._dragging ? ' dragging' : '')}
      style={{ left: el.x, top: el.y }}
      onMouseDown={(e) => onDragStart(e, el.eid)}
      onClick={(e) => { e.stopPropagation(); onSelect(el.eid); }}
      onDoubleClick={(e) => { e.stopPropagation(); onOpenDialog(el); }}
    >
      <div className="node-bar" style={{ background: catColor }}></div>
      <div className="node-head">
        <span className="nicon"><Icon kind={ICON_OF_TYPE[el.type]} size={22} color={catColor} /></span>
        <div>
          <div className="node-title">{el.name}</div>
          <div className="node-id mono">{el.eid}</div>
        </div>
      </div>
      <div className="node-divider"></div>

      <div className="node-body">
        {/* type-specific body content */}
        {el.type === 'TimeSeries' && (
          <div className="node-metric"><span className="val mono">mm/day</span><span className="unit">daily series</span></div>
        )}
        {el.type === 'Constant' && (
          <div className="node-metric"><span className="val mono">{el.value}</span><span className="unit">{el.unit || ''}</span></div>
        )}
        {el.type === 'Expression' && (
          <div className="node-formula mono">
            <span className="tok-elem">Daily_Rainfall</span> <span className="tok-op">×</span> <span className="tok-elem">RunoffCoeff</span>
          </div>
        )}
        {el.type === 'WaterStore' && (
          <div className="mini-storage">
            <div className="track"><div className="fill" style={{ width: (80/150*100) + '%' }}></div></div>
            <div className="lbl"><span className="mono">80 mm</span><span className="mono">/ 150 mm</span></div>
          </div>
        )}
        {el.type === 'TimeHistoryResult' && (
          <div className="sparkline">
            <svg width="156" height="34" viewBox="0 0 156 34" style={{ display: 'block' }}>
              <defs>
                <linearGradient id={'spk-' + el.eid} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0" stopColor={catColor} stopOpacity="0.22" />
                  <stop offset="1" stopColor={catColor} stopOpacity="0" />
                </linearGradient>
              </defs>
              <path d={sparkPath(sparkData, 156, 34) + ' L154,32 L2,32 Z'} fill={'url(#spk-' + el.eid + ')'} />
              <path d={sparkPath(sparkData, 156, 34)} fill="none" stroke={catColor} strokeWidth="1.6"
                strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
        )}

        {/* ports */}
        {ports.in.map(renderInPort)}
        {ports.out.map(renderOutPort)}
      </div>
    </div>
  );
}
window.ElementCard = ElementCard;
