import { request, toQueryString } from './http'
import type { Order, OrderDraft, OrdersQuery, Page, Stats } from '../types'

export const ordersApi = {
  list(query: OrdersQuery) {
    return request<Page<Order>>('GET', `/api/orders${toQueryString({ ...query })}`)
  },
  get(id: number) {
    return request<Order>('GET', `/api/orders/${id}`)
  },
  create(draft: OrderDraft) {
    return request<Order>('POST', '/api/orders', draft)
  },
  update(id: number, patch: Partial<OrderDraft>) {
    return request<Order>('PATCH', `/api/orders/${id}`, patch)
  },
  remove(id: number) {
    return request<null>('DELETE', `/api/orders/${id}`)
  },
  stats() {
    return request<Stats>('GET', '/api/stats')
  },
}

export const authApi = {
  login(login: string, password: string) {
    return request<{ token: string; name: string }>('POST', '/api/login', { login, password })
  },
}
