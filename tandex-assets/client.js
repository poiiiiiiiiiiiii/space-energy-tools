const pendingTandexRequests = new Map();
let tandexWorker;
let nextTandexRequest = 0;
const tandexStartupLimitMs = 90000;

function startTandexWorker() {
  const worker = new Worker('./tandex-assets/worker.mjs', { type: 'module' });
  function fail(message) {
    if (tandexWorker !== worker) return;
    clearTimeout(startupTimer);
    worker.terminate();
    tandexWorker = null;
    for (const finish of pendingTandexRequests.values()) finish({ error: message });
    pendingTandexRequests.clear();
  }
  const startupTimer = setTimeout(() => {
    fail('浏览器计算环境初始化超时，请刷新页面重试。');
  }, tandexStartupLimitMs);
  worker.onmessage = ({ data }) => {
    if (data.type === 'ready') {
      clearTimeout(startupTimer);
    } else if (data.type === 'init-error') {
      fail(data.error);
    } else {
      const finish = pendingTandexRequests.get(data.id);
      pendingTandexRequests.delete(data.id);
      finish?.(data.result);
    }
  };
  worker.onerror = event => fail(event.message || '浏览器计算模块加载失败，请刷新页面重试。');
  return worker;
}

function requestTandex(operation, payload = {}) {
  return new Promise(resolve => {
    if (!tandexWorker) {
      try {
        tandexWorker = startTandexWorker();
      } catch (error) {
        resolve({ error: `浏览器计算模块启动失败：${error.message}` });
        return;
      }
    }
    const id = ++nextTandexRequest;
    pendingTandexRequests.set(id, resolve);
    tandexWorker.postMessage({ id, operation, payload });
  });
}
