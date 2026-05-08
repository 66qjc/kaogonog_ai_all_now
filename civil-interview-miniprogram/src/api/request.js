import { TOKEN_STORAGE_KEY, USERNAME_STORAGE_KEY } from '../utils/constants'
import { toast } from '../utils/navigation'

export const API_BASE = (import.meta.env.VITE_API_BASE || 'http://10.5.186.17:8003').replace(/\/$/, '')

function joinUrl(path = '') {
  const value = String(path || '')
  if (/^https?:\/\//.test(value)) return value
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
    return `后端服务连接失败：${API_BASE}。微信开发者工具在 Windows 中运行时，127.0.0.1 指向 Windows 本机；如果后端在 WSL、虚拟机或另一台机器，请把 .env 里的 VITE_API_BASE 改成可访问的局域网地址后重新构建。`
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
