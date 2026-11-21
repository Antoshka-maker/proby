<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { onBeforeRouteLeave, useRouter } from 'vue-router'
import { ordersApi } from '../api/orders'
import { ApiError } from '../api/http'
import { formatDate } from '../utils/format'
import type { FieldErrors } from '../utils/validation'
import type { Order, OrderDraft } from '../types'
import OrderForm from '../components/OrderForm.vue'

const props = defineProps<{ id?: string }>()
const router = useRouter()

const EMPTY: OrderDraft = { client: '', phone: '', service: '', price: 0, status: 'new', comment: '' }

const order = ref<Order | null>(null)
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const serverErrors = ref<FieldErrors>({})
const formRef = ref<InstanceType<typeof OrderForm> | null>(null)
let leaving = false

const isNew = computed(() => !props.id)
const initial = computed<OrderDraft>(() => {
  if (!order.value) return EMPTY
  const { id: _id, createdAt: _createdAt, ...draft } = order.value
  return draft
})

onMounted(async () => {
  if (isNew.value) return
  loading.value = true
  try {
    order.value = await ordersApi.get(Number(props.id))
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    loading.value = false
  }
})

async function save(draft: OrderDraft) {
  saving.value = true
  error.value = ''
  serverErrors.value = {}
  try {
    if (isNew.value) await ordersApi.create(draft)
    else await ordersApi.update(order.value!.id, draft)
    leaving = true
    router.push({ name: 'orders' })
  } catch (e) {
    error.value = (e as Error).message
    if (e instanceof ApiError && e.status === 422) serverErrors.value = e.fields
  } finally {
    saving.value = false
  }
}

async function remove() {
  if (!order.value || !window.confirm(`Удалить заказ №${order.value.id}?`)) return
  try {
    await ordersApi.remove(order.value.id)
    leaving = true
    router.push({ name: 'orders' })
  } catch (e) {
    error.value = (e as Error).message
  }
}

onBeforeRouteLeave(() => {
  if (!leaving && formRef.value?.dirty) return window.confirm('Есть несохранённые изменения. Уйти со страницы?')
})
</script>

<template>
  <RouterLink :to="{ name: 'orders' }" class="back">← К заказам</RouterLink>
  <h1>{{ isNew ? 'Новый заказ' : `Заказ №${id}` }}</h1>
  <p v-if="order" class="muted">Создан {{ formatDate(order.createdAt) }}</p>
  <p v-if="error" class="error" role="alert">{{ error }}</p>
  <p v-if="loading" class="muted">Загружаю…</p>
  <template v-else-if="isNew || order">
    <OrderForm ref="formRef" :initial="initial" :saving="saving" :server-errors="serverErrors" @submit="save" @cancel="router.push({ name: 'orders' })" />
    <button v-if="order" class="btn danger delete" @click="remove">Удалить заказ</button>
  </template>
</template>

<style scoped>
.back {
  display: inline-block;
  margin-bottom: 12px;
  color: var(--muted);
  text-decoration: none;
}
.delete {
  margin-top: 16px;
}
</style>
