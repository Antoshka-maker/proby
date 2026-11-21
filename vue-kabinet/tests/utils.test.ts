import { describe, expect, it } from 'vitest'
import { normalizePhone, validateOrder } from '../src/utils/validation'
import { plural } from '../src/utils/format'

describe('validateOrder', () => {
  const ok = { client: 'Анна', phone: '+7 900 123-45-67', service: 'Лендинг', price: 1000, status: 'new' as const, comment: '' }

  it('accepts a correct order', () => {
    expect(validateOrder(ok)).toEqual({})
  })

  it('reports every broken field', () => {
    expect(Object.keys(validateOrder({ ...ok, client: ' ', phone: '123', price: 0 }))).toEqual(['client', 'phone', 'price'])
  })

  it('rejects NaN from an emptied number input', () => {
    expect(validateOrder({ ...ok, price: Number.NaN }).price).toBeDefined()
  })
})

describe('normalizePhone', () => {
  it.each([
    ['8 (900) 123-45-67', '79001234567'],
    ['9001234567', '79001234567'],
    ['+7 900 123 45 67', '79001234567'],
  ])('%s -> %s', (input, expected) => {
    expect(normalizePhone(input)).toBe(expected)
  })
})

describe('plural', () => {
  const forms: [string, string, string] = ['заказ', 'заказа', 'заказов']
  it.each([
    [1, 'заказ'], [2, 'заказа'], [5, 'заказов'], [11, 'заказов'], [12, 'заказов'], [21, 'заказ'], [104, 'заказа'], [111, 'заказов'],
  ])('%i %s', (n, expected) => {
    expect(plural(n, forms)).toBe(expected)
  })
})
