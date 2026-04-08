<template>
  <section class="ops-page__header">
    <div class="ops-page__copy">
      <p v-if="eyebrow" class="ops-page__eyebrow">{{ eyebrow }}</p>
      <h2 class="ops-page__title">{{ title }}</h2>
      <p v-if="description" class="ops-page__description">{{ description }}</p>
    </div>

    <div v-if="$slots.actions" class="ops-page__actions">
      <slot name="actions" />
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  title: string;
  eyebrow?: string;
  description?: string;
}>();
</script>
