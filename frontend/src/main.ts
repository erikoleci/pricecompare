import { createApp } from 'vue'
import { createPinia } from 'pinia'
import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import '@mdi/font/css/materialdesignicons.css'
import App from './App.vue'
import router from './router'

const vuetify = createVuetify({
  theme: {
    defaultTheme: 'light',
    themes: {
      light: {
        colors: {
          primary: '#1F6FEB',
          secondary: '#0B1B33',
          success: '#1F9D55',
          warning: '#E0A800',
          error: '#D0342C'
        }
      }
    }
  }
})

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(vuetify)
app.mount('#app')

// Once a route has genuinely loaded successfully, clear the stale-chunk
// reload guard from router/index.ts - so a later, unrelated chunk-load
// failure (e.g. a flaky network blip weeks from now) can still trigger one
// automatic recovery reload instead of being silently swallowed by a guard
// left over from an earlier, already-resolved deploy.
router.isReady().then(() => sessionStorage.removeItem('pricecompare:chunk-reload-attempted'))
