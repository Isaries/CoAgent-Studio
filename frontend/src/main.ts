import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createI18n } from 'vue-i18n'
import './style.css'
import App from './App.vue'
import router from './router'
import en from './locales/en'
import zhTW from './locales/zh-TW'

const pinia = createPinia()

const savedLocale = localStorage.getItem('locale') || 'en'

const i18n = createI18n({
  legacy: false, // Composition API
  locale: savedLocale,
  fallbackLocale: 'en',
  messages: {
    en,
    'zh-TW': zhTW
  }
})

const app = createApp(App)

app.use(pinia)
app.use(router)
app.use(i18n)

app.mount('#app')
