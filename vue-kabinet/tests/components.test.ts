import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import AppPagination from '../src/components/AppPagination.vue'
import OrderForm from '../src/components/OrderForm.vue'

describe('AppPagination', () => {
  it('collapses long ranges and emits the chosen page', async () => {
    const wrapper = mount(AppPagination, { props: { page: 5, total: 200, perPage: 10 } })
    const labels = wrapper.findAll('button, span').map((el) => el.text())
    expect(labels).toEqual(['←', '1', '…', '4', '5', '6', '…', '20', '→'])
    await wrapper.findAll('button').find((b) => b.text() === '6')!.trigger('click')
    expect(wrapper.emitted('change')).toEqual([[6]])
  })

  it('hides itself when everything fits on one page', () => {
    expect(mount(AppPagination, { props: { page: 1, total: 5, perPage: 10 } }).html()).not.toContain('nav')
  })
})

describe('OrderForm', () => {
  const initial = { client: '', phone: '', service: '', price: 0, status: 'new' as const, comment: '' }

  it('shows errors instead of submitting an empty form', async () => {
    const wrapper = mount(OrderForm, { props: { initial } })
    await wrapper.find('form').trigger('submit')
    expect(wrapper.emitted('submit')).toBeUndefined()
    expect(wrapper.text()).toContain('Укажите клиента')
  })

  it('submits a cleaned-up order', async () => {
    const wrapper = mount(OrderForm, { props: { initial } })
    await wrapper.find('#client').setValue('  Анна  ')
    await wrapper.find('#phone').setValue('8 900 123 45 67')
    await wrapper.find('#service').setValue('Лендинг')
    await wrapper.find('#price').setValue('25000')
    await wrapper.find('form').trigger('submit')
    expect(wrapper.emitted('submit')![0][0]).toMatchObject({ client: 'Анна', phone: '+7 900 123-45-67', price: 25000 })
  })
})
