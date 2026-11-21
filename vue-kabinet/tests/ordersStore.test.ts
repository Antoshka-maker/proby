import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useOrdersStore } from '../src/stores/orders'
import { ordersApi } from '../src/api/orders'
import type { Order, Page } from '../src/types'

const order = (id: number) => ({ id }) as Order

describe('orders store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
  })

  it('ignores a slow response that arrives after a newer one', async () => {
    const resolvers: ((p: Page<Order>) => void)[] = []
    vi.spyOn(ordersApi, 'list').mockImplementation(() => new Promise((r) => resolvers.push(r)))
    const store = useOrdersStore()

    const first = store.setQuery({ search: 'а' })
    const second = store.setQuery({ search: 'ан' })
    resolvers[1]({ items: [order(2)], total: 1 })
    resolvers[0]({ items: [order(1)], total: 1 })
    await Promise.all([first, second])

    expect(store.items.map((o) => o.id)).toEqual([2])
    expect(store.loading).toBe(false)
  })

  it('goes back to page 1 when a filter changes', async () => {
    vi.spyOn(ordersApi, 'list').mockResolvedValue({ items: [order(1)], total: 30 })
    const store = useOrdersStore()
    await store.setQuery({ page: 3 })
    expect(store.query.page).toBe(3)
    await store.setQuery({ status: 'done' })
    expect(store.query.page).toBe(1)
  })

  it('toggles sort direction on the same column', async () => {
    vi.spyOn(ordersApi, 'list').mockResolvedValue({ items: [], total: 0 })
    const store = useOrdersStore()
    await store.toggleSort('price')
    expect(store.query).toMatchObject({ sort: 'price', desc: true })
    await store.toggleSort('price')
    expect(store.query.desc).toBe(false)
  })

  it('shows the error text when the request fails', async () => {
    vi.spyOn(ordersApi, 'list').mockRejectedValue(new Error('Нет связи с сервером'))
    const store = useOrdersStore()
    await store.load()
    expect(store.error).toBe('Нет связи с сервером')
  })
})
