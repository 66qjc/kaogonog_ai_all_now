<template>
  <view class="page page--tab">
    <text class="page-title">定向备面</text>
    <text class="page-desc">选择省份与岗位系统，生成更贴近报考方向的训练题。</text>

    <view v-if="readonlyMode" class="card">
      <view class="section-head">
        <text class="section-title">界面预览</text>
      </view>
      <text class="muted">当前仅展示页面结构，相关内容暂不展示。</text>
    </view>

    <view class="card">
      <view class="section-head">
        <text class="section-title">选择省份</text>
      </view>
      <view class="chip-row">
        <view
          v-for="province in PROVINCES"
          :key="province.code"
          class="chip"
          :class="{ 'chip--active': selectedProvince === province.code }"
          @tap="selectedProvince = province.code"
        >
          {{ province.name }}
        </view>
      </view>
    </view>

    <view class="card">
      <view class="section-head">
        <text class="section-title">选择岗位系统</text>
      </view>
      <view class="chip-row">
        <view
          v-for="position in currentPositionSystems"
          :key="position.code"
          class="chip"
          :class="{ 'chip--active': selectedPosition === position.code }"
          @tap="selectedPosition = position.code"
        >
          <text class="chip__name">{{ position.name }}</text>
          <text v-if="position.desc" class="chip__desc">{{ position.desc }}</text>
        </view>
      </view>
    </view>

    <view class="targeted-actions">
      <button class="primary-button" :disabled="readonlyMode || !canProceed" @tap="goFocus">分析面试重点</button>
      <button class="secondary-button" :disabled="readonlyMode || !canProceed" :loading="targetedStore.generateLoading" @tap="generate">
        生成题目
      </button>
    </view>

    <view v-if="!readonlyMode && targetedStore.generatedQuestions.length">
      <view class="section-head">
        <text class="section-title">生成题目</text>
        <text class="muted" @tap="generate">重新生成</text>
      </view>
      <QuestionCard
        v-for="question in targetedStore.generatedQuestions"
        :key="question.id"
        :question="question"
        @select="startQuestion"
      />
    </view>
  </view>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import QuestionCard from '../../components/QuestionCard.vue'
import { useBillingStore } from '../../stores/billing'
import { useExamStore } from '../../stores/exam'
import { useTargetedStore } from '../../stores/targeted'
import { POSITION_SYSTEMS, PROVINCES } from '../../utils/constants'
import { JIANGSU_TARGETED_POSITIONS } from '../../utils/jiangsuJobs'
import { hideLoading, requireLogin, showLoading, toast } from '../../utils/navigation'

const billingStore = useBillingStore()
const targetedStore = useTargetedStore()
const examStore = useExamStore()
const selectedProvince = ref(targetedStore.selectedProvince || 'national')
const selectedPosition = ref(targetedStore.selectedPosition || 'general')
const currentPositionSystems = computed(() => (
  selectedProvince.value === 'jiangsu' ? JIANGSU_TARGETED_POSITIONS : POSITION_SYSTEMS
))
const canProceed = computed(() => !!selectedProvince.value && !!selectedPosition.value)
const readonlyMode = computed(() => !billingStore.isPaid)

function getDefaultPositionCode() {
  if (selectedProvince.value === 'jiangsu') return JIANGSU_TARGETED_POSITIONS[0]?.code || ''
  return POSITION_SYSTEMS.find((item) => item.code === 'general')?.code || POSITION_SYSTEMS[0]?.code || ''
}

watch(selectedProvince, () => {
  if (!currentPositionSystems.value.some((item) => item.code === selectedPosition.value)) {
    selectedPosition.value = getDefaultPositionCode()
  }
}, { immediate: true })

onShow(() => {
  requireLogin()
})

function syncSelection() {
  targetedStore.setSelection(selectedProvince.value, selectedPosition.value)
}

function goFocus() {
  if (readonlyMode.value) return
  if (!canProceed.value) return
  syncSelection()
  uni.navigateTo({ url: '/pages/targeted/focus' })
}

async function generate() {
  if (readonlyMode.value) return
  if (!canProceed.value) {
    toast('请先选择省份和岗位系统')
    return
  }
  syncSelection()
  showLoading('生成题目')
  try {
    const questions = await targetedStore.fetchGeneratedQuestions(5)
    if (!questions.length) toast('暂未生成题目')
  } catch (error) {
    toast(error?.message || '生成失败')
  } finally {
    hideLoading()
  }
}

async function startQuestion(question) {
  if (readonlyMode.value) return
  showLoading('创建考场')
  try {
    await examStore.startFromQuestions([question], 'targeted')
    uni.navigateTo({ url: '/pages/exam/room' })
  } catch (error) {
    toast(error?.message || '无法开始练习')
  } finally {
    hideLoading()
  }
}
</script>

<style scoped>
.targeted-actions {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 220rpx;
  gap: 16rpx;
  margin-bottom: 28rpx;
}

.chip {
  display: inline-flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4rpx;
}

.chip__name,
.chip__desc {
  display: block;
}

.chip__desc {
  font-size: 21rpx;
  line-height: 1.25;
  opacity: 0.78;
}
</style>
