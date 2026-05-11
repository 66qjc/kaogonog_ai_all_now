import { TOKEN_STORAGE_KEY, USERNAME_STORAGE_KEY } from '../utils/constants'
import { toast } from '../utils/navigation'

const RUNTIME_API_BASE_KEY = 'civil_runtime_api_base'
const STALE_API_BASE_PATTERNS = [
  /xzqianmianyuzhoukeji\.cn/i
]

function normalizeBase(base) {
  return String(base || '').trim().replace(/\/$/, '')
}

function isStaleApiBase(base) {
  return STALE_API_BASE_PATTERNS.some((pattern) => pattern.test(String(base || '')))
}

function resolveApiBase() {
  const runtimeBase = normalizeBase(uni.getStorageSync(RUNTIME_API_BASE_KEY))
  if (runtimeBase) {
    if (!isStaleApiBase(runtimeBase)) return runtimeBase
    uni.removeStorageSync(RUNTIME_API_BASE_KEY)
  }

  const h5Base = normalizeBase(import.meta.env.VITE_API_BASE_H5)
  const mpWeixinBase = normalizeBase(import.meta.env.VITE_API_BASE_MP_WEIXIN)
  const commonBase = normalizeBase(import.meta.env.VITE_API_BASE)

  // #ifdef MP-WEIXIN
  return mpWeixinBase || commonBase || 'http://127.0.0.1:8050'
  // #endif
  // #ifdef H5
  return h5Base || commonBase || '/api'
  // #endif
  return mpWeixinBase || h5Base || commonBase || '/api'
}

export const API_BASE = resolveApiBase()

function joinUrl(path = '') {
  const value = String(path || '')
  if (/^https?:\/\//.test(value)) return value
  if (!API_BASE) return value
  return `${API_BASE}${value.startsWith('/') ? value : `/${value}`}`
}

function getAuthHeader() {
  const token = uni.getStorageSync(TOKEN_STORAGE_KEY)
  return token ? { Authorization: `Bearer ${token}` } : {}
}

function normalizeErrorMessage(payload, fallback = '请求失败') {
  const detail = payload?.detail ?? payload?.message ?? payload
  if (Array.isArray(detail)) {
    return detail
      .map((item) => item?.msg || item?.message || item)
      .filter(Boolean)
      .join('; ') || fallback
  }
  if (detail && typeof detail === 'object') {
    return detail.msg || detail.message || fallback
  }
  return detail ? String(detail) : fallback
}

function handleUnauthorized() {
  uni.removeStorageSync(TOKEN_STORAGE_KEY)
  uni.removeStorageSync(USERNAME_STORAGE_KEY)
  toast('登录已过期，请重新登录')
  uni.reLaunch({ url: '/pages/login/index' })
}

function normalizeNetworkError(err) {
  const rawMessage = String(err?.errMsg || err?.message || '')
  if (
    rawMessage.includes('ERR_CONNECTION_REFUSED')
    || rawMessage.includes('request:fail')
    || rawMessage.includes('timeout')
  ) {
    return `后端服务连接失败：${API_BASE || '(未配置 API 地址)'}。请检查 VITE_API_BASE_MP_WEIXIN / VITE_API_BASE_H5 配置，或在运行时通过 uni.setStorageSync('${RUNTIME_API_BASE_KEY}', 'http://可访问地址:8050') 覆盖后重启小程序。`
  }
  return rawMessage || '网络请求失败，请检查后端服务'
}

export function request(options = {}) {
  const {
    url,
    method = 'GET',
    data = {},
    header = {},
    timeout = 30000,
    skipErrorHandler = false
  } = options

  return new Promise((resolve, reject) => {
    uni.request({
      url: joinUrl(url),
      method,
      data,
      timeout,
      header: {
        ...getAuthHeader(),
        ...header
      },
      success(res) {
        const status = Number(res.statusCode || 0)
        if (status >= 200 && status < 300) {
          resolve(res.data)
          return
        }

        const message = normalizeErrorMessage(res.data, status >= 500 ? '服务暂时不可用' : '请求失败')
        const error = new Error(message)
        error.statusCode = status
        error.data = res.data

        if (status === 401) {
          handleUnauthorized()
        } else if (!skipErrorHandler) {
          toast(message)
        }
        reject(error)
      },
      fail(err) {
        const error = new Error(normalizeNetworkError(err))
        if (!skipErrorHandler) toast(error.message)
        reject(error)
      }
    })
  })
}

export function uploadFile(options = {}) {
  const {
    url,
    filePath,
    name = 'file',
    formData = {},
    header = {},
    timeout = 60000,
    skipErrorHandler = false
  } = options

  return new Promise((resolve, reject) => {
    uni.uploadFile({
      url: joinUrl(url),
      filePath,
      name,
      formData,
      timeout,
      header: {
        ...getAuthHeader(),
        ...header
      },
      success(res) {
        const status = Number(res.statusCode || 0)
        let payload = res.data
        try {
          payload = typeof res.data === 'string' ? JSON.parse(res.data) : res.data
        } catch {
          payload = res.data
        }

        if (status >= 200 && status < 300) {
          resolve(payload)
          return
        }

        const message = normalizeErrorMessage(payload, status >= 500 ? '服务暂时不可用' : '上传失败')
        const error = new Error(message)
        error.statusCode = status
        error.data = payload
        if (status === 401) {
          handleUnauthorized()
        } else if (!skipErrorHandler) {
          toast(message)
        }
        reject(error)
      },
      fail(err) {
        const error = new Error(normalizeNetworkError(err))
        if (!skipErrorHandler) toast(error.message)
        reject(error)
      }
    })
  })
}
