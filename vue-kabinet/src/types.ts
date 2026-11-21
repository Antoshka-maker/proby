export type OrderStatus = 'new' | 'in_progress' | 'done' | 'cancelled'

export interface Order {
  id: number
  client: string
  phone: string
  service: string
  price: number
  status: OrderStatus
  createdAt: string // ISO date
  comment: string
}

export type OrderDraft = Omit<Order, 'id' | 'createdAt'>

export type SortField = 'createdAt' | 'price' | 'client'

export interface OrdersQuery {
  search: string
  status: OrderStatus | ''
  sort: SortField
  desc: boolean
  page: number
  perPage: number
}

export interface Page<T> {
  items: T[]
  total: number
}

export interface Stats {
  total: number
  revenue: number
  byStatus: Record<OrderStatus, number>
}

export const STATUS_LABELS: Record<OrderStatus, string> = {
  new: 'Новый',
  in_progress: 'В работе',
  done: 'Готов',
  cancelled: 'Отменён',
}
