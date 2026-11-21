import { createRouter, createWebHashHistory } from 'vue-router'
import { useAuthStore } from './stores/auth'

export const router = createRouter({
  // Hash history: works on static hosting without server rewrites
  history: createWebHashHistory(),
  routes: [
    { path: '/login', name: 'login', component: () => import('./views/LoginView.vue'), meta: { public: true } },
    { path: '/', name: 'dashboard', component: () => import('./views/DashboardView.vue') },
    { path: '/orders', name: 'orders', component: () => import('./views/OrdersView.vue') },
    { path: '/orders/new', name: 'order-new', component: () => import('./views/OrderView.vue') },
    { path: '/orders/:id(\\d+)', name: 'order', component: () => import('./views/OrderView.vue'), props: true },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isLoggedIn) return { name: 'login', query: { next: to.fullPath } }
  if (to.name === 'login' && auth.isLoggedIn) return { name: 'dashboard' }
})
