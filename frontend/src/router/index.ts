import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: () => import('@/views/HomeView.vue') },
    { path: '/products/:id', name: 'product', component: () => import('@/views/ProductView.vue') },
    { path: '/compare', name: 'compare', component: () => import('@/views/CompareView.vue') },
    { path: '/deals', name: 'deals', component: () => import('@/views/DealsView.vue') },
    { path: '/search', name: 'search', component: () => import('@/views/SearchView.vue') },
    { path: '/admin', name: 'admin', component: () => import('@/views/AdminView.vue') }
  ]
})

// Defense-in-depth against the classic Vite post-deploy chunk-404 error:
// if a tab was open BEFORE a new deploy finished, its in-memory index.html
// still references the previous build's hashed chunk filenames. Navigating
// to a not-yet-visited route then tries to dynamically import a file that
// no longer exists on the server (replaced by the new build's new hashes).
// The real fix is the cache headers in public/_headers and nginx.conf
// (index.html must never be cached) - this handles the narrow window where
// someone already has the stale page open when a new deploy lands: reload
// once to pick up the current index.html + matching asset hashes, instead
// of leaving them on a broken white screen. sessionStorage guards against a
// reload loop if the failure has some other real cause.
function isChunkLoadError(error: unknown): boolean {
  const message = error instanceof Error ? error.message : String(error)
  return /Failed to fetch dynamically imported module|Importing a module script failed|error loading dynamically imported module/i.test(message)
}

function reloadOnceForStaleChunk(error: unknown) {
  if (!isChunkLoadError(error)) return
  const key = 'pricecompare:chunk-reload-attempted'
  if (sessionStorage.getItem(key)) return // already tried once this session - avoid a loop
  sessionStorage.setItem(key, '1')
  window.location.reload()
}

router.onError(reloadOnceForStaleChunk)
window.addEventListener('unhandledrejection', (event) => reloadOnceForStaleChunk(event.reason))

export default router
