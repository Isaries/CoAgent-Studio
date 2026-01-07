import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createI18n } from 'vue-i18n'
import './style.css'
import App from './App.vue'
import router from './router'

const pinia = createPinia()
const i18n = createI18n({
    legacy: false, // Composition API
    locale: 'en',
    fallbackLocale: 'en',
    messages: {
        en: {
            hello: 'hello world'
        },
        zh: {
            hello: '你好'
        }
    }
})

const app = createApp(App)

app.use(pinia)
app.use(router)
app.use(i18n)

app.mount('#app')
