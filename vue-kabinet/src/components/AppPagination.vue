<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ page: number; total: number; perPage: number }>()
const emit = defineEmits<{ change: [page: number] }>()

const pages = computed(() => Math.max(1, Math.ceil(props.total / props.perPage)))

/** 1 … 4 5 6 … 20: current page, its neighbours and the edges */
const visible = computed(() => {
  const result: (number | '…')[] = []
  for (let p = 1; p <= pages.value; p++) {
    if (p === 1 || p === pages.value || Math.abs(p - props.page) <= 1) result.push(p)
    else if (result[result.length - 1] !== '…') result.push('…')
  }
  return result
})
</script>

<template>
  <nav v-if="pages > 1" class="pagination" aria-label="Страницы">
    <button class="btn" :disabled="page === 1" @click="emit('change', page - 1)">←</button>
    <template v-for="(p, i) in visible" :key="i">
      <span v-if="p === '…'" class="muted">…</span>
      <button v-else class="btn" :class="{ primary: p === page }" :aria-current="p === page ? 'page' : undefined" @click="emit('change', p)">
        {{ p }}
      </button>
    </template>
    <button class="btn" :disabled="page === pages" @click="emit('change', page + 1)">→</button>
  </nav>
</template>

<style scoped>
.pagination {
  display: flex;
  gap: 6px;
  align-items: center;
  flex-wrap: wrap;
  margin-top: 16px;
}
.btn {
  min-width: 38px;
}
</style>
