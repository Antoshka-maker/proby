<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { validateOrder, normalizePhone, type FieldErrors } from '../utils/validation'
import { STATUS_LABELS, type OrderDraft } from '../types'

const props = defineProps<{ initial: OrderDraft; saving?: boolean; serverErrors?: FieldErrors }>()
const emit = defineEmits<{ submit: [draft: OrderDraft]; cancel: [] }>()

const form = reactive<OrderDraft>({ ...props.initial })
const touched = ref(false)

watch(
  () => props.initial,
  (value) => Object.assign(form, value),
)

// Errors appear after the first submit attempt, then update as the user types
const errors = computed<FieldErrors>(() => (touched.value ? { ...props.serverErrors, ...validateOrder(form) } : {}))
const dirty = computed(() => JSON.stringify(form) !== JSON.stringify(props.initial))

function submit() {
  touched.value = true
  if (Object.keys(validateOrder(form)).length) return
  emit('submit', { ...form, phone: formatPhone(form.phone), client: form.client.trim(), service: form.service.trim() })
}

function formatPhone(phone: string) {
  const d = normalizePhone(phone)
  return `+${d[0]} ${d.slice(1, 4)} ${d.slice(4, 7)}-${d.slice(7, 9)}-${d.slice(9)}`
}

defineExpose({ dirty })
</script>

<template>
  <form class="form card" novalidate @submit.prevent="submit">
    <div class="field">
      <label for="client">Клиент</label>
      <input id="client" v-model="form.client" autocomplete="off" :aria-invalid="!!errors.client" />
      <p v-if="errors.client" class="error">{{ errors.client }}</p>
    </div>
    <div class="field">
      <label for="phone">Телефон</label>
      <input id="phone" v-model="form.phone" type="tel" placeholder="+7 900 000-00-00" :aria-invalid="!!errors.phone" />
      <p v-if="errors.phone" class="error">{{ errors.phone }}</p>
    </div>
    <div class="field">
      <label for="service">Услуга</label>
      <input id="service" v-model="form.service" :aria-invalid="!!errors.service" />
      <p v-if="errors.service" class="error">{{ errors.service }}</p>
    </div>
    <div class="field">
      <label for="price">Сумма, ₽</label>
      <input id="price" v-model.number="form.price" type="number" min="1" step="100" :aria-invalid="!!errors.price" />
      <p v-if="errors.price" class="error">{{ errors.price }}</p>
    </div>
    <div class="field">
      <label for="status">Статус</label>
      <select id="status" v-model="form.status">
        <option v-for="(label, value) in STATUS_LABELS" :key="value" :value="value">{{ label }}</option>
      </select>
    </div>
    <div class="field wide">
      <label for="comment">Комментарий</label>
      <textarea id="comment" v-model="form.comment" rows="3" />
      <p class="muted small" :class="{ error: errors.comment }">{{ form.comment.length }} / 500</p>
    </div>
    <div class="actions wide">
      <button class="btn primary" type="submit" :disabled="saving">{{ saving ? 'Сохраняю…' : 'Сохранить' }}</button>
      <button class="btn" type="button" @click="emit('cancel')">Отмена</button>
    </div>
  </form>
</template>

<style scoped>
.form {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.wide {
  grid-column: 1 / -1;
}
.error,
.small {
  font-size: 13px;
  margin: 4px 0 0;
}
.actions {
  display: flex;
  gap: 8px;
}
@media (max-width: 640px) {
  .form {
    grid-template-columns: 1fr;
  }
}
</style>
