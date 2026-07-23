/**
 * Đặc Sản Phố — Service Worker
 * Caching strategy: Stale-While-Revalidate for pages, Cache-First for assets
 */
const CACHE_NAME = "dacsanpho-v2";
const ASSETS_CACHE = "dacsanpho-assets-v2";
const OFFLINE_URL = "/offline/";

// ── Install: Pre-cache critical assets ──
self.addEventListener("install", (event) => {
  const preCache = async () => {
    const cache = await caches.open(CACHE_NAME);
    return cache.addAll([
      "/",
      "/offline/",
      "/css/style.css",
      "/js/search.js",
      "/manifest.json",
      "/icons/icon-192.png",
      "/icons/icon-512.png",
      "/icons/og-image.png",
    ]);
  };
  event.waitUntil(preCache());
  self.skipWaiting();
});

// ── Activate: Clean old caches ──
self.addEventListener("activate", (event) => {
  const cleanOld = async () => {
    const keys = await caches.keys();
    await Promise.all(
      keys
        .filter((k) => k !== CACHE_NAME && k !== ASSETS_CACHE)
        .map((k) => caches.delete(k))
    );
    await clients.claim();
  };
  event.waitUntil(cleanOld());
});

// ── Fetch: Stale-While-Revalidate ──
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Only handle same-origin requests
  if (url.origin !== self.location.origin) return;

  // Skip non-GET
  if (request.method !== "GET") return;

  // Skip API/data calls (let them go through)
  if (url.pathname.startsWith("/data/")) return;

  // Strategy: Network first for HTML, Cache first for static assets
  if (request.destination === "document") {
    event.respondWith(networkFirst(request));
  } else {
    event.respondWith(cacheFirst(request));
  }
});

// ── Network First (for HTML pages) ──
async function networkFirst(request) {
  try {
    const response = await fetch(request);
    const cache = await caches.open(CACHE_NAME);
    cache.put(request, response.clone());
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;
    // Offline fallback
    const cache = await caches.open(CACHE_NAME);
    const fallback = await cache.match("/offline/");
    return fallback || new Response("Offline — Vui lòng kết nối mạng", {
      status: 503,
      headers: { "Content-Type": "text/html; charset=utf-8" },
    });
  }
}

// ── Cache First (for static assets) ──
async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    const cache = await caches.open(ASSETS_CACHE);
    cache.put(request, response.clone());
    return response;
  } catch {
    return new Response("", { status: 408 });
  }
}

// ── Notify clients about updates ──
self.addEventListener("message", (event) => {
  if (event.data === "skipWaiting") {
    self.skipWaiting();
  }
});
