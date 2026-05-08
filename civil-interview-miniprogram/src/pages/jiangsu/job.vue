<template>
  <view class="page">
    <view class="job-hero card">
      <text class="job-hero__eyebrow">2026 江苏事业单位统考</text>
      <text class="job-hero__title">{{ category.title }}</text>
      <text class="job-hero__desc">{{ category.scope }} · {{ category.subtitle }}</text>
      <text class="job-hero__tag">{{ category.hot }}</text>
    </view>

    <view class="filter-card card">
      <view class="filter-block">
        <text class="filter-block__label">地市</text>
        <scroll-view scroll-x class="filter-scroll">
          <view class="filter-scroll__inner">
            <view
              v-for="city in JIANGSU_CITY_FILTERS"
              :key="city.key"
              class="chip"
              :class="{ 'chip--active': filters.city === city.key }"
              @tap="filters.city = city.key"
            >
              {{ city.name }}
            </view>
          </view>
        </scroll-view>
      </view>

      <view class="filter-block">
        <text class="filter-block__label">年份</text>
        <view class="chip-row">
          <view class="chip" :class="{ 'chip--active': filters.year === '' }" @tap="filters.year = ''">全部</view>
          <view
            v-for="year in JIANGSU_YEAR_FILTERS"
            :key="year"
            class="chip"
            :class="{ 'chip--active': filters.year === year }"
            @tap="filters.year = year"
          >
            {{ year }}
          </view>
        </view>
      </view>

      <view class="filter-block">
        <text class="filter-block__label">题型</text>
        <view class="chip-row">
          <view class="chip" :class="{ 'chip--active': filters.type === '' }" @tap="filters.type = ''">全部</view>
          <view
            v-for="type in JIANGSU_QUESTION_TYPES"
            :key="type.key"
            class="chip"
            :class="{ 'chip--active': filters.type === type.key }"
            @tap="filters.type = type.key"
          >
            {{ type.name }}
          </view>
        </view>
      </view>
    </view>

    <view class="section-head">
      <text class="section-title">题目列表</text>
      <text class="muted">按年份倒序 · {{ filteredItems.length }} 题</text>
    </view>

    <view v-if="filteredItems.length">
      <view v-for="item in filteredItems" :key="item.id" class="question-card card">
        <view class="question-card__meta">
          <text>{{ item.date }}</text>
          <text>{{ item.cityName }}</text>
          <text>{{ item.typeName }}</text>
        </view>
        <text class="question-card__title">{{ item.title }}</text>
        <text class="question-card__stem">{{ item.stem }}</text>
        <button class="primary-button question-card__button" @tap="goPractice">开始刷题</button>
      </view>
    </view>
    <view v-else class="card">
      <EmptyState title="暂无匹配题目" desc="换个地市、年份或题型再试。" />
    </view>
  </view>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import EmptyState from '../../components/EmptyState.vue'
import {
  JIANGSU_CITY_FILTERS,
  JIANGSU_QUESTION_TYPES,
  JIANGSU_YEAR_FILTERS,
  buildJiangsuQuestionItems,
  filterJiangsuQuestionItems,
  getJiangsuJobCategory
} from '../../utils/jiangsuJobs'

const categoryKey = ref('a')
const filters = reactive({
  city: 'all',
  year: '',
  type: ''
})

const category = computed(() => getJiangsuJobCategory(categoryKey.value))
const allItems = computed(() => buildJiangsuQuestionItems(category.value.key))
const filteredItems = computed(() => filterJiangsuQuestionItems(allItems.value, filters))

onLoad((query) => {
  categoryKey.value = query?.category || 'a'
})

function goPractice() {
  uni.navigateTo({ url: '/pages/exam/prepare' })
}
</script>

<style scoped>
.job-hero {
  background: linear-gradient(135deg, #ffffff 0%, #edf7ff 100%);
}

.job-hero__eyebrow,
.job-hero__title,
.job-hero__desc,
.job-hero__tag {
  display: block;
}

.job-hero__eyebrow {
  color: #1b5faa;
  font-size: 24rpx;
  font-weight: 700;
}

.job-hero__title {
  margin-top: 10rpx;
  color: #1a1a2e;
  font-size: 40rpx;
  font-weight: 900;
}

.job-hero__desc {
  margin-top: 8rpx;
  color: #6f7c8f;
  font-size: 25rpx;
}

.job-hero__tag {
  align-self: flex-start;
  margin-top: 18rpx;
  padding: 8rpx 18rpx;
  border-radius: 999rpx;
  background: #e8f4fd;
  color: #1b5faa;
  font-size: 23rpx;
  font-weight: 700;
}

.filter-card {
  padding-bottom: 10rpx;
}

.filter-block {
  margin-bottom: 22rpx;
}

.filter-block__label {
  display: block;
  margin-bottom: 14rpx;
  color: #1a1a2e;
  font-size: 27rpx;
  font-weight: 800;
}

.filter-scroll {
  width: 100%;
  white-space: nowrap;
}

.filter-scroll__inner {
  display: inline-flex;
  gap: 14rpx;
  padding-bottom: 4rpx;
}

.question-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
  margin-bottom: 14rpx;
}

.question-card__meta text {
  padding: 6rpx 14rpx;
  border-radius: 999rpx;
  background: #f0f5fa;
  color: #45617e;
  font-size: 22rpx;
}

.question-card__title,
.question-card__stem {
  display: block;
}

.question-card__title {
  color: #1a1a2e;
  font-size: 30rpx;
  font-weight: 800;
  line-height: 1.5;
}

.question-card__stem {
  margin-top: 10rpx;
  color: #6f7c8f;
  font-size: 25rpx;
  line-height: 1.6;
}

.question-card__button {
  margin-top: 20rpx;
}
</style>
