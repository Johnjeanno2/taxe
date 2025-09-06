const CACHE_NAME = 'retam-static-v1';
const OFFLINE_DB_NAME = 'retam-offline-db';
const OUTBOX_STORE = 'outbox';

// assets à mettre en cache (ajoute tes CSS/JS/HTML)
const ASSETS = [
  '/',
  '/static/js/offline-sync.js',
  '/static/css/site.css',
];

self.addEventListener('install', (evt) => {
  evt.waitUntil(caches.open(CACHE_NAME).then(c => c.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate', (evt) => {
  evt.waitUntil(self.clients.claim());
});

// fetch fallback to cache
self.addEventListener('fetch', (evt) => {
  const req = evt.request;
  // uniquement GET
  if (req.method !== 'GET') return;
  evt.respondWith(
    fetch(req).catch(() => caches.match(req))
  );
});

// helper IndexedDB simple
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

function getAllOutbox() {
  return openDb().then(db => new Promise((res, rej) => {
    const tx = db.transaction(OUTBOX_STORE, 'readonly');
    const store = tx.objectStore(OUTBOX_STORE);
    const all = store.getAll();
    all.onsuccess = () => res(all.result);
    all.onerror = () => rej(all.error);
  }));
}

function deleteOutboxItem(id) {
  return openDb().then(db => new Promise((res, rej) => {
    const tx = db.transaction(OUTBOX_STORE, 'readwrite');
    tx.objectStore(OUTBOX_STORE).delete(id).onsuccess = () => res();
    tx.onerror = () => rej(tx.error);
  }));
}

// Background Sync: quand le navigateur signale 'sync'
self.addEventListener('sync', (event) => {
  if (event.tag === 'retam-sync-outbox') {
    event.waitUntil(processOutbox());
  }
});

// process outbox: POST each item to server endpoint
async function processOutbox() {
  const items = await getAllOutbox();
  for (const it of items) {
    try {
      const resp = await fetch('/api/offline-sync/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin', // inclut cookies
        body: JSON.stringify(it.payload)
      });
      if (resp.ok) {
        await deleteOutboxItem(it.id);
      } else {
        // si échec côté serveur, garder pour prochaine tentative
        console.warn('sync failed for', it, resp.status);
      }
    } catch (e) {
      console.warn('network error during sync', e);
      return; // sortir, on reverra plus tard
    }
  }
}