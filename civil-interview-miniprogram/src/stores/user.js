import { defineStore } from 'pinia'
import { login as loginApi, register as registerApi } from '../api/auth'
import { getProvinces, getUserInfo, updatePreferences } from '../api/user'
import { useBillingStore } from './billing'
import {
  DEFAULT_PREFERENCES,
  PREFERENCES_STORAGE_KEY,
  PROVINCE_STORAGE_KEY,
  PROVINCES,
  TOKEN_STORAGE_KEY,
  USERNAME_STORAGE_KEY
} from '../utils/constants'

function readStorage(key, fallback = '') {
  try {
    const value = uni.getStorageSync(key)
    return value === '' || value === undefined ? fallback : value
  } catch {
    return fallback
  }
}

function readJsonStorage(key, fallback) {
  try {
    const value = uni.getStorageSync(key)
    if (!value) return fallback
    return typeof value === 'string' ? JSON.parse(value) : value
  } catch {
    return fallback
  }
}

function normalizePreferences(preferences = {}) {
  const merged = {
    ...DEFAULT_PREFERENCES,
    ...(preferences || {})
  }
  return {
    defaultPrepTime: Math.max(30, Number(merged.defaultPrepTime) || DEFAULT_PREFERENCES.defaultPrepTime),
    defaultAnswerTime: Math.max(60, Number(merged.defaultAnswerTime) || DEFAULT_PREFERENCES.defaultAnswerTime),
    enableAudio: merged.enableAudio !== false
  }
}

export const useUserStore = defineStore('user', {
  state: () => ({
    token: readStorage(TOKEN_STORAGE_KEY, ''),
    username: readStorage(USERNAME_STORAGE_KEY, ''),
    userInfo: {
      id: '',
      name: '',
      avatar: '',
      province: readStorage(PROVINCE_STORAGE_KEY, 'national'),
      role: 'user',
      isAdmin: false,
      billing: {
        planType: 'trial',
        isPaid: false
      },
      permissions: {
        canManageQuestionBank: false,
        canAccessPremiumModules: false
      }
    },
    selectedProvince: readStorage(PROVINCE_STORAGE_KEY, 'national'),
    provinces: PROVINCES,
    preferences: normalizePreferences(readJsonStorage(PREFERENCES_STORAGE_KEY, DEFAULT_PREFERENCES))
  }),

  getters: {
    isAuthenticated(state) {
      return !!state.token
    },
    isAdmin(state) {
      return !!state.userInfo?.isAdmin || state.username === 'admin' || state.userInfo?.id === 'admin'
    },
    displayName(state) {
      const baseName = state.userInfo?.name || state.username || '考生'
      const isAdmin = !!state.userInfo?.isAdmin || state.username === 'admin' || state.userInfo?.id === 'admin'
      return isAdmin ? `${baseName}（管理员权限）` : baseName
    },
    selectedProvinceName(state) {
      return state.provinces.find((item) => item.code === state.selectedProvince)?.name || '国考'
    }
  },

  actions: {
    async login(username, password) {
      const response = await loginApi(username, password)
      this.token = response.access_token
      this.username = username
      uni.setStorageSync(TOKEN_STORAGE_KEY, response.access_token)
      uni.setStorageSync(USERNAME_STORAGE_KEY, username)
      await this.loadUserInfo().catch(() => null)
      return response
    },

    async register(form) {
      return registerApi(form)
    },

    logout() {
      this.token = ''
      this.username = ''
      this.userInfo = {
        id: '',
        name: '',
        avatar: '',
        province: 'national',
        role: 'user',
        isAdmin: false,
        billing: {
          planType: 'trial',
          isPaid: false
        },
        permissions: {
          canManageQuestionBank: false,
          canAccessPremiumModules: false
        }
      }
      uni.removeStorageSync(TOKEN_STORAGE_KEY)
      uni.removeStorageSync(USERNAME_STORAGE_KEY)
    },

    async loadUserInfo() {
      const billingStore = useBillingStore()
      const info = await getUserInfo({ skipErrorHandler: true })
      const username = info?.id || this.username
      const isAdmin = !!info?.isAdmin || username === 'admin'
      const permissions = {
        canManageQuestionBank: isAdmin || !!info?.permissions?.canManageQuestionBank,
        canAccessPremiumModules: isAdmin || !!info?.permissions?.canAccessPremiumModules
      }
      const billing = {
        planType: info?.billing?.planType || 'trial',
        remainingSeconds: Number(info?.billing?.remainingSeconds || 0),
        monthlyExpireAt: Number(info?.billing?.monthlyExpireAt || 0),
        activatedAt: Number(info?.billing?.activatedAt || 0),
        orderHistory: Array.isArray(info?.billing?.orderHistory) ? info.billing.orderHistory : [],
        isPaid: isAdmin || permissions.canAccessPremiumModules || info?.billing?.isPaid === true
      }
      this.username = username
      if (username) uni.setStorageSync(USERNAME_STORAGE_KEY, username)

      this.userInfo = {
        id: username,
        name: info?.name || username || '考生',
        avatar: info?.avatar || '',
        province: info?.province || this.selectedProvince || 'national',
        role: info?.role || 'user',
        isAdmin,
        billing,
        permissions
      }
      billingStore.applyBackendState(billing, permissions)
      if (info?.province) this.setProvince(info.province)
      if (info?.preferences) {
        this.preferences = normalizePreferences({
          ...this.preferences,
          ...info.preferences
        })
        uni.setStorageSync(PREFERENCES_STORAGE_KEY, JSON.stringify(this.preferences))
      }
      return this.userInfo
    },

    async validateSession() {
      if (!this.token) return false
      try {
        await this.loadUserInfo()
        return true
      } catch (error) {
        if (error?.statusCode === 401) {
          this.logout()
        }
        return false
      }
    },

    async loadProvinces() {
      try {
        const response = await getProvinces()
        if (Array.isArray(response) && response.length) {
          this.provinces = response
        }
      } catch {
        this.provinces = PROVINCES
      }
      return this.provinces
    },

    setProvince(code) {
      this.selectedProvince = code || 'national'
      this.userInfo = {
        ...this.userInfo,
        province: this.selectedProvince
      }
      uni.setStorageSync(PROVINCE_STORAGE_KEY, this.selectedProvince)
    },

    async savePreferences(preferences) {
      this.preferences = normalizePreferences(preferences)
      uni.setStorageSync(PREFERENCES_STORAGE_KEY, JSON.stringify(this.preferences))
      try {
        await updatePreferences(this.preferences)
      } catch {
        return this.preferences
      }
      return this.preferences
    }
  }
})
