<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const login = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(login.value.trim(), password.value)
    const next = typeof route.query.next === 'string' ? route.query.next : '/'
    router.replace(next)
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <form class="login card" @submit.prevent="submit">
    <h1>Вход</h1>
    <p class="muted">Демо-доступ: логин <b>demo</b>, пароль <b>demo</b></p>
    <label for="login">Логин</label>
    <input id="login" v-model="login" autocomplete="username" required />
    <label for="password">Пароль</label>
    <input id="password" v-model="password" type="password" autocomplete="current-password" required />
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <button class="btn primary" type="submit" :disabled="loading">{{ loading ? 'Вхожу…' : 'Войти' }}</button>
  </form>
</template>

<style scoped>
.login {
  max-width: 360px;
  margin: 10vh auto 0;
  display: grid;
  gap: 8px;
}
.login input {
  margin-bottom: 8px;
}
</style>
