import http from './index'

export function createPaymentOrder(data) {
  return http.post('/payment/orders', data)
}

export function getMyPaymentOrders() {
  return http.get('/payment/orders/me')
}

export function getPaymentOrder(orderNo) {
  return http.get(`/payment/orders/${encodeURIComponent(orderNo)}`)
}

export function mockWechatPaymentCallback(data) {
  return http.post('/payment/callback/wechat', {
    mode: 'mock',
    ...data
  })
}

export function getRefundBalanceStats(data = {}) {
  return http.post('/payment/admin/refund-stats', data)
}

export function applyRefund(data) {
  return http.post('/payment/admin/refund', data)
}
