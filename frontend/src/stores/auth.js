/**
 * Auth Store - manages user authentication state
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as apiLogin, getMe } from '../api'
import router from '../router'

export const useAuthStore = defineStore('auth', () => {
  // State
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(null)
  const loading = ref(false)

  // Getters
  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const username = computed(() => user.value?.username || '')

  // Actions
  async function login(username, password) {
    loading.value = true
    try {
      const res = await apiLogin({ username, password })
      const data = res.data
      token.value = data.access_token
      user.value = data.user
      localStorage.setItem('token', data.access_token)
      return true
    } catch (error) {
      return false
    } finally {
      loading.value = false
    }
  }

  async function fetchUser() {
    if (!token.value) return
    try {
      const res = await getMe()
      user.value = res.data
    } catch (error) {
      // Token invalid, clear auth
      logout()
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    router.push('/login')
  }

  // Initialize - fetch user on store creation
  if (token.value) {
    fetchUser()
  }

  return {
    token,
    user,
    loading,
    isAuthenticated,
    isAdmin,
    username,
    login,
    fetchUser,
    logout,
  }
})
