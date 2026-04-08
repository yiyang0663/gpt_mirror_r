<template>
  <section class="ops-metrics-grid" :class="`ops-metrics-grid--${columns}`">
    <article v-for="item in items" :key="item.label" class="ops-metric" :style="metricStyle(item.color)">
      <div class="ops-metric__top">
        <component :is="item.icon" v-if="item.icon" class="ops-metric__icon" />
        <p class="ops-metric__label">{{ item.label }}</p>
      </div>
      <p class="ops-metric__value">{{ item.value }}</p>
      <p v-if="item.meta" class="ops-metric__meta">{{ item.meta }}</p>
    </article>
  </section>
</template>

<script setup lang="ts">
import type { Component } from 'vue';

interface MetricItem {
  label: string;
  value: string | number;
  meta?: string;
  color?: string;
  icon?: Component;
}

withDefaults(
  defineProps<{
    items: MetricItem[];
    columns?: number;
  }>(),
  {
    columns: 4,
  },
);

const metricStyle = (color?: string) => {
  if (!color) return {};
  return {
    '--metric-color': color,
  };
};
</script>
