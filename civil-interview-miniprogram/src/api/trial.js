import { request } from './request'

export function getTrialQuestion() {
  return request({
    url: '/trial/question'
  })
}
