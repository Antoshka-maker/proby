/**
 * Fake REST backend for the demo. The app talks to it through the ordinary
 * fetch('/api/...') calls, so swapping in a real server changes nothing in the
 * components or stores.
 */
import type { Order, OrderDraft, OrderStatus, SortField, Stats } from '../types'
import { makeSeed } from './seed'
import { validateOrder } from '../utils/validation'

export interface MockResponse {
  status: number
  body: unknown
}

const DEMO_LOGIN = 'demo'
const DEMO_PASSWORD = 'demo'
const STATUSES: OrderStatus[] = ['new', 'in_progress', 'done', 'cancelled']
const SORT_FIELDS: SortField[] = ['createdAt', 'price', 'client']

export function handle(db: Order[], method: string, rawUrl: string, body: unknown, authorized: boolean): MockResponse {
  const url = new URL(rawUrl, 'http://local')
  const path = url.pathname

  if (method === 'POST' && path === '/api/login') {
    const { login, password } = (body ?? {}) as { login?: string; password?: string }
    if (login === DEMO_LOGIN && password === DEMO_PASSWORD) {
      return { status: 200, body: { token: 'demo-token', name: 'Менеджер' } }
    }
    return { status: 401, body: { message: 'Неверный логин или пароль' } }
  }

  if (!authorized) return { status: 401, body: { message: 'Нужно войти' } }

  if (method === 'GET' && path === '/api/orders') {
    const p = url.searchParams
    const search = (p.get('search') ?? '').trim().toLowerCase()
    const status = p.get('status') as OrderStatus | null
    const sort = SORT_FIELDS.includes(p.get('sort') as SortField) ? (p.get('sort') as SortField) : 'createdAt'
    const desc = p.get('desc') !== 'false'
    const perPage = clamp(Number(p.get('perPage')) || 10, 1, 100)
    const page = Math.max(1, Number(p.get('page')) || 1)

    let items = db.filter(
      (o) =>
        (!status || o.status === status) &&
        (!search || `${o.client} ${o.service} ${o.phone} ${o.id}`.toLowerCase().includes(search)),
    )
    items = [...items].sort((a, b) => compare(a[sort], b[sort]) * (desc ? -1 : 1))
    return { status: 200, body: { items: items.slice((page - 1) * perPage, page * perPage), total: items.length } }
  }

  if (method === 'GET' && path === '/api/stats') {
    const byStatus = Object.fromEntries(STATUSES.map((s) => [s, 0])) as Record<OrderStatus, number>
    let revenue = 0
    for (const o of db) {
      byStatus[o.status]++
      if (o.status === 'done') revenue += o.price
    }
    const stats: Stats = { total: db.length, revenue, byStatus }
    return { status: 200, body: stats }
  }

  if (method === 'POST' && path === '/api/orders') {
    const draft = body as OrderDraft
    const errors = validateOrder(draft)
    if (Object.keys(errors).length) return { status: 422, body: { message: 'Проверьте поля', errors } }
    const order: Order = { ...draft, id: Math.max(0, ...db.map((o) => o.id)) + 1, createdAt: new Date().toISOString() }
    db.push(order)
    return { status: 201, body: order }
  }

  const match = path.match(/^\/api\/orders\/(\d+)$/)
  if (match) {
    const index = db.findIndex((o) => o.id === Number(match[1]))
    if (index === -1) return { status: 404, body: { message: 'Заказ не найден' } }

    if (method === 'GET') return { status: 200, body: db[index] }
    if (method === 'PATCH') {
      const next = { ...db[index], ...(body as Partial<OrderDraft>) }
      const errors = validateOrder(next)
      if (Object.keys(errors).length) return { status: 422, body: { message: 'Проверьте поля', errors } }
      db[index] = next
      return { status: 200, body: next }
    }
    if (method === 'DELETE') {
      db.splice(index, 1)
      return { status: 204, body: null }
    }
  }

  return { status: 404, body: { message: 'Нет такого адреса' } }
}

function compare(a: string | number, b: string | number) {
  return typeof a === 'number' && typeof b === 'number' ? a - b : String(a).localeCompare(String(b), 'ru')
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}

const STORAGE_KEY = 'vue-kabinet-orders'

function loadDb(): Order[] {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) return JSON.parse(saved)
  } catch {
    /* storage may be unavailable, fall back to seed */
  }
  return makeSeed()
}

function saveDb(db: Order[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(db))
  } catch {
    /* ignore */
  }
}

export function resetDemoData() {
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    /* ignore */
  }
}

/** Routes fetch('/api/...') to the fake backend with a small network delay */
export function installMockFetch(latency = 300) {
  const db = loadDb()
  const realFetch = window.fetch.bind(window)

  window.fetch = async (input, init = {}) => {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url
    const apiIndex = url.indexOf('/api/')
    if (apiIndex === -1) return realFetch(input, init)
    const apiUrl = url.slice(apiIndex)

    await new Promise((r) => setTimeout(r, latency))
    const method = (init.method ?? 'GET').toUpperCase()
    const headers = new Headers(init.headers)
    const body = init.body ? JSON.parse(String(init.body)) : undefined
    const result = handle(db, method, apiUrl, body, headers.get('Authorization') === 'Bearer demo-token')
    if (method !== 'GET') saveDb(db)
    return new Response(result.status === 204 ? null : JSON.stringify(result.body), {
      status: result.status,
      headers: { 'Content-Type': 'application/json' },
    })
  }
}
