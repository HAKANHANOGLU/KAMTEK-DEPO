// Kamtek Depo - minimal PWA service worker.
// Streamlit sayfaları sunucudan canlı (websocket) geldiği için tam offline
// çalışma desteklenmiyor; bu worker "yüklenebilir uygulama" (installable)
// deneyimini ve güncelleme bildirimi akışını sağlıyor.
//
// GUNCELLEME AKISI: yeni bir surum yayinlarken CACHE_NAME'i degistirin
// (ornegin v1 -> v2). Tarayici bu dosyanin byte'larinin degistigini fark
// edince yeni worker'i "waiting" durumunda kurar; sayfadaki kod bunu
// yakalayip kullaniciya "Guncelle" bildirimi gosterir. Kullanici tikladiginda
// SKIP_WAITING mesaji gonderilir, yeni worker aktif olur ve sayfa yeniden
// yuklenir.
const CACHE_NAME = "kamtek-depo-shell-v68";
const SHELL_ASSETS = [
  "/app/static/manifest.json",
  "/app/static/icons/pwa-192x192.png",
  "/app/static/icons/pwa-512x512.png",
  "/app/static/icons/maskable-icon-512x512.png",
  "/app/static/icons/apple-touch-icon-180x180.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_ASSETS))
  );
  // Kasıtlı olarak self.skipWaiting() ÇAĞRILMIYOR: yeni worker "waiting"
  // durumunda bekleyecek ki sayfa kullanıcıya güncelleme bildirimi
  // gösterebilsin. Aktifleşme, kullanıcı "Güncelle"ye basınca gelen
  // SKIP_WAITING mesajıyla tetiklenir.
});

self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  // Sadece kendi statik varlıklarımızı önbellekten karşıla; geri kalan her şeyi
  // (Streamlit'in canlı sayfası, websocket, Supabase, DIA XML) doğrudan ağa bırak.
  if (url.pathname.startsWith("/app/static/")) {
    event.respondWith(
      caches.match(event.request).then((cached) => cached || fetch(event.request))
    );
  }
});
