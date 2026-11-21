import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { authApi } from '../api/orders'
import { setToken } from '../api/http'

const KEY = 'vue-kabinet-session'

export const useAuthStore = defineStore('auth', () => {
  const saved = readSession()
  const token = ref<string | null>(saved?.token ?? null)
  const name = ref(saved?.name ?? '')
  setToken(token.value)

  const isLoggedIn = computed(() => token.value !== null)

  async function login(login: string, password: string) {
    const session = await authApi.login(login, password)
    token.value = session.token
    name.value = session.name
    setToken(session.token)
    try {
      sessionStorage.setItem(KEY, JSON.stringify(session))
    } catch {
      /* private mode: session lives until reload */
    }
  }

  function logout() {
    token.value = null
    name.value = ''
    setToken(null)
    try {
      sessionStorage.removeItem(KEY)
    } catch {
      /* ignore */
    }
  }

  return { token, name, isLoggedIn, login, logout }
})

function readSession(): { token: string; name: string } | null {
  try {
    return JSON.parse(sessionStorage.getItem(KEY) ?? 'null')
  } catch {
    return null
  }
}
