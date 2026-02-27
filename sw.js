const CACHE_NAME = 'iceland-map-v1';
const ASSETS_TO_CACHE = [
    '/',
    '/index.html',
    // We cannot reliable cache all OSM tiles, but we'll cache what the user views
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => {
            console.log('Opened cache');
            return cache.addAll(ASSETS_TO_CACHE).catch(err => console.error("Cache addAll failed", err));
        })
    );
});

self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);

    // Exclude map tiles from pre-caching, but try to cache them as they are loaded
    if (url.hostname.includes('tile.openstreetmap.org') || url.hostname.includes('arcgisonline.com')) {
        event.respondWith(
            caches.match(event.request).then(response => {
                if (response) return response;
                return fetch(event.request).then(res => {
                    if (!res || res.status !== 200 || res.type !== 'basic' && res.type !== 'cors') {
                        return res;
                    }
                    const resClone = res.clone();
                    caches.open(CACHE_NAME).then(cache => {
                        cache.put(event.request, resClone);
                    });
                    return res;
                }).catch(() => {
                    // If offline and tile not in cache, just fail silently (show empty grey map tile)
                });
            })
        );
        return;
    }

    // General Network-First Strategy for everything else to ensure we always see the latest version
    event.respondWith(
        fetch(event.request).then(response => {
            if (!response || response.status !== 200) {
                return response;
            }
            const resClone = response.clone();
            caches.open(CACHE_NAME).then(cache => {
                cache.put(event.request, resClone);
            });
            return response;
        }).catch(() => {
            return caches.match(event.request);
        })
    );
});

self.addEventListener('activate', event => {
    const cacheWhitelist = [CACHE_NAME];
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheWhitelist.indexOf(cacheName) === -1) {
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
});
