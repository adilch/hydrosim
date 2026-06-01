/* app.jsx — HydroSim main window: shell, canvas, connections, interactions, simulation */

const { useState, useRef, useLayoutEffect, useEffect, useCallback } = React;

/* ---- pre-built example model ---- */
const INITIAL_ELEMENTS = [
  { eid: 'ts_rain',  type: 'TimeSeries', name: 'Daily_Rainfall', x: 40,  y: 104 },
  { eid: 'c_coeff',  type: 'Constant',   name: 'RunoffCoeff',    x: 40,  y: 330, value: '0.30' },
  { eid: 'ex_rate',  type: 'Expression', name: 'RunoffRate',     x: 318, y: 204 },
  { eid: 'ws_soil',  type: 'WaterStore', name: 'SoilMoisture',   x: 596, y: 158 },
  { eid: 'th_plot',  type: 'TimeHistoryResult', name: 'Storage_Plot', x: 874, y: 222 },
];

const CONNECTIONS = [
  { from: ['ts_rain', 'value'],   to: ['ex_rate', 'inputs'],   cat: 'input'  },
  { from: ['c_coeff', 'value'],   to: ['ex_rate', 'inputs'],   cat: 'input'  },
  { from: ['ex_rate', 'value'],   to: ['ws_soil', 'inflow'],   cat: 'expr'   },
  { from: ['ws_soil', 'storage'], to: ['th_plot', 'series_1'], cat: 'stock'  },
];

/* sparkline data for the result card preview (short downsample of the hydrograph) */
const FULL_HYDRO = generateHydrograph(366);
const SPARK = FULL_HYDRO.filter((_, i) => i % 9 === 0);

/* ===================== Menu bar ===================== */
const MENUS = {
  File: [
    { label: 'New Model', sc: '⌘N' }, { label: 'Open…', sc: '⌘O' }, { sep: true },
    { label: 'Save', sc: '⌘S' }, { label: 'Save As…', sc: '⇧⌘S' }, { sep: true },
    { label: 'Export…' }, { label: 'Quit', sc: '⌘Q' },
  ],
  Simulation: [
    { label: 'Run', sc: 'F5' }, { label: 'Stop', sc: '⇧F5' }, { sep: true },
    { label: 'Run Settings…' }, { label: 'Clear Results' },
  ],
  View: [
    { label: 'Zoom In', sc: '⌘+' }, { label: 'Zoom Out', sc: '⌘−' }, { label: 'Reset Zoom', sc: '⌘0' }, { sep: true },
    { label: 'Show Grid', check: true }, { label: 'Fit to Window' },
  ],
  Help: [
    { label: 'Documentation' }, { label: 'Keyboard Shortcuts' }, { sep: true }, { label: 'About HydroSim' },
  ],
};

