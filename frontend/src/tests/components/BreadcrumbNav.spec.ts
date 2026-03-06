import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import BreadcrumbNav from '../../components/common/BreadcrumbNav.vue'
import { createI18n } from 'vue-i18n'
import en from '../../locales/en'

const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })

describe('BreadcrumbNav', () => {
  it('renders breadcrumbs from route meta', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        {
          path: '/',
          meta: { breadcrumb: 'Home' },
          children: [
            { path: 'spaces', component: { template: '<div />' }, meta: { breadcrumb: 'Spaces' } }
          ],
          component: { template: '<router-view />' }
        }
      ]
    })

    await router.push('/spaces')
    await router.isReady()

    const wrapper = mount(BreadcrumbNav, {
      global: { plugins: [router, i18n] }
    })

    const items = wrapper.findAll('li')
    expect(items.length).toBeGreaterThanOrEqual(1)
  })

  it('renders nothing when no breadcrumb meta', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/', component: { template: '<div />' } }]
    })

    await router.push('/')
    await router.isReady()

    const wrapper = mount(BreadcrumbNav, {
      global: { plugins: [router, i18n] }
    })

    expect(wrapper.find('.breadcrumbs').exists()).toBe(false)
  })
})
