import { request } from './request'

export function reportUsage(data) {
  return request({
    url: '/usage/report',
    method: 'POST',
    data,
    skipErrorHandler: true
  })
}