function MenuBar({ openMenu, setOpenMenu, onRun }) {
  return (
    <div className="menubar">
      <div className="brand">
        <svg className="logo" width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M8 1.5C8 1.5 13 7 13 10.4A5 5 0 0 1 3 10.4C3 7 8 1.5 8 1.5Z" fill="#2E86C1"/>
          <path d="M8 1.5C8 1.5 13 7 13 10.4A5 5 0 0 1 3 10.4" fill="#4CAF82" opacity="0.0"/>
        </svg>
        HydroSim
      </div>
      {Object.keys(MENUS).map((m) => (
        <div
          key={m}
          className={'menu-item' + (openMenu === m ? ' open' : '')}
          onClick={(e) => { e.stopPropagation(); setOpenMenu(openMenu === m ? null : m); }}
          onMouseEnter={() => { if (openMenu) setOpenMenu(m); }}
        >
          {m}
          {openMenu === m && (
            <div className="menu-dropdown" onClick={(e) => e.stopPropagation()}>
              {MENUS[m].map((it, i) => it.sep
                ? <div className="sep" key={i}></div>
                : (
                  <div className="row" key={i} onClick={() => { setOpenMenu(null); if (it.label === 'Run') onRun(); }}>
                    <span>{it.check ? '✓ ' : ''}{it.label}</span>
                    {it.sc && <span className="sc mono">{it.sc}</span>}
                  </div>
                ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

/* ===================== Toolbar ===================== */
function Toolbar({ running, progress, onRun, onStop }) {
  const TBtn = ({ children, ...p }) => <button className="tbtn" {...p}>{children}</button>;
  return (
    <div className="toolbar" style={{ position: 'relative' }}>
      <button className="tbtn">
        <svg width="15" height="15" viewBox="0 0 16 16" fill="none"><rect x="2.5" y="2.5" width="11" height="11" rx="2" stroke="currentColor" strokeWidth="1.4"/><path d="M8 5.5v5M5.5 8h5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/></svg>
        New
      </button>
      <button className="tbtn">
        <svg width="15" height="15" viewBox="0 0 16 16" fill="none"><path d="M2 4.5A1.5 1.5 0 0 1 3.5 3h2.8l1.2 1.5h5A1.5 1.5 0 0 1 14 6v6a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/></svg>
        Open
      </button>
      <button className="tbtn">
        <svg width="15" height="15" viewBox="0 0 16 16" fill="none"><path d="M3 2.5h8L13.5 5v8.5a.5.5 0 0 1-.5.5H3a.5.5 0 0 1-.5-.5v-11A.5.5 0 0 1 3 2.5z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/><rect x="5" y="9" width="6" height="4.5" stroke="currentColor" strokeWidth="1.3"/><rect x="5.5" y="3" width="4" height="3" fill="currentColor"/></svg>
        Save
      </button>

      <span className="tbar-divider"></span>

      <button className={'tbtn run' + (running ? ' disabled' : '')} disabled={running} onClick={onRun}>
        <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M4 3.2 13 8l-9 4.8z" fill="currentColor"/></svg>
        {running ? 'Running…' : 'Run'}
      </button>
      <button className={'tbtn stop' + (running ? '' : ' disabled')} disabled={!running} onClick={onStop}>
        <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><rect x="3" y="3" width="10" height="10" rx="1.5" fill="currentColor"/></svg>
        Stop
      </button>

      <span className="tbar-spacer"></span>
      <span className="tbar-meta mono">Δt = 1 day &nbsp;·&nbsp; 365 steps</span>

      {running && <div className="run-progress" style={{ width: (progress * 100) + '%' }}></div>}
    </div>
  );
}

/* ===================== Palette ===================== */
function Palette({ search, setSearch }) {
  const [collapsed, setCollapsed] = useState({});
  const toggle = (c) => setCollapsed((s) => ({ ...s, [c]: !s[c] }));
  const q = search.trim().toLowerCase();

  return (
    <div className="palette">
      <div className="palette-search">
        <div className="search-wrap">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="7" cy="7" r="4.5" stroke="#9CA3AF" strokeWidth="1.5"/><path d="M10.5 10.5 14 14" stroke="#9CA3AF" strokeWidth="1.5" strokeLinecap="round"/></svg>
          <input placeholder="Search elements…" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
      </div>
      <div className="palette-scroll">
        {PALETTE.map((group) => {
          const items = group.items.filter((it) =>
            !q || it.name.toLowerCase().includes(q) || it.desc.toLowerCase().includes(q));
          if (items.length === 0) return null;
          const c = CAT[group.cat];
          const isCollapsed = collapsed[group.cat];
          return (
            <div className="cat" key={group.cat}>
              <div className={'cat-header' + (isCollapsed ? ' collapsed' : '')}
                   style={{ color: c.hex }} onClick={() => toggle(group.cat)}>
                <span className="cat-swatch" style={{ background: c.hex }}></span>
                {c.label}
                <svg className="chev" width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/></svg>
              </div>
              {!isCollapsed && items.map((it) => (
                <div className="pal-item" key={it.type} draggable
                  onDragStart={(e) => { e.dataTransfer.setData('text/plain', it.type); e.currentTarget.classList.add('dragging'); }}
                  onDragEnd={(e) => e.currentTarget.classList.remove('dragging')}>
                  <span className="pal-icon"><Icon kind={it.icon} size={20} color={c.hex} /></span>
                  <div className="pal-text">
                    <div className="pname">{it.name}</div>
                    <div className="pdesc">{it.desc}</div>
                  </div>
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ===================== Connections layer ===================== */
function Connections({ paths }) {
  return (
    <svg className="conn-layer">
      {paths.map((p, i) => (
        <g key={i}>
          <path d={p.d} fill="none" stroke={p.color} strokeWidth="2" strokeOpacity="0.8" />
          <polygon points={p.arrow} fill={p.color} fillOpacity="0.85" />
        </g>
      ))}
    </svg>
  );
}

/* ===================== Canvas ===================== */
function Canvas({ elements, setElements, selectedId, setSelectedId, onOpenDialog, simProgress, zoom, setZoom, pan, setPan }) {
  const contentRef = useRef(null);
  const portEls = useRef({});
  const [paths, setPaths] = useState([]);

  const registerPort = useCallback((eid, port, node) => {
    if (node) portEls.current[eid + ':' + port] = node;
  }, []);

  const measure = useCallback(() => {
    const content = contentRef.current;
    if (!content) return;
    const cr = content.getBoundingClientRect();
    const ptAt = (eid, port) => {
      const node = portEls.current[eid + ':' + port];
      if (!node) return null;
      const r = node.getBoundingClientRect();
      return {
        x: (r.left + r.width / 2 - cr.left) / zoom,
        y: (r.top + r.height / 2 - cr.top) / zoom,
      };
    };
    const next = [];
    for (const conn of CONNECTIONS) {
      const a = ptAt(conn.from[0], conn.from[1]);
      const b = ptAt(conn.to[0], conn.to[1]);
      if (!a || !b) continue;
      const dx = Math.max(46, Math.abs(b.x - a.x) * 0.45);
      const d = `M${a.x},${a.y} C${a.x + dx},${a.y} ${b.x - dx},${b.y} ${b.x},${b.y}`;
      // arrowhead pointing into the input port (rightward)
      const ax = b.x, ay = b.y;
      const arrow = `${ax - 9},${ay - 4.5} ${ax},${ay} ${ax - 9},${ay + 4.5}`;
      next.push({ d, arrow, color: CAT[conn.cat].hex });
    }
    setPaths(next);
  }, [zoom]);

  useLayoutEffect(() => { measure(); }, [elements, zoom, measure]);
  useEffect(() => {
    window.addEventListener('resize', measure);
    return () => window.removeEventListener('resize', measure);
  }, [measure]);

  /* ---- node dragging ---- */
  const dragRef = useRef(null);
  const onNodeDragStart = (e, eid) => {
    if (e.button !== 0) return;
    e.stopPropagation();
    const el = elements.find((x) => x.eid === eid);
    dragRef.current = { eid, sx: e.clientX, sy: e.clientY, ox: el.x, oy: el.y, moved: false };
    const move = (ev) => {
      const dx = (ev.clientX - dragRef.current.sx) / zoom;
      const dy = (ev.clientY - dragRef.current.sy) / zoom;
      if (Math.abs(dx) > 2 || Math.abs(dy) > 2) dragRef.current.moved = true;
      setElements((els) => els.map((x) => x.eid === eid
        ? { ...x, x: dragRef.current.ox + dx, y: dragRef.current.oy + dy, _dragging: true } : x));
    };
    const up = () => {
      setElements((els) => els.map((x) => x.eid === eid ? { ...x, _dragging: false } : x));
      window.removeEventListener('mousemove', move);
      window.removeEventListener('mouseup', up);
    };
    window.addEventListener('mousemove', move);
    window.addEventListener('mouseup', up);
  };

  /* ---- background pan ---- */
  const panRef = useRef(null);
  const onBgDown = (e) => {
    if (e.button !== 0) return;
    setSelectedId(null);
    panRef.current = { sx: e.clientX, sy: e.clientY, px: pan.x, py: pan.y };
    const move = (ev) => setPan({ x: panRef.current.px + ev.clientX - panRef.current.sx, y: panRef.current.py + ev.clientY - panRef.current.sy });
    const up = () => { window.removeEventListener('mousemove', move); window.removeEventListener('mouseup', up); };
    window.addEventListener('mousemove', move);
    window.addEventListener('mouseup', up);
  };

  const onWheel = (e) => {
    if (e.ctrlKey || e.metaKey) {
      e.preventDefault();
      setZoom((z) => Math.max(0.4, Math.min(2, z - e.deltaY * 0.002)));
    }
  };

  /* ---- drop from palette ---- */
  const onDrop = (e) => {
    e.preventDefault();
    const type = e.dataTransfer.getData('text/plain');
    if (!type) return;
    const cr = contentRef.current.getBoundingClientRect();
    const x = (e.clientX - cr.left) / zoom - 90;
    const y = (e.clientY - cr.top) / zoom - 30;
    const n = elements.filter((el) => el.type === type).length + 1;
    const eid = type.slice(0, 2).toLowerCase() + '_' + Math.random().toString(36).slice(2, 5);
    setElements((els) => [...els, {
      eid, type, name: type + '_' + n, x, y,
      value: type === 'Constant' ? '0.00' : undefined,
    }]);
  };

  return (
    <div className="canvas-zone" onMouseDown={onBgDown} onWheel={onWheel}
      onDragOver={(e) => e.preventDefault()} onDrop={onDrop}>
      <div className="canvas-grid"></div>
      <div className="canvas-content" ref={contentRef}
        style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})` }}>
        <Connections paths={paths} />
        {elements.map((el) => (
          <ElementCard key={el.eid} el={el}
            selected={selectedId === el.eid}
            simProgress={simProgress}
            sparkData={SPARK}
            onSelect={setSelectedId}
            onOpenDialog={onOpenDialog}
            onDragStart={onNodeDragStart}
            registerPort={registerPort} />
        ))}
      </div>
    </div>
  );
}

/* ===================== Status bar ===================== */
function StatusBar({ sim, zoom, setZoom }) {
  let pill;
  if (sim.state === 'running') pill = <span className="status-pill run"><span className="dot"></span>Running… step {sim.step} / 365</span>;
  else if (sim.state === 'complete') pill = <span className="status-pill ok"><span className="dot"></span>Simulation complete — 365 steps in {sim.elapsed}</span>;
  else if (sim.state === 'stopped') pill = <span className="status-pill idle"><span className="dot"></span>Stopped at step {sim.step}</span>;
  else pill = <span className="status-pill idle"><span className="dot"></span>Ready</span>;

  return (
    <div className="statusbar statusbar-wrap">
      <div className="left">
        <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M8 2C8 2 12 6.2 12 9a4 4 0 0 1-8 0C4 6.2 8 2 8 2Z" fill="#2E86C1"/></svg>
        <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Simple Water Balance</span>
        <span style={{ color: '#C2C7D0' }}>·</span>
        <span className="mono">5 elements</span>
      </div>
      <div className="center">{pill}</div>
      <div className="right">
        <div className="zoom-ctrl">
          <button onClick={() => setZoom((z) => Math.max(0.4, z - 0.1))}>−</button>
          <span className="mono" style={{ minWidth: 40, textAlign: 'center' }}>{Math.round(zoom * 100)}%</span>
          <button onClick={() => setZoom((z) => Math.min(2, z + 0.1))}>+</button>
        </div>
      </div>
    </div>
  );
}

/* ===================== App ===================== */
function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [elements, setElements] = useState(INITIAL_ELEMENTS);
  const [selectedId, setSelectedId] = useState('ws_soil');
  const [openMenu, setOpenMenu] = useState(null);
  const [dialog, setDialog] = useState(null);   // 'WaterStore' | 'Expression'
  const [viewer, setViewer] = useState(false);
  const [search, setSearch] = useState('');
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });

  const [sim, setSim] = useState({ state: 'complete', step: 365, elapsed: '0.23s' });
  const simTimer = useRef(null);

  const runSim = () => {
    if (sim.state === 'running') return;
    clearInterval(simTimer.current);
    let step = 0;
    const t0 = performance.now();
    setSim({ state: 'running', step: 0, elapsed: '' });
    simTimer.current = setInterval(() => {
      step += 11;
      if (step >= 365) {
        clearInterval(simTimer.current);
        const secs = (0.18 + Math.random() * 0.12).toFixed(2);
        setSim({ state: 'complete', step: 365, elapsed: secs + 's' });
      } else {
        setSim({ state: 'running', step, elapsed: '' });
      }
    }, 36);
  };
  const stopSim = () => {
    clearInterval(simTimer.current);
    setSim((s) => ({ state: 'stopped', step: s.step, elapsed: '' }));
  };
  useEffect(() => () => clearInterval(simTimer.current), []);

  const openDialog = (el) => {
    if (el.type === 'WaterStore') setDialog('WaterStore');
    else if (el.type === 'Expression') setDialog('Expression');
    else if (el.type === 'TimeHistoryResult') setViewer(true);
  };

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') { setDialog(null); setViewer(false); setOpenMenu(null); }
      if (e.key === 'F5') { e.preventDefault(); runSim(); }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [sim.state]);

  const running = sim.state === 'running';
  const progress = running ? sim.step / 365 : 0;

  const shadowMap = {
    flat: '0 1px 2px rgba(0,0,0,0.07)',
    subtle: '0 4px 12px rgba(0,0,0,0.10)',
    floating: '0 10px 26px rgba(0,0,0,0.16)',
  };

  const appStyle = {
    '--card-radius': t.cardRadius + 'px',
    '--card-shadow': shadowMap[t.shadow] || shadowMap.subtle,
    '--grid-spacing': t.gridSpacing + 'px',
    '--grid-dot-size': (t.showGrid ? 1.6 : 0) + 'px',
  };

  return (
    <div className="app" style={appStyle} onClick={() => setOpenMenu(null)}>
      <MenuBar openMenu={openMenu} setOpenMenu={setOpenMenu} onRun={runSim} />
      <Toolbar running={running} progress={progress} onRun={runSim} onStop={stopSim} />
      <div className="body">
        <Palette search={search} setSearch={setSearch} />
        <Canvas
          elements={elements} setElements={setElements}
          selectedId={selectedId} setSelectedId={setSelectedId}
          onOpenDialog={openDialog}
          simProgress={progress}
          zoom={zoom} setZoom={setZoom} pan={pan} setPan={setPan} />
      </div>
      <StatusBar sim={sim} zoom={zoom} setZoom={setZoom} />

      {dialog === 'WaterStore' && <WaterStoreDialog onClose={() => setDialog(null)} />}
      {dialog === 'Expression' && <ExpressionDialog onClose={() => setDialog(null)} />}
      {viewer && <ResultViewer data={FULL_HYDRO} onClose={() => setViewer(false)} />}

      <TweaksPanel>
        <TweakSection label="Canvas" />
        <TweakToggle label="Show dot grid" value={t.showGrid} onChange={(v) => setTweak('showGrid', v)} />
        <TweakSlider label="Grid spacing" value={t.gridSpacing} min={12} max={40} step={2} unit="px"
          onChange={(v) => setTweak('gridSpacing', v)} />
        <TweakSection label="Element cards" />
        <TweakSlider label="Corner radius" value={t.cardRadius} min={0} max={18} unit="px"
          onChange={(v) => setTweak('cardRadius', v)} />
        <TweakRadio label="Shadow depth" value={t.shadow} options={['flat', 'subtle', 'floating']}
          onChange={(v) => setTweak('shadow', v)} />
        <TweakSection label="Try it" />
        <TweakButton label="Re-run simulation" onClick={runSim} />
      </TweaksPanel>
    </div>
  );
}

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "showGrid": true,
  "gridSpacing": 20,
  "cardRadius": 10,
  "shadow": "subtle"
}/*EDITMODE-END*/;

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
