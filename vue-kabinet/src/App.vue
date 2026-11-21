<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'
import { resetDemoData } from './api/mockServer'

const auth = useAuthStore()
const router = useRouter()

function logout() {
  auth.logout()
  router.push({ name: 'login' })
}

function reset() {
  resetDemoData()
  location.reload()
}
</script>

<template>
  <header v-if="auth.isLoggedIn" class="topbar">
    <span class="logo">Кабинет заказов</span>
    <nav>
      <RouterLink to="/" exact-active-class="active">Сводка</RouterLink>
      <RouterLink to="/orders" active-class="active">Заказы</RouterLink>
    </nav>
    <div class="user">
      <span class="muted">{{ auth.name }}</span>
      <button class="link" title="Вернуть демо-данные к исходным" @click="reset">Сбросить данные</button>
      <button class="link" @click="logout">Выйти</button>
    </div>
  </header>
  <main class="page">
    <RouterView />
  </main>
</template>

<style scoped>
.topbar {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 12px 24px;
  background: var(--surface);
  border-bottom: 1px solid var(--line);
  flex-wrap: wrap;
}
.logo {
  font-weight: 700;
}
nav {
  display: flex;
  gap: 16px;
}
nav a {
  color: var(--muted);
  text-decoration: none;
  padding: 4px 0;
  border-bottom: 2px solid transparent;
}
nav a.active {
  color: var(--text);
  border-color: var(--accent);
}
.user {
  margin-left: auto;
  display: flex;
  gap: 12px;
  align-items: center;
}
@media (max-width: 640px) {
  .topbar {
    padding: 12px 16px;
    gap: 12px;
  }
  .user {
    margin-left: 0;
    width: 100%;
  }
}
</style>
