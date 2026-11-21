import type { Order, OrderStatus } from '../types'

const clients = [
  'Анна Смирнова', 'Игорь Петров', 'ООО «Вектор»', 'Мария Кузнецова', 'Дмитрий Орлов',
  'ИП Соколов', 'Елена Васильева', 'Павел Морозов', 'Студия «Лён»', 'Ольга Новикова',
  'Сергей Волков', 'Кафе «Тмин»', 'Наталья Фёдорова', 'Алексей Зайцев', 'ООО «Ремстрой»',
]
const services: [string, number][] = [
  ['Лендинг', 25000], ['Доработка сайта', 8000], ['Личный кабинет', 60000],
  ['Telegram-бот', 15000], ['Интеграция с CRM', 12000], ['Вёрстка по макету', 10000],
  ['Админ-панель', 45000], ['Исправление ошибок', 4000],
]
const statuses: OrderStatus[] = ['new', 'in_progress', 'done', 'done', 'cancelled', 'in_progress']

/** Deterministic demo data, so the demo looks the same for everyone */
export function makeSeed(count = 47): Order[] {
  const start = new Date('2026-11-20T12:00:00Z').getTime()
  return Array.from({ length: count }, (_, i) => {
    const [service, base] = services[(i * 5) % services.length]
    return {
      id: i + 1,
      client: clients[(i * 7) % clients.length],
      phone: `+7 9${String(10 + ((i * 37) % 89)).padStart(2, '0')} ${String(100 + ((i * 53) % 899))}-${String(10 + ((i * 17) % 89))}-${String(10 + ((i * 29) % 89))}`,
      service,
      price: base + ((i * 1300) % 7000),
      status: statuses[(i * 7 + Math.floor(i / 3)) % statuses.length],
      createdAt: new Date(start - i * 19 * 3600 * 1000).toISOString(),
      comment: i % 4 === 0 ? 'Срочно, созвониться до обеда' : '',
    }
  })
}
