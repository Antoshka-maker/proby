import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import { router } from './router'
import { installMockFetch } from './api/mockServer'
import './styles.css'

// The demo has no real backend: requests to /api go to an in-browser fake server
installMockFetch()

createApp(App).use(createPinia()).use(router).mount('#app')
