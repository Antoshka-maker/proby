<script setup lang="ts">
import StatusBadge from './StatusBadge.vue'
import { formatDate, formatMoney } from '../utils/format'
import type { Order, SortField } from '../types'

defineProps<{ orders: Order[]; sort: SortField; desc: boolean }>()
const emit = defineEmits<{ sort: [field: SortField]; open: [id: number] }>()

const columns: { field: SortField; label: string }[] = [
  { field: 'createdAt', label: 'Дата' },
  { field: 'client', label: 'Клиент' },
  { field: 'price', label: 'Сумма' },
]
</script>

<template>
  <table class="table">
    <thead>
      <tr>
        <th>№</th>
        <th v-for="col in columns" :key="col.field" :class="['sortable', { right: col.field === 'price' }]">
          <button class="link" @click="emit('sort', col.field)">
            {{ col.label }}
            <span v-if="sort === col.field" aria-hidden="true">{{ desc ? '↓' : '↑' }}</span>
          </button>
        </th>
        <th>Услуга</th>
        <th>Статус</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="o in orders" :key="o.id" tabindex="0" @click="emit('open', o.id)" @keydown.enter="emit('open', o.id)">
        <td data-label="№">{{ o.id }}</td>
        <td data-label="Дата">{{ formatDate(o.createdAt) }}</td>
        <td data-label="Клиент">{{ o.client }}</td>
        <td data-label="Сумма" class="right">{{ formatMoney(o.price) }}</td>
        <td data-label="Услуга">{{ o.service }}</td>
        <td data-label="Статус"><StatusBadge :status="o.status" /></td>
      </tr>
    </tbody>
  </table>
</template>

<style scoped>
.table {
  width: 100%;
  border-collapse: collapse;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  overflow: hidden;
}
th,
td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid var(--line);
}
th {
  font-size: 13px;
  color: var(--muted);
  font-weight: 500;
}
th .link {
  color: var(--muted);
  font-weight: 500;
}
.right {
  text-align: right;
}
tbody tr {
  cursor: pointer;
}
tbody tr:hover,
tbody tr:focus {
  background: color-mix(in srgb, var(--accent) 6%, transparent);
  outline: none;
}
/* On phones the table turns into cards */
@media (max-width: 640px) {
  thead {
    display: none;
  }
  .table,
  tbody,
  tr,
  td {
    display: block;
  }
  .table {
    border: 0;
    background: none;
  }
  tr {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--radius);
    margin-bottom: 10px;
    padding: 6px 0;
  }
  td {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    border: 0;
    padding: 4px 12px;
    text-align: right;
  }
  td::before {
    content: attr(data-label);
    color: var(--muted);
  }
}
</style>
