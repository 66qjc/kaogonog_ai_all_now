import { request, uploadFile } from './request'

export function transcribeAudio(filePath, options = {}) {
  const mediaType = options.mediaType || 'audio'
  return uploadFile({
    url: '/scoring/transcribe',
    filePath,
    name: 'audio',
    timeout: mediaType === 'video' ? 120000 : 60000
  })
}

export function evaluateAnswer(data) {
  return request({
    url: '/scoring/evaluate',
    method: 'POST',
    data
  })
}

export function getScoringResult(examId, questionId) {
  return request({
    url: `/scoring/result/${examId}/${questionId}`
  })
}
