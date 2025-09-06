// fonctions à appeler au submit d'un formulaire : queueRequest(payload)
const OFFLINE_DB_NAME = 'retam-offline-db';
const OUTBOX_STORE = 'outbox';

function openDb() {
  return new Promise((res, rej) => {
    const req = indexedDB.open(OFFLINE_DB_NAME, 1);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(OUTBOX_STORE)) {
        db.createObjectStore(OUTBOX_STORE, { keyPath: 'id', autoIncrement: true });
      }
    };
    req.onsuccess = () => res(req.result);
    req.onerror = () => rej(req.error);
  });
}

function addToOutbox(payload) {
  return openDb().then(db => new Promise((res, rej) => {
    const tx = db.transaction(OUTBOX_STORE, 'readwrite');
    tx.objectStore(OUTBOX_STORE).add({ payload, created_at: Date.now() });
    tx.oncomplete = () => res();
    tx.onerror = () => rej(tx.error);
  }));
}

async function registerSync() {
  if ('serviceWorker' in navigator && 'SyncManager' in window) {
    const reg = await navigator.serviceWorker.ready;
    try {
      await reg.sync.register('retam-sync-outbox');
      return true;
    } catch (e) {
      console.warn('Background Sync registration failed', e);
      return false;
    }
  }
  return false;
}

// public function to call when submitting a form
async function queueRequest(payload) {
  // try online first
  try {
    const r = await fetch('/api/offline-sync/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify(payload)
    });
    if (r.ok) return { online: true };
    // else fallthrough to queue
  } catch (e) {
    // offline or network error -> queue
  }
  await addToOutbox(payload);
  await registerSync();
  return { online: false };
}

// register service worker
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/static/js/sw.js').then(()=> {
    console.log('sw registered');
  }).catch(e => console.warn('sw reg fail', e));
}

// fallback retry: every 60s try to trigger sync via fetch to service worker or call process
setInterval(() => {
  if (navigator.onLine && navigator.serviceWorker) {
    navigator.serviceWorker.ready.then(reg => {
      if (reg.sync) reg.sync.register('retam-sync-outbox').catch(()=>{});
      else {
        // force a fetch to the endpoint to trigger possible processing in sw
        fetch('/api/offline-sync/heartbeat', {method:'GET', credentials:'same-origin'}).catch(()=>{});
      }
    });
  }
}, 60000);