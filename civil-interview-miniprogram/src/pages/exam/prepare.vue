<template>
  <view class="page">
    <text class="page-title">模考准备</text>
    <text class="page-desc">小程序端支持麦克风录音和摄像头录像作答，提交后自动转写并评分。</text>

    <view v-if="readonlyMode" class="card tips-card">
      <text class="tips-card__title">界面预览</text>
      <text class="tips-card__line">当前仅展示页面结构，相关内容暂不展示。</text>
    </view>

    <view class="card">
      <view class="section-head">
        <text class="section-title">练习配置</text>
      </view>

      <view v-if="showPracticeConfig" class="config-row">
        <text>题目数量</text>
        <view class="stepper">
          <button class="stepper__button" @tap="decreaseCount">-</button>
          <text class="stepper__value">{{ count }}</text>
          <button class="stepper__button" @tap="increaseCount">+</button>
        </view>
      </view>

      <view class="config-row">
        <text>练习模式</text>
      </view>
      <view class="mode-grid">
        <view class="mode-card" :class="{ 'mode-card--active': mode === 'free' }" @tap="mode = 'free'">
          <text class="mode-card__title">自由练习</text>
          <text class="mode-card__desc">适合单题拆解和即时复盘</text>
        </view>
        <view class="mode-card" :class="{ 'mode-card--active': mode === 'mock' }" @tap="mode = 'mock'">
          <text class="mode-card__title">模拟面试</text>
          <text class="mode-card__desc">按准备和作答计时推进</text>
        </view>
      </view>

      <view v-if="showPracticeConfig" class="question-type-panel">
        <view class="config-row config-row--type">
          <text>题目类型</text>
          <text class="config-row__value">{{ selectedCategoryName }}</text>
        </view>
        <view class="type-chip-grid">
          <view
            v-for="item in questionCategoryOptions"
            :key="item.key"
            class="type-chip"
            :class="{
              'type-chip--active': isTypeSelected(item.key),
              'type-chip--disabled': item.key === RANDOM_DIMENSION_KEY && selectedSpecificDimensions.length > 0
            }"
            @tap="toggleQuestionType(item.key)"
          >
            <text>{{ item.name }}</text>
          </view>
        </view>
      </view>
    </view>

    <view class="card tips-card">
      <text class="tips-card__title">开考前检查</text>
      <text class="tips-card__line">保持环境安静，进入考场后请授权麦克风和摄像头。</text>
      <text class="tips-card__line">真机调试时，后端地址需使用手机可访问的域名或局域网 IP。</text>
    </view>

    <button class="primary-button" :disabled="loading || accessLoading" :loading="loading || accessLoading" @tap="startPractice">进入考场</button>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import { useExamStore } from '../../stores/exam'
import { useBillingStore } from '../../stores/billing'
import { useQuestionBankStore } from '../../stores/questionBank'
import { useSubscriptionStore } from '../../stores/subscription'
import { useUserStore } from '../../stores/user'
import { getQuestionById } from '../../api/questionBank'
import { getTrialQuestion, getTrialStatus } from '../../api/trial'
import { hideLoading, requireLogin, showLoading, toast } from '../../utils/navigation'
import { QUESTION_CATEGORIES } from '../../utils/constants'

const examStore = useExamStore()
const billingStore = useBillingStore()
const questionBankStore = useQuestionBankStore()
const subscriptionStore = useSubscriptionStore()
const userStore = useUserStore()
const DEFAULT_EXAM_QUESTION_COUNT = 5
const MAX_FREE_QUESTION_COUNT = 10
const count = ref(DEFAULT_EXAM_QUESTION_COUNT)
const mode = ref('free')
const selectedDimensions = ref(['random'])
const loading = ref(false)
const accessLoading = ref(false)
const trial = ref(false)
const trialStatus = ref(null)
const hasFullAccess = computed(() => {
  return billingStore.isPaid
    || subscriptionStore.status.hasActivePlan
    || userStore.isAdmin
    || userStore.userInfo?.billing?.isPaid === true
    || userStore.userInfo?.permissions?.canAccessPremiumModules === true
})
const readonlyMode = computed(() => !trial.value && !hasFullAccess.value)
const RANDOM_DIMENSION_KEY = 'random'
const questionCategoryOptions = [
  { key: RANDOM_DIMENSION_KEY, name: '随机题型' },
  ...QUESTION_CATEGORIES.filter((item) => item.key)
]
const showPracticeConfig = computed(() => mode.value === 'free')
const selectedSpecificDimensions = computed(() => selectedDimensions.value.filter((item) => item && item !== RANDOM_DIMENSION_KEY))
const selectedDimensionParam = computed(() => selectedSpecificDimensions.value.join(','))
const selectedCategoryName = computed(() => {
  if (!selectedSpecificDimensions.value.length) return '随机题型'
  const names = selectedSpecificDimensions.value
    .map((key) => questionCategoryOptions.find((item) => item.key === key)?.name)
    .filter(Boolean)
  return names.join('、') || '随机题型'
})

onLoad((query) => {
  const requestedTrial = String(query?.trial || '') === '1'
  trial.value = requestedTrial && !hasFullAccess.value
  if (trial.value) count.value = 1
})

onShow(() => {
  refreshAccessState().catch(() => null)
})

async function refreshAccessState() {
  if (!userStore.isAuthenticated) return false
  accessLoading.value = true
  try {
    await Promise.allSettled([
      userStore.loadUserInfo(),
      subscriptionStore.refresh({ skipErrorHandler: true })
    ])
    if (hasFullAccess.value && trial.value) {
      trial.value = false
      count.value = DEFAULT_EXAM_QUESTION_COUNT
    }
    if (trial.value) {
      trialStatus.value = await getTrialStatus({ skipErrorHandler: true }).catch(() => null)
    }
    return hasFullAccess.value
  } finally {
    accessLoading.value = false
  }
}

