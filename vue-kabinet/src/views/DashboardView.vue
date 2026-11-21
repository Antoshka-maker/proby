<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ordersApi } from '../api/orders'
import { formatMoney, plural } from '../utils/format'
import { STATUS_LABELS, type OrderStatus, type Stats } from '../types'
import StatusBadge from '../components/StatusBadge.vue'

const stats = ref<Stats | null>(null)
const error = ref('')

onMounted(async () => {
  try {
    stats.value = await ordersApi.stats()
  } catch (e) {
    error.value = (e as Error).message
  }
})

const rows = computed(() => {
  if (!stats.value) return []
  const s = stats.value
  return (Object.keys(STATUS_LABELS) as OrderStatus[]).map((status) => ({
    status,
    count: s.byStatus[status],
    share: s.total ? Math.round((s.byStatus[status] / s.total) * 100) : 0,
  }))
})
</script>

<template>
  <h1>Сводка</h1>
  <p v-if="error" class="error">{{ error }}</p>
  <p v-else-if="!stats" class="muted">Загружаю…</p>
  <template v-else>
    <div class="tiles">
      <div class="card tile">
        <span class="muted">Всего</span>
        <strong>{{ stats.total }}</strong>
        <span class="muted">{{ plural(stats.total, ['заказ', 'заказа', 'заказов']) }}</span>
      </div>
      <div class="card tile">
        <span class="muted">В работе</span>
        <strong>{{ stats.byStatus.in_progress }}</strong>
        <RouterLink :to="{ name: 'orders', query: { status: 'in_progress' } }">открыть список</RouterLink>
      </div>
      <div class="card tile">
        <span class="muted">Выручка по готовым</span>
        <strong>{{ formatMoney(stats.revenue) }}</strong>
      </div>
    </div>
    <div class="card">
      <h2>По статусам</h2>
      <div v-for="row in rows" :key="row.status" class="bar-row">
        <StatusBadge :status="row.status" />
        <div class="bar" role="img" :aria-label="`${row.share}%`">
          <div class="fill" :class="row.status" :style="{ width: row.share + '%' }" />
        </div>
        <span class="num">{{ row.count }}</span>
      </div>
    </div>
  </template>
</template>

<style scoped>
.tiles {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}
.tile {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.tile strong {
  font-size: 28px;
}
h2 {
  font-size: 17px;
  margin: 0 0 12px;
}
.bar-row {
  display: grid;
  grid-template-columns: 100px 1fr 40px;
  gap: 12px;
  align-items: center;
  margin-bottom: 10px;
}
.bar {
  height: 10px;
  background: var(--line);
  border-radius: 5px;
  overflow: hidden;
}
.fill {
  height: 100%;
  background: var(--accent);
  transition: width 0.4s;
}
.fill.done { background: #2f9e5b; }
.fill.in_progress { background: #b7791f; }
.fill.cancelled { background: #8a8f9c; }
.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
</style>
