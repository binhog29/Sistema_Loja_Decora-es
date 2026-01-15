const CACHE_NAME = 'sistema-loja-v1';

// Lista de arquivos para salvar no cache (Offline)
// Adicione aqui as rotas principais e arquivos CSS/JS
const urlsToCache = [
  '/',
  '/static/style.css',
  '/static/notifications.js',
  '/static/images/icon-192x192.png',
  '/static/images/icon-512x512.png',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css'
];

// Instalação: Cria o cache e salva os arquivos estáticos
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Cache aberto: Salvando arquivos estáticos');
        return cache.addAll(urlsToCache);
      })
  );
});

// Ativação: Limpa caches antigos quando você atualizar a versão (v1, v2...)
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            console.log('Removendo cache antigo:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// Interceptação de buscas (Fetch): 
// Tenta buscar na rede primeiro, se falhar (offline), busca no cache.
self.addEventListener('fetch', event => {
  event.respondWith(
    fetch(event.request)
      .then(response => {
        // Se a resposta for válida, clonamos e salvamos no cache para uso futuro
        if (!response || response.status !== 200 || response.type !== 'basic') {
          return response;
        }
        const responseToCache = response.clone();
        caches.open(CACHE_NAME).then(cache => {
          cache.put(event.request, responseToCache);
        });
        return response;
      })
      .catch(() => {
        // Se a rede falhar, tenta encontrar no cache
        return caches.match(event.request);
      })
  );
});