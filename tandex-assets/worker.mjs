import { loadPyodide } from 'https://cdn.jsdelivr.net/pyodide/v0.27.7/full/pyodide.mjs';

const modelDirectory = '/tandex';
const assetURL = path => new URL(path, import.meta.url).href;

async function readAsset(path) {
  const response = await fetch(assetURL(path));
  if (!response.ok) throw new Error(`无法加载 ${path} (${response.status})`);
  return response;
}

async function initialize() {
  const [python, manifest] = await Promise.all([
    loadPyodide(),
    readAsset('files.json').then(response => response.json())
  ]);
  const files = ['tandex_core.py', 'tandex_func_02.py', 'tandex_circuit.py',
    ...manifest.map(name => `data/${name}`)];
  await Promise.all([
    python.loadPackage(['numpy', 'scipy', 'pandas', 'matplotlib',
      assetURL('et_xmlfile-2.0.0-py3-none-any.whl'), assetURL('openpyxl-3.1.5-py2.py3-none-any.whl')]),
    ...files.map(async path => {
      const bytes = new Uint8Array(await (await readAsset(path)).arrayBuffer());
      const filename = `${modelDirectory}/${path}`;
      python.FS.mkdirTree(filename.slice(0, filename.lastIndexOf('/')));
      python.FS.writeFile(filename, bytes);
    })
  ]);
  python.runPython("import sys\nsys.path.insert(0, '/tandex')");
  return python.pyimport('tandex_core').calculate;
}

let model;
let queue = Promise.resolve();
self.onmessage = ({ data: { id, operation, payload } }) => {
  queue = queue.then(async () => {
    try {
      model ??= initialize();
      const calculate = await model;
      const result = JSON.parse(calculate(operation, JSON.stringify(payload)));
      self.postMessage({ id, result });
    } catch (error) {
      self.postMessage({ id, result: { error: error.message || String(error) } });
    }
  });
};
