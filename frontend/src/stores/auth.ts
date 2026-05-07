import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  getCurrentAccount,
  getBillingSummary,
  loginAccount,
  logoutAccount,
  registerAccount
} from '../api'
import type { UserSummary, BillingSummaryResponse } from '../types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserSummary | null>(null)
  const billing = ref<BillingSummaryResponse | null>(null)
  const loading = ref(false)

  const isLoggedIn = computed(() => !!user.value)
  const credits = computed(() => billing.value?.user.credits_balance ?? 0)

  async function init() {
    try {
      user.value = await getCurrentAccount()
      billing.value = await getBillingSummary()
    } catch {
      user.value = null
      billing.value = null
    }
  }

  async function login(email: string, password: string) {
    loading.value = true
    try {
      const session = await loginAccount({ email, password })
      user.value = session.user
      billing.value = await getBillingSummary()
    } finally {
      loading.value = false
    }
  }

  async function register(email: string, password: string, displayName?: string) {
    loading.value = true
    try {
      const session = await registerAccount({ email, password, displayName })
      user.value = session.user
      billing.value = await getBillingSummary()
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    try {
      await logoutAccount()
    } catch {
      // ignore
    }
    user.value = null
    billing.value = null
  }

  async function refreshBilling() {
    if (!user.value) return
    billing.value = await getBillingSummary()
  }

  return { user, billing, loading, isLoggedIn, credits, init, login, register, logout, refreshBilling }
})