function decreaseCount() {
  count.value = Math.max(1, count.value - 1)
}

function increaseCount() {
  if (trial.value) return
  count.value = Math.min(MAX_FREE_QUESTION_COUNT, count.value + 1)
}

function isTypeSelected(key) {
  return selectedDimensions.value.includes(key)
}

function toggleQuestionType(key) {
  if (key === RANDOM_DIMENSION_KEY) {
    if (selectedSpecificDimensions.value.length) return
    selectedDimensions.value = [RANDOM_DIMENSION_KEY]
    return
  }

  const specific = selectedSpecificDimensions.value
  if (specific.includes(key)) {
    const next = specific.filter((item) => item !== key)
    selectedDimensions.value = next.length ? next : [RANDOM_DIMENSION_KEY]
    return
  }

  selectedDimensions.value = [...specific, key]
}

async function startPractice() {
  if (!requireLogin()) return
  if (loading.value) return
  await refreshAccessState().catch(() => null)
  if (trial.value && trialStatus.value?.trialCompleted) {
    toast('试用已完成，请开通套餐后继续练习')
    return
  }
  if (readonlyMode.value) {
    toast('请先开通套餐后进入正式考场')
    return
  }
  loading.value = true
  showLoading('抽取题目')
  try {
    let questions = []
    if (trial.value) {
      try {
        const trialQuestion = await getTrialQuestion()
        if (trialQuestion?.id) {
          questions = [trialQuestion]
        } else {
          const fallbackQuestion = await getQuestionById('q001')
          questions = fallbackQuestion?.id ? [fallbackQuestion] : []
        }
      } catch {
        const fallbackQuestion = await getQuestionById('q001')
        questions = fallbackQuestion?.id ? [fallbackQuestion] : []
      }
    } else {
      if (!userStore.isAdmin) {
        const access = await subscriptionStore.check(mode.value === 'mock' ? 'mock' : 'practice', { skipErrorHandler: true }).catch(() => null)
        if (access && access.allowed === false) {
          toast(access.reason || '当前套餐额度不足')
          return
        }
      }
      questions = await questionBankStore.fetchRandom({
        province: userStore.selectedProvince,
        count: mode.value === 'mock' ? DEFAULT_EXAM_QUESTION_COUNT : count.value,
        dimension: mode.value === 'mock' ? '' : selectedDimensionParam.value
      })
    }

    if (!questions.length) {
      toast(trial.value ? '试用题暂不可用，请稍后重试' : '当前筛选条件暂无题目')
      return
    }
    const targetCount = trial.value ? 1 : mode.value === 'mock' ? DEFAULT_EXAM_QUESTION_COUNT : count.value
    await examStore.startFromQuestions(questions.slice(0, targetCount), trial.value ? 'trial' : mode.value)
    uni.navigateTo({ url: '/pages/exam/room' })
  } catch (error) {
    toast(error?.message || '进入考场失败')
  } finally {
    loading.value = false
    hideLoading()
  }
}
</script>

<style scoped>
.config-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18rpx 0;
  color: #2a3648;
  font-size: 28rpx;
  font-weight: 600;
}

.config-row__value {
  flex: 1;
  margin-left: 24rpx;
  color: #1b5faa;
  font-weight: 700;
  text-align: right;
}

.config-row--type {
  padding-bottom: 10rpx;
  align-items: flex-start;
}

.question-type-panel {
  margin-top: 10rpx;
}

.type-chip-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 14rpx;
  padding-top: 6rpx;
}

.type-chip {
  min-width: 148rpx;
  padding: 16rpx 20rpx;
  border: 1rpx solid #d9e3ef;
  border-radius: 14rpx;
  background: #ffffff;
  color: #2a3648;
  font-size: 25rpx;
  font-weight: 700;
  text-align: center;
}

.type-chip--active {
  border-color: #1b5faa;
  background: #e8f4fd;
  color: #1b5faa;
}

.type-chip--disabled {
  opacity: 0.45;
}

.stepper {
  display: flex;
  align-items: center;
  overflow: hidden;
  border: 1rpx solid #d9e3ef;
  border-radius: 12rpx;
}

.stepper__button {
  width: 76rpx;
  height: 68rpx;
  border-radius: 0;
  background: #f6f8fb;
  color: #1b5faa;
  font-size: 34rpx;
}

.stepper__value {
  width: 86rpx;
  color: #1a1a2e;
  font-size: 30rpx;
  font-weight: 800;
  text-align: center;
}

.mode-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16rpx;
  margin-top: 8rpx;
}

.mode-card {
  min-height: 150rpx;
  padding: 22rpx;
  border: 1rpx solid #d9e3ef;
  border-radius: 16rpx;
  background: #ffffff;
}

.mode-card--active {
  border-color: #1b5faa;
  background: #e8f4fd;
}

.mode-card__title,
.mode-card__desc {
  display: block;
}

.mode-card__title {
  color: #1a1a2e;
  font-size: 29rpx;
  font-weight: 800;
}

.mode-card__desc {
  margin-top: 10rpx;
  color: #6f7c8f;
  font-size: 23rpx;
  line-height: 1.5;
}

.tips-card__title,
.tips-card__line {
  display: block;
}

.tips-card__title {
  color: #1a1a2e;
  font-size: 30rpx;
  font-weight: 800;
}

.tips-card__line {
  margin-top: 12rpx;
  color: #6f7c8f;
  font-size: 24rpx;
  line-height: 1.6;
}
</style>
