import { request } from './request'

export function getTrialStatus(config = {}) {
  return request({
    url: '/trial/status',
    ...config
  })
}

export function getTrialQuestion() {
  return request({
    url: '/trial/question'
  })
}

export function completeTrial() {
  return request({
    url: '/trial/complete',
    method: 'POST',
    skipErrorHandler: true
  })
}
