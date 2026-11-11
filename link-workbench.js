const element = id => document.getElementById(id);
const form = element('linkForm');
const canvas = element('chartContainer');
const status = element('linkStatus');
const fields = [...form.querySelectorAll('input')];
const outputIds = ['actualEfficiency', 'captureEfficiency', 'receivedPower', 'outputPower', 'beamWavelength',
  'spotDiameter', 'receiverReadout', 'd2lResult', 'l2lResult', 'l2dResult', 'allPCE', 'spotSize', 'receiverArea'];
let solution = null;
let pceWindow = null;

function solveLink(values) {
  const apertureRadius = values.beamDiameter / 2;
  const divergence = values.beamQuality * 1e-6 / apertureRadius;
  const spotRadius = divergence * values.distance * 1000;
  const receiverRadius = values.receiverDiameter / 2;
  const capture = Math.min(1, (receiverRadius / spotRadius) ** 2);
  const transmit = values.dcacEfficiency / 100 * values.d2lEfficiency / 100;
  const path = (1 - values.trackingLoss / 100) * values.l2lEfficiency / 100;
  const conversion = values.pceEfficiency / 100;
  const theoretical = transmit * path * conversion;
  const received = values.power * path * capture;
  const result = {
    actualEfficiency: theoretical * capture * 100,
    captureEfficiency: capture * 100,
    receivedPower: received,
    outputPower: received * conversion,
    beamWavelength: values.wavelength,
    spotDiameter: spotRadius * 2,
    receiverReadout: values.receiverDiameter,
    d2lResult: transmit * 100,
    l2lResult: path * 100,
    l2dResult: values.pceEfficiency,
    allPCE: theoretical * 100,
    spotSize: Math.PI * spotRadius ** 2,
    receiverArea: Math.PI * receiverRadius ** 2
  };
  return spotRadius > 0 && Object.values(result).every(Number.isFinite) ? result : null;
}

function paintBeam() {
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  if (!width || !height) return;
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const w = Math.round(width * dpr);
  const h = Math.round(height * dpr);
  if (canvas.width !== w || canvas.height !== h) {
    canvas.width = w;
    canvas.height = h;
  }
  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.fillStyle = '#13272d';
  ctx.fillRect(0, 0, width, height);
  const cx = width / 2;
  const cy = height / 2;
  ctx.strokeStyle = '#284047';
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let x = cx % 24; x < width; x += 24) { ctx.moveTo(x, 0); ctx.lineTo(x, height); }
  for (let y = cy % 24; y < height; y += 24) { ctx.moveTo(0, y); ctx.lineTo(width, y); }
  ctx.stroke();
  if (!solution) return;
  const scale = (Math.min(width, height) - 40) / Math.max(solution.spotDiameter, solution.receiverReadout);
  const circle = (diameter, fill, stroke, dashed) => {
    if (!diameter) return;
    ctx.beginPath();
    ctx.arc(cx, cy, diameter * scale / 2, 0, 2 * Math.PI);
    if (fill) { ctx.fillStyle = fill; ctx.fill(); }
    ctx.strokeStyle = stroke;
    ctx.setLineDash(dashed ? [6, 4] : []);
    ctx.lineWidth = 2;
    ctx.stroke();
  };
  circle(solution.spotDiameter, '#b27a354f', '#f9bb64', false);
  circle(solution.receiverReadout, null, '#68e1d0', true);
  ctx.setLineDash([]);
}

function renderLink() {
  const values = {};
  let invalidField = null;
  for (const field of fields) {
    const valid = field.validity.valid && Number.isFinite(field.valueAsNumber);
    field.setAttribute('aria-invalid', String(!valid));
    if (!valid && !invalidField) invalidField = field;
    values[field.id] = field.valueAsNumber;
  }
  solution = invalidField ? null : solveLink(values);
  status.dataset.error = String(!solution);
  status.textContent = invalidField ? '请检查标出的数值范围。' : solution ? '' : '参数超出可计算范围。';
  for (const id of outputIds) {
    const value = solution?.[id];
    const digits = id === 'spotDiameter' || id === 'receiverReadout' ? 3 : 2;
    element(id).value = value == null ? '--' : id === 'beamWavelength' ? `${value} nm` : value.toFixed(digits);
  }
  paintBeam();
  return invalidField;
}

form.addEventListener('input', renderLink);
form.addEventListener('submit', event => {
  event.preventDefault();
  renderLink()?.focus();
});
element('calculatePCE').addEventListener('click', () => {
  pceWindow = window.open('bec.html', `solarPCE_${Date.now()}`, 'width=1200,height=900');
  if (!pceWindow) status.textContent = '计算器窗口被浏览器拦截。';
});
window.addEventListener('message', event => {
  if (!pceWindow || event.source !== pceWindow) return;
  if (event.origin !== location.origin && !(location.protocol === 'file:' && event.origin === 'null')) return;
  const value = event.data?.pce;
  if (event.data?.type !== 'solarPCE' || !['string', 'number'].includes(typeof value) || String(value).trim() === '') return;
  const pce = Number(value);
  if (!Number.isFinite(pce) || pce < 0 || pce > 100) return;
  element('pceEfficiency').value = pce;
  renderLink();
});

new ResizeObserver(paintBeam).observe(canvas);
renderLink();
