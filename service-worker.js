self.addEventListener('install', (event) => {
    console.log('Service Worker: Instalando...');
    // Esta é a etapa de cache, que é opcional para a instalação, mas é uma boa prática
    event.waitUntil(
        caches.open('meu-app-cache-v1').then((cache) => {
            return cache.addAll([
                '/',
                '/clientes',
                '/transacoes',
                '/combos',
                '/static/images/icon-192x192.png',
                '/static/images/icon-512x512.png',
                '/static/style.css' // Se você tiver um arquivo de estilo
            ]);
        })
    );
});

self.addEventListener('fetch', (event) => {
    // Retorna o conteúdo do cache se disponível
    event.respondWith(
        caches.match(event.request).then((response) => {
            return response || fetch(event.request);
        })
    );
});
