import { describe, expect, it } from 'vitest'
import { handle } from '../src/api/mockServer'
import { makeSeed } from '../src/api/seed'
import type { Order, Page } from '../src/types'

const list = (db: Order[], qs = '') => handle(db, 'GET', `/api/orders${qs}`, undefined, true).body as Page<Order>

describe('fake REST backend', () => {
  it('requires a login', () => {
    expect(handle(makeSeed(), 'GET', '/api/orders', undefined, false).status).toBe(401)
    expect(handle([], 'POST', '/api/login', { login: 'demo', password: 'x' }, false).status).toBe(401)
    expect(handle([], 'POST', '/api/login', { login: 'demo', password: 'demo' }, false).status).toBe(200)
  })

  it('paginates and reports the total', () => {
    const db = makeSeed(25)
    const page3 = list(db, '?page=3&perPage=10')
    expect(page3.total).toBe(25)
    expect(page3.items).toHaveLength(5)
  })

  it('filters by status and searches case-insensitively', () => {
    const db = makeSeed()
    const done = list(db, '?status=done&perPage=100')
    expect(done.items.every((o) => o.status === 'done')).toBe(true)
    const found = list(db, '?search=ЛЕНДИНГ&perPage=100')
    expect(found.total).toBeGreaterThan(0)
    expect(found.items.every((o) => o.service === 'Лендинг')).toBe(true)
  })

  it('sorts by price both ways', () => {
    const db = makeSeed()
    const asc = list(db, '?sort=price&desc=false&perPage=100').items.map((o) => o.price)
    expect(asc).toEqual([...asc].sort((a, b) => a - b))
    const desc = list(db, '?sort=price&perPage=100').items.map((o) => o.price)
    expect(desc).toEqual([...asc].reverse())
  })

  it('validates on create and update, and assigns ids', () => {
    const db = makeSeed(3)
    expect(handle(db, 'POST', '/api/orders', { client: '' }, true).status).toBe(422)
    const created = handle(db, 'POST', '/api/orders', { client: 'Тест', phone: '89001234567', service: 'Бот', price: 500, status: 'new', comment: '' }, true)
    expect(created.status).toBe(201)
    expect((created.body as Order).id).toBe(4)
    expect(handle(db, 'PATCH', '/api/orders/1', { price: -5 }, true).status).toBe(422)
    expect(handle(db, 'PATCH', '/api/orders/1', { status: 'done' }, true).body).toMatchObject({ id: 1, status: 'done' })
  })

  it('deletes and then returns 404', () => {
    const db = makeSeed(3)
    expect(handle(db, 'DELETE', '/api/orders/2', undefined, true).status).toBe(204)
    expect(handle(db, 'GET', '/api/orders/2', undefined, true).status).toBe(404)
  })
})
