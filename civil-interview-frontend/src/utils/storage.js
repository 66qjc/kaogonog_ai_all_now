// 安全的 localStorage 操作
import { logger } from '@/utils/logger'

const isStorageAvailable = () => {
  try {
    const test = '__test__'
    localStorage.setItem(test, test)
    localStorage.removeItem(test)
    return true
  } catch (e) {
    return false
  }
}

export const storage = {
  get(key, defaultValue = null) {
    if (!isStorageAvailable()) return defaultValue
    try {
      const item = localStorage.getItem(key)
      return item ? JSON.parse(item) : defaultValue
    } catch (e) {
      logger.warn('Storage read failed', {
        event: 'storage.read.failed',
        key,
        error: e
      })
      return defaultValue
    }
  },

  set(key, value) {
    if (!isStorageAvailable()) return false
    try {
      localStorage.setItem(key, JSON.stringify(value))
      return true
    } catch (e) {
      logger.warn('Storage write failed', {
        event: 'storage.write.failed',
        key,
        error: e
      })
      return false
    }
  },

  remove(key) {
    if (!isStorageAvailable()) return false
    try {
      localStorage.removeItem(key)
      return true
    } catch (e) {
      logger.warn('Storage remove failed', {
        event: 'storage.remove.failed',
        key,
        error: e
      })
      return false
    }
  }
}
