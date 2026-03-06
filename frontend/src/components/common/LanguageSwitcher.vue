<script setup lang="ts">
import { usePreferencesStore, type LocaleCode } from '../../stores/preferences'
import { useI18n } from 'vue-i18n'
import { storeToRefs } from 'pinia'

const store = usePreferencesStore()
const { locale } = storeToRefs(store)
const { locale: i18nLocale } = useI18n()

const setLocale = (code: LocaleCode) => {
  store.locale = code
  i18nLocale.value = code
}
</script>

<template>
  <div class="dropdown dropdown-top">
    <label tabindex="0" class="btn btn-ghost btn-sm gap-1">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        class="h-4 w-4"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="2"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
      <span class="text-xs">{{ locale === 'en' ? 'EN' : '中文' }}</span>
    </label>
    <ul tabindex="0" class="dropdown-content menu p-2 shadow bg-base-100 rounded-box w-36 z-50">
      <li>
        <a @click="setLocale('en')" :class="{ active: locale === 'en' }">English</a>
      </li>
      <li>
        <a @click="setLocale('zh-TW')" :class="{ active: locale === 'zh-TW' }">繁體中文</a>
      </li>
    </ul>
  </div>
</template>
