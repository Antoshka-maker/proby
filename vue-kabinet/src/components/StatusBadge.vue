<script setup lang="ts">
import { STATUS_LABELS, type OrderStatus } from '../types'

defineProps<{ status: OrderStatus }>()
</script>

<template>
  <span class="badge" :class="status">{{ STATUS_LABELS[status] }}</span>
</template>

<style scoped>
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 13px;
  white-space: nowrap;
  background: color-mix(in srgb, var(--c) 15%, transparent);
  color: var(--c);
}
.new { --c: #2f6fde; }
.in_progress { --c: #b7791f; }
.done { --c: #2f9e5b; }
.cancelled { --c: #8a8f9c; }
</style>
