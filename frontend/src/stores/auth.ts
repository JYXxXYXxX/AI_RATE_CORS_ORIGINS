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
  const pendingVerificationEmail = ref('')
  const pendingDevVerificationUrl = ref('')

  const isLoggedIn = computed(() => !!user.value)
  const credits = computed(() => billing.value?.user.credits_balance ?? 0)

  async function refreshBillingAfterAuth() {
    try {
      billing.value = await getBillingSummary()
    } catch {
      billing.value = null
    }
  }

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
      if (session.status === 'pending_verification') {
        user.value = null
        billing.value = null
        pendingVerificationEmail.value = session.email || email
        pendingDevVerificationUrl.value = session.dev_verification_url || ''
        return session
      }
      user.value = session.user || null
      await refreshBillingAfterAuth()
      pendingVerificationEmail.value = ''
      pendingDevVerificationUrl.value = ''
      return session
    } finally {
      loading.value = false
    }
  }

  async function register(email: string, password: string, displayName?: string) {
    loading.value = true
    try {
      const session = await registerAccount({ email, password, displayName })
      if (session.status === 'pending_verification') {
        user.value = null
        billing.value = null
        pendingVerificationEmail.value = session.email || email
        pendingDevVerificationUrl.value = session.dev_verification_url || ''
        return session
      }
      user.value = session.user || null
      await refreshBillingAfterAuth()
      pendingVerificationEmail.value = ''
      pendingDevVerificationUrl.value = ''
      return session
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
    pendingVerificationEmail.value = ''
    pendingDevVerificationUrl.value = ''
  }

  async function refreshBilling() {
    if (!user.value) return
    billing.value = await getBillingSummary()
  }

  function setPendingVerification(email: string, devUrl?: string | null) {
    pendingVerificationEmail.value = email
    pendingDevVerificationUrl.value = devUrl || ''
  }

  function clearPendingVerification() {
    pendingVerificationEmail.value = ''
    pendingDevVerificationUrl.value = ''
  }

  return {
    user,
    billing,
    loading,
    isLoggedIn,
    credits,
    pendingVerificationEmail,
    pendingDevVerificationUrl,
    init,
    login,
    register,
    logout,
    refreshBilling,
    setPendingVerification,
    clearPendingVerification
  }
})
