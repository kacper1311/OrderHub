import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

const app = createApp(App)
app.use(createPinia())  // Pinia przed routerem, bo strażnik routera (B3) korzysta ze store
app.use(router)
app.mount('#app')
