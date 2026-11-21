import { defineStore } from 'pinia'
import { reactive, ref } from 'vue'
import { ordersApi } from '../api/orders'
import type { Order, OrdersQuery } from '../types'

export const DEFAULT_QUERY: OrdersQuery = {
  search: '',
  status: '',
  sort: 'createdAt',
  desc: true,
  page: 1,
  perPage: 10,
}

export const useOrdersStore = defineStore('orders', () => {
  const query = reactive<OrdersQuery>({ ...DEFAULT_QUERY })
  const items = ref<Order[]>([])
  const total = ref(0)
  const loading = ref(false)
  const error = ref('')

  // Responses can come back out of order when the user types fast:
  // only the latest request is allowed to write to the state.
  let lastRequest = 0

  async function load() {
    const id = ++lastRequest
    loading.value = true
    error.value = ''
    try {
      const page = await ordersApi.list({ ...query })
      if (id !== lastRequest) return
      items.value = page.items
      total.value = page.total
      // Deleting the last row on the last page leaves the page empty
      const pages = Math.max(1, Math.ceil(page.total / query.perPage))
      if (query.page > pages) {
        query.page = pages
        await load()
      }
    } catch (e) {
      if (id === lastRequest) error.value = (e as Error).message
    } finally {
      if (id === lastRequest) loading.value = false
    }
  }

  function setQuery(patch: Partial<OrdersQuery>) {
    // Any filter change starts from the first page
    const resetPage = Object.keys(patch).some((k) => k !== 'page')
    Object.assign(query, patch, resetPage && patch.page === undefined ? { page: 1 } : {})
    return load()
  }

  function toggleSort(field: OrdersQuery['sort']) {
    return setQuery(query.sort === field ? { desc: !query.desc } : { sort: field, desc: true })
  }

  async function remove(id: number) {
    await ordersApi.remove(id)
    await load()
  }

  return { query, items, total, loading, error, load, setQuery, toggleSort, remove }
})
