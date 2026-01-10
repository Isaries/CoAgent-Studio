

module.exports = {
    root: true,
    'extends': [
        'plugin:vue/vue3-essential',
        'eslint:recommended',
        '@vue/eslint-config-typescript',
        '@vue/eslint-config-prettier/skip-formatting'
    ],
    parserOptions: {
        ecmaVersion: 'latest'
    },
    env: {
        node: true,
        'vue/setup-compiler-macros': true
    },
    rules: {
        // Add custom rules here
        'vue/multi-word-component-names': 'off'
    },
    globals: {
        __INTLIFY_PROD_DEVTOOLS__: 'readonly',
        __INTLIFY_JIT_COMPILATION__: 'readonly',
        __INTLIFY_DROP_MESSAGE_COMPILER__: 'readonly',
        __VUE_I18N_LEGACY_API__: 'readonly',
        __VUE_I18N_FULL_INSTALL__: 'readonly'
    }
}
