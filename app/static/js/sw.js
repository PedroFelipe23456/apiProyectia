// Service worker: permite instalar la app. Solo guarda en caché archivos
// estáticos (/static/...). Las consultas a la API NUNCA se cachean.
const CACHE = "powermonitor-v1";
self.addEventListener("install", (e) => { self.skipWaiting(); });
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener("fetch", (e) => {
  const req = e.request;
  const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== location.origin) return;
  if (!url.pathname.startsWith("/static/")) return;   // API y HTML: siempre red
  e.respondWith(
    fetch(req).then((r) => {
      const copia = r.clone();
      caches.open(CACHE).then((c) => c.put(req, copia)).catch(() => {});
      return r;
    }).catch(() => caches.match(req))
  );
});
