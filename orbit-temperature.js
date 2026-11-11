const STEFAN_BOLTZMANN = 5.670367e-8;
const SOLAR_CONSTANT = 1367;
const ENVIRONMENT_K = 2.7;
const SAMPLE_SECONDS = 60;
const MAX_INTEGRATION_SECONDS = 5;
const ORBITS = {
  leo400: { minutes: 90, sunlit: 0.6 },
  leo2000: { minutes: 120, sunlit: 0.7 },
  'dawn-dusk': { minutes: 96, sunlit: 1 },
  geo: { minutes: 1440, sunlit: 0.9 },
  sso: { minutes: 99, sunlit: 0.8 }
};
const thermalElement = id => document.getElementById(id);
const thermalForm = thermalElement('thermalForm');
const thermalStatus = thermalElement('status');
const exportButton = thermalElement('export-btn');
let simulationData = null;

function orbitIntervals(orbit, count) {
  const period = orbit.minutes * 60;
  const intervals = [];
  for (let i = 0; i < count; i++) {
    const start = i * period;
    const end = (i + 1) * period;
    const dusk = start + orbit.sunlit * period;
    intervals.push({ start, end: dusk, irradiance: SOLAR_CONSTANT });
    if (dusk < end) intervals.push({ start: dusk, end, irradiance: 0 });
  }
  return intervals;
}

function thermalStep(temperature, dt, irradiance, cell) {
  const gain = irradiance * cell.absorptivity * (1 - cell.efficiency);
  const slope = t => (gain - cell.emissivity * STEFAN_BOLTZMANN * (t ** 4 - ENVIRONMENT_K ** 4)) / cell.capacity;
  const a = slope(temperature);
  const b = slope(temperature + dt * a / 2);
  const c = slope(temperature + dt * b / 2);
  const d = slope(temperature + dt * c);
  return temperature + dt * (a + 2 * b + 2 * c + d) / 6;
}

function solveOrbit(orbit, count, initialC, silicon, perovskite) {
  const intervals = orbitIntervals(orbit, count);
  const time = [], siTemp = [], perovskiteTemp = [], irradiance = [];
  const duration = orbit.minutes * 60 * count;
  let t = 0, interval = 0;
  let siK = initialC + 273.15, pvK = siK;
  const advanceInterval = () => {
    if (interval < intervals.length - 1 && t >= intervals[interval].end) interval++;
  };

  for (let target = 0; target <= duration; target += SAMPLE_SECONDS) {
    // Step to the exact eclipse boundary before changing the heat input.
    while (t < target) {
      advanceInterval();
      const active = intervals[interval];
      const end = Math.min(target, active.end, t + MAX_INTEGRATION_SECONDS);
      const dt = end - t;
      siK = thermalStep(siK, dt, active.irradiance, silicon);
      pvK = thermalStep(pvK, dt, active.irradiance, perovskite);
      t = end;
    }
    advanceInterval();
    time.push(target / 60);
    siTemp.push(target === 0 ? initialC : siK - 273.15);
    perovskiteTemp.push(target === 0 ? initialC : pvK - 273.15);
    irradiance.push(intervals[interval].irradiance);
  }
  return { time, siTemp, perovskiteTemp, irradiance, intervals };
}

const eclipseBands = {
  id: 'eclipseBands',
  beforeDatasetsDraw(chart, _args, options) {
    if (!options.intervals?.length) return;
    const { ctx, chartArea, scales: { x } } = chart;
    ctx.save();
    ctx.fillStyle = '#e7eef6';
    for (const { start, end } of options.intervals) {
      const left = Math.max(chartArea.left, x.getPixelForValue(start / 60));
      const right = Math.min(chartArea.right, x.getPixelForValue(end / 60));
      if (right > left) ctx.fillRect(left, chartArea.top, right - left, chartArea.height);
    }
    ctx.restore();
  }
};

function line(label, color, data, fill) {
  return { label, data, borderColor: color, backgroundColor: fill || color,
    borderWidth: 2, pointRadius: 0, pointHoverRadius: 4, tension: 0, fill: !!fill };
}

function drawThermalChart(id, datasets, xTitle, yTitle, options = {}) {
  const canvas = thermalElement(id);
  const chart = Chart.getChart(canvas);
  if (chart) chart.destroy();
  new Chart(canvas, {
    type: 'line',
    data: { datasets },
    plugins: [eclipseBands],
    options: {
      responsive: true, maintainAspectRatio: false, animation: false, parsing: false,
      interaction: { mode: 'index', intersect: false, axis: 'x' },
      scales: {
        x: { type: 'linear', title: { display: true, text: xTitle }, grid: { display: false }, ticks: { maxTicksLimit: 8 } },
        y: { title: { display: true, text: yTitle }, beginAtZero: !!options.beginAtZero, ticks: { maxTicksLimit: 6 } }
      },
      plugins: {
        legend: { display: datasets.length > 1, labels: { usePointStyle: true, boxWidth: 10, boxHeight: 8 } },
        eclipseBands: { intervals: options.intervals },
        tooltip: { callbacks: {
          title: items => items.length ? `${Number(items[0].parsed.x.toFixed(2))} ${options.xUnit || 'min'}` : '',
          afterTitle: items => options.phase && items.length ?
            (options.phase[items[0].dataIndex] ? '日照' : '地影') : '',
          label: item => `${item.dataset.label}: ${Number(item.parsed.y.toFixed(2))}${options.yUnit || ''}`
        } }
      }
    }
  });
}

