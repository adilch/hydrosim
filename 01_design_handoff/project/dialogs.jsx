/* dialogs.jsx — WaterStore & Expression property dialogs */

function Field({ label, children }) {
  return (
    <div className="field">
      <label>{label}</label>
      {children}
    </div>
  );
}

/* ---------- WaterStore property dialog ---------- */
function WaterStoreDialog({ onClose }) {
  const [name, setName] = React.useState('SoilMoisture');
  const [desc, setDesc] = React.useState('Root-zone soil moisture store');
  const [units, setUnits] = React.useState('mm');
  const [initial, setInitial] = React.useState('80');
  const [lower, setLower] = React.useState('0');
  const [upper, setUpper] = React.useState('150');

  const lo = parseFloat(lower) || 0;
  const hi = parseFloat(upper) || 1;
  const cur = parseFloat(initial) || 0;
  const pct = Math.max(0, Math.min(100, ((cur - lo) / (hi - lo)) * 100));

  return (
    <div className="overlay" onMouseDown={onClose}>
      <div className="dialog" style={{ width: 500 }} onMouseDown={(e) => e.stopPropagation()}>
        <div className="dialog-head">
          <span className="dicon" style={{ background: '#E3F0FA' }}>
            <Icon kind="waterstore" size={20} color="#2E86C1" />
          </span>
          <div>
            <div className="dt">WaterStore — SoilMoisture</div>
            <div className="dsub">Stock element · integrates inflow − outflow</div>
          </div>
          <button className="xbtn" onClick={onClose}>✕</button>
        </div>

        <div className="dialog-body">
          <Field label="Name">
            <input className="input mono" value={name} onChange={(e) => setName(e.target.value)} />
          </Field>
          <Field label="Description">
            <input className="input" value={desc} onChange={(e) => setDesc(e.target.value)} />
          </Field>
          <Field label="Units">
            <input className="input" style={{ maxWidth: 140 }} value={units} onChange={(e) => setUnits(e.target.value)} />
          </Field>

          <div className="field-grid">
            <Field label="Initial Storage">
              <div className="suffix-wrap">
                <input className="input mono" value={initial} onChange={(e) => setInitial(e.target.value)} />
                <span className="suffix">{units}</span>
              </div>
            </Field>
            <div></div>
            <Field label="Lower Bound">
              <div className="suffix-wrap">
                <input className="input mono" value={lower} onChange={(e) => setLower(e.target.value)} />
                <span className="suffix">{units}</span>
              </div>
            </Field>
            <Field label="Upper Bound">
              <div className="suffix-wrap">
                <input className="input mono" value={upper} onChange={(e) => setUpper(e.target.value)} />
                <span className="suffix">{units}</span>
              </div>
            </Field>
          </div>

          <Field label="Storage range">
            <div className="storage-indicator">
              <div className="si-track">
                <div className="si-fill" style={{ width: pct + '%' }}>
                  <span className="si-val mono">{cur} {units}</span>
                </div>
              </div>
              <div className="si-scale">
                <span className="mono">{lo} {units}</span>
                <span>initial {cur} of {hi} {units}</span>
                <span className="mono">{hi} {units}</span>
              </div>
            </div>
          </Field>
        </div>

        <div className="dialog-foot">
          <button className="btn" onClick={onClose}>Cancel</button>
          <button className="btn primary" onClick={onClose}>OK</button>
        </div>
      </div>
    </div>
  );
}
window.WaterStoreDialog = WaterStoreDialog;

/* ---------- Expression property dialog ---------- */
function ExpressionDialog({ onClose }) {
  const [name, setName] = React.useState('RunoffRate');
  const [desc, setDesc] = React.useState('Rainfall converted to runoff depth');
  const [outUnits, setOutUnits] = React.useState('mm/day');
  const [tested, setTested] = React.useState(false);

  const elements = [
    { name: 'Daily_Rainfall', port: 'value' },
    { name: 'RunoffCoeff', port: 'value' },
  ];

  return (
    <div className="overlay" onMouseDown={onClose}>
      <div className="dialog" style={{ width: 600 }} onMouseDown={(e) => e.stopPropagation()}>
        <div className="dialog-head">
          <span className="dicon" style={{ background: '#E0F2F1' }}>
            <Icon kind="expression" size={20} color="#00897B" />
          </span>
          <div>
            <div className="dt">Expression — RunoffRate</div>
            <div className="dsub">Evaluated each timestep</div>
          </div>
          <button className="xbtn" onClick={onClose}>✕</button>
        </div>

        <div className="dialog-body">
          <div className="field-grid">
            <Field label="Name">
              <input className="input mono" value={name} onChange={(e) => setName(e.target.value)} />
            </Field>
            <Field label="Output Units">
              <input className="input" value={outUnits} onChange={(e) => setOutUnits(e.target.value)} />
            </Field>
          </div>
          <Field label="Description">
            <input className="input" value={desc} onChange={(e) => setDesc(e.target.value)} />
          </Field>

          <Field label="Formula">
            <div className="formula-editor">
              <div className="fe-gutter mono">
                <span>ƒ(x)</span><span>·</span><span>expression</span>
              </div>
              <div className="fe-body mono">
                <div className="fe-lines">1</div>
                <div className="fe-code">
                  <span className="tok-elem">Daily_Rainfall</span>
                  {' '}<span className="tok-op">*</span>{' '}
                  <span className="tok-elem">RunoffCoeff</span>
                </div>
              </div>
            </div>
          </Field>

          <Field label="Available Elements">
            <div className="chips">
              {elements.map((e) => (
                <span className="chip mono" key={e.name}>
                  <span className="cdot"></span>
                  <span className="cname">{e.name}</span>
                  <span className="cport">.{e.port}</span>
                </span>
              ))}
            </div>
          </Field>

          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 4 }}>
            <button className="btn" onClick={() => setTested(true)}>Test</button>
            {tested && (
              <span className="test-pill">
                result = <span className="mono">3.69 mm/day</span>
              </span>
            )}
          </div>
        </div>

        <div className="dialog-foot">
          <button className="btn" onClick={onClose}>Cancel</button>
          <button className="btn primary" onClick={onClose}>OK</button>
        </div>
      </div>
    </div>
  );
}
window.ExpressionDialog = ExpressionDialog;
