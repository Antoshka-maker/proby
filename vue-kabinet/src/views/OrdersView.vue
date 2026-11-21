<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useOrdersStore, DEFAULT_QUERY } from '../stores/orders'
import { useDebounced } from '../composables/useDebounced'
import { plural } from '../utils/format'
import { STATUS_LABELS, type OrderStatus, type OrdersQuery, type SortField } from '../types'
import OrdersTable from '../components/OrdersTable.vue'
import AppPagination from '../components/AppPagination.vue'

const store = useOrdersStore()
const { query, items, total, loading, error } = storeToRefs(store)
const route = useRoute()
const router = useRouter()

const search = ref('')
const applySearch = useDebounced((value: string) => store.setQuery({ search: value }), 300)

// Filters live in the URL, so a filtered list can be bookmarked or shared
function readUrl(): Partial<OrdersQuery> {
  const q = route.query
  const status = String(q.status ?? '')
  const sort = String(q.sort ?? '')
  return {
    search: String(q.search ?? ''),
    status: status in STATUS_LABELS ? (status as OrderStatus) : '',
    sort: ['createdAt', 'price', 'client'].includes(sort) ? (sort as SortField) : DEFAULT_QUERY.sort,
    desc: q.desc !== 'false',
    page: Math.max(1, Number(q.page) || 1),
  }
}

watch(
  query,
  (q) => {
    const next: Record<string, string> = {}
    if (q.search) next.search = q.search
    if (q.status) next.status = q.status
    if (q.sort !== DEFAULT_QUERY.sort) next.sort = q.sort
    if (!q.desc) next.desc = 'false'
    if (q.page > 1) next.page = String(q.page)
    router.replace({ query: next })
  },
  { deep: true },
)

onMounted(() => {
  const fromUrl = readUrl()
  search.value = fromUrl.search ?? ''
  Object.assign(store.query, DEFAULT_QUERY, fromUrl)
  store.load()
})
</script>

<template>
  <div class="head">
    <h1>Заказы</h1>
    <RouterLink class="btn primary" :to="{ name: 'order-new' }">Новый заказ</RouterLink>
  </div>

  <div class="filters">
    <input v-model="search" type="search" placeholder="Поиск: клиент, услуга, телефон, №" aria-label="Поиск" @input="applySearch(search)" />
    <select :value="query.status" aria-label="Статус" @change="store.setQuery({ status: ($event.target as HTMLSelectElement).value as OrderStatus | '' })">
      <option value="">Все статусы</option>
      <option v-for="(label, value) in STATUS_LABELS" :key="value" :value="value">{{ label }}</option>
    </select>
  </div>

  <p class="muted summary">
    {{ loading ? 'Загружаю…' : `Найдено ${total} ${plural(total, ['заказ', 'заказа', 'заказов'])}` }}
  </p>
  <p v-if="error" class="error">{{ error }} <button class="link" @click="store.load()">Повторить</button></p>

  <div :class="{ loading }">
    <OrdersTable v-if="items.length" :orders="items" :sort="query.sort" :desc="query.desc" @sort="store.toggleSort" @open="(id) => router.push({ name: 'order', params: { id } })" />
    <div v-else-if="!loading && !error" class="card empty">
      Ничего не нашлось.
      <button class="link" @click="search = ''; store.setQuery({ search: '', status: '' })">Сбросить фильтры</button>
    </div>
  </div>

  <AppPagination :page="query.page" :total="total" :per-page="query.perPage" @change="(page) => store.setQuery({ page })" />
</template>

<style scoped>
.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}
.head h1 {
  margin: 0;
}
.filters {
  display: grid;
  grid-template-columns: 1fr 200px;
  gap: 12px;
  margin-bottom: 8px;
}
.summary {
  margin: 0 0 8px;
}
.loading {
  opacity: 0.55;
  transition: opacity 0.2s;
}
.empty {
  text-align: center;
  padding: 32px;
}
@media (max-width: 640px) {
  .filters {
    grid-template-columns: 1fr;
  }
}
</style>