function runThermalSimulation() {
  const fields = [...thermalForm.querySelectorAll('input')];
  let invalid = null;
  for (const input of fields) {
    const valid = input.validity.valid && Number.isFinite(input.valueAsNumber);
    input.setAttribute('aria-invalid', String(!valid));
    if (!valid && !invalid) invalid = input;
  }
  if (invalid) {
    thermalStatus.textContent = '参数超出范围，保留上一轮结果。';
    thermalStatus.dataset.error = 'true';
    exportButton.disabled = true;
    invalid.focus();
    return;
  }
  const number = id => thermalElement(id).valueAsNumber;
  const cell = id => ({ emissivity: number(`${id}-emissivity`), absorptivity: number(`${id}-absorptivity`),
    efficiency: number(`${id}-efficiency`), capacity: number(`${id}-heat-capacity`) });
  const orbit = ORBITS[thermalElement('orbit-type').value];
  const count = number('orbits');
  simulationData = solveOrbit(orbit, count, number('initialTemp'), cell('si'), cell('perovskite'));
  const { time, siTemp, perovskiteTemp, irradiance, intervals } = simulationData;
  const points = values => time.map((x, i) => ({ x, y: values[i] }));
  const shadows = intervals.filter(interval => interval.irradiance === 0);
  drawThermalChart('temperature-chart', [line('晶硅', '#255fa8', points(siTemp)), line('钙钛矿', '#ae5d10', points(perovskiteTemp))],
    '时间 (min)', '温度 (°C)', { intervals: shadows, phase: irradiance, yUnit: ' °C' });

  const irradianceSteps = intervals.flatMap(interval => [
    { x: interval.start / 60, y: interval.irradiance }, { x: interval.end / 60, y: interval.irradiance }
  ]);
  drawThermalChart('irradiance-chart', [line('辐照度', '#b4751c', irradianceSteps, '#efd9b780')],
    '时间 (min)', '辐照度 (W/m²)', { intervals: shadows, beginAtZero: true, yUnit: ' W/m²' });

  const range = values => `${Math.min(...values).toFixed(1)} ~ ${Math.max(...values).toFixed(1)}`;
  thermalElement('periodMetric').value = orbit.minutes;
  thermalElement('eclipseMetric').value = Number((orbit.minutes * (1 - orbit.sunlit)).toFixed(2));
  thermalElement('siRange').value = range(siTemp);
  thermalElement('pvRange').value = range(perovskiteTemp);
  thermalStatus.textContent = `模拟完成 · ${count} 圈 · ${time.length} 个采样点`;
  thermalStatus.dataset.error = 'false';
  exportButton.disabled = false;
}

thermalForm.addEventListener('submit', event => {
  event.preventDefault();
  runThermalSimulation();
});
thermalForm.addEventListener('input', event => {
  event.target.removeAttribute('aria-invalid');
  exportButton.disabled = true;
  thermalStatus.textContent = '参数已修改，当前图表仍为上一轮结果。';
  thermalStatus.dataset.error = 'false';
});
exportButton.addEventListener('click', () => {
  const { time, siTemp, perovskiteTemp, irradiance } = simulationData;
  const rows = time.map((t, i) => [t.toFixed(2), siTemp[i].toFixed(2), perovskiteTemp[i].toFixed(2), irradiance[i].toFixed(2)].join(','));
  const url = URL.createObjectURL(new Blob(['\ufeff时间(分钟),晶硅电池温度(℃),钙钛矿电池温度(℃),辐照强度(W/m²)\r\n',
    rows.join('\r\n'), '\r\n'], { type: 'text/csv;charset=utf-8' }));
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = 'solar_cell_temperature_data.csv';
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});

Chart.defaults.font.family = "system-ui, 'Microsoft YaHei', sans-serif";
Chart.defaults.color = '#4f666c';
const illustration = Array.from({ length: 161 }, (_, i) => {
  const x = 300 + 5 * i;
  return { x, y: Math.exp(-(((x - 500) / 150) ** 2)) };
});
drawThermalChart('spectrum-chart', [line('相对强度', '#08766d', illustration, '#c8e7df80')],
  '波长 (nm)', '相对强度', { beginAtZero: true, xUnit: 'nm' });
runThermalSimulation();
