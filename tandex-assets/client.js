const pendingTandexRequests = new Map();
let tandexWorker;
let nextTandexRequest = 0;

function requestTandex(operation, payload = {}) {
  return new Promise(resolve => {
    if (!tandexWorker) {
      try {
        tandexWorker = new Worker('./tandex-assets/worker.mjs', { type: 'module' });
      } catch (error) {
        resolve({ error: `浏览器计算模块启动失败：${error.message}` });
        return;
      }
      tandexWorker.onmessage = ({ data: { id, result } }) => {
        const finish = pendingTandexRequests.get(id);
        pendingTandexRequests.delete(id);
        finish?.(result);
      };
      tandexWorker.onerror = () => {
        tandexWorker.terminate();
        tandexWorker = null;
        for (const finish of pendingTandexRequests.values()) {
          finish({ error: '浏览器计算模块加载失败，请检查网络并刷新页面。' });
        }
        pendingTandexRequests.clear();
      };
    }
    const id = ++nextTandexRequest;
    pendingTandexRequests.set(id, resolve);
    tandexWorker.postMessage({ id, operation, payload });
  });
}
