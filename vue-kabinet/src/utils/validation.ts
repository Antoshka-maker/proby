import type { OrderDraft } from '../types'

export type FieldErrors = Partial<Record<keyof OrderDraft, string>>

const PHONE_DIGITS = /^\d{11}$/

export function normalizePhone(phone: string): string {
  let digits = phone.replace(/\D/g, '')
  if (digits.length === 10) digits = '7' + digits
  if (digits.length === 11 && digits.startsWith('8')) digits = '7' + digits.slice(1)
  return digits
}

export function validateOrder(order: Partial<OrderDraft>): FieldErrors {
  const errors: FieldErrors = {}
  if (!order.client?.trim()) errors.client = 'Укажите клиента'
  if (!order.service?.trim()) errors.service = 'Укажите услугу'
  if (!PHONE_DIGITS.test(normalizePhone(order.phone ?? ''))) errors.phone = 'Телефон из 11 цифр'
  if (typeof order.price !== 'number' || !Number.isFinite(order.price) || order.price <= 0) {
    errors.price = 'Цена больше нуля'
  } else if (order.price > 10_000_000) {
    errors.price = 'Слишком большая сумма'
  }
  if ((order.comment ?? '').length > 500) errors.comment = 'Не больше 500 символов'
  return errors
}
