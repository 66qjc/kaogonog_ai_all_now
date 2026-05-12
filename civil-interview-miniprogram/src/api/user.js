import { request } from './request'

export function getUserInfo(config = {}) {
  return request({
    url: '/user/info',
    ...config
  })
}

export function getProvinces() {
  return request({
    url: '/user/provinces'
  })
}

export function updatePreferences(data) {
  return request({
    url: '/user/preferences',
    method: 'PUT',
    data
  })
}

export function updateUserProfile(data) {
  return request({
    url: '/user/profile',
    method: 'PUT',
    data
  })
}

export function updatePassword(data) {
  return request({
    url: '/user/password',
    method: 'PUT',
    data
  })
}

export function getTermsStatus(config = {}) {
  return request({
    url: '/user/terms-status',
    ...config
  })
}

export function agreeTerms(version) {
  return request({
    url: '/user/agree-terms',
    method: 'POST',
    data: { version }
  })
}

export function getDeviceRisk(deviceId, config = {}) {
  return request({
    url: '/user/device-risk',
    header: {
      'X-Device-ID': deviceId || ''
    },
    ...config
  })
}
