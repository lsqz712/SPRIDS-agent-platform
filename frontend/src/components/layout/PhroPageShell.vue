<template>
  <div class="phro-page">
    <div class="phro-page-window">
      <header
        v-if="title || subtitle || $slots.header || $slots.actions"
        class="phro-module phro-page-header"
      >
        <div class="phro-page-header-main">
          <h2 v-if="title">{{ title }}</h2>
          <p v-if="subtitle">{{ subtitle }}</p>
          <slot name="header" />
        </div>
        <div v-if="$slots.actions" class="phro-page-header-actions">
          <slot name="actions" />
        </div>
      </header>
      <div class="phro-page-body" :class="{ 'phro-page-body--scroll': scrollBody }">
        <slot />
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  scrollBody: { type: Boolean, default: false },
})
</script>
