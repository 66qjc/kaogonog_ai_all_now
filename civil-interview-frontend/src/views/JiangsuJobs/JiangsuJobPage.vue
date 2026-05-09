<template>
  <div class="jiangsu-job-page page-container">
    <div class="jiangsu-job-hero card">
      <a-button type="link" class="jiangsu-job-hero__back" @click="$router.push('/')">
        返回首页
      </a-button>
      <div class="jiangsu-job-hero__main">
        <div>
          <div class="jiangsu-job-hero__eyebrow">2026 江苏事业单位统考</div>
          <h1>{{ category.title }}</h1>
          <p>{{ categoryMeta }}</p>
        </div>
        <a-tag color="blue">{{ category.hot }}</a-tag>
      </div>
    </div>

    <div class="jiangsu-job-filters card">
      <div class="filter-row">
        <span class="filter-row__label">地市</span>
        <a-radio-group v-model:value="filters.city" size="small">
          <a-radio-button v-for="city in JIANGSU_CITY_FILTERS" :key="city.key" :value="city.key">
            {{ city.name }}
          </a-radio-button>
        </a-radio-group>
      </div>
      <div class="filter-row">
        <span class="filter-row__label">年份</span>
        <a-radio-group v-model:value="filters.year" size="small">
          <a-radio-button value="">全部</a-radio-button>
          <a-radio-button v-for="year in JIANGSU_YEAR_FILTERS" :key="year" :value="year">
            {{ year }}
          </a-radio-button>
        </a-radio-group>
      </div>
      <div class="filter-row">
        <span class="filter-row__label">题型</span>
        <a-radio-group v-model:value="filters.type" size="small">
          <a-radio-button value="">全部</a-radio-button>
          <a-radio-button v-for="type in JIANGSU_QUESTION_TYPES" :key="type.key" :value="type.key">
            {{ type.name }}
          </a-radio-button>
        </a-radio-group>
      </div>
    </div>

    <div class="jiangsu-job-list">
      <div class="jiangsu-job-list__head">
        <h2>题目列表</h2>
        <span>按年份倒序 · {{ filteredItems.length }} 题</span>
      </div>

      <div v-if="filteredItems.length">
        <div v-for="item in filteredItems" :key="item.id" class="jiangsu-question-card card">
          <div class="jiangsu-question-card__top">
            <a-tag color="blue">{{ item.date }}</a-tag>
            <a-tag>{{ item.cityName }}</a-tag>
            <a-tag color="green">{{ item.typeName }}</a-tag>
          </div>
          <h3>{{ item.title }}</h3>
          <p>{{ item.stem }}</p>
          <div class="jiangsu-question-card__actions">
            <a-button type="primary" size="small" @click="$router.push('/exam/prepare')">
              开始刷题
            </a-button>
            <a-button size="small" @click="$router.push('/bank')">去题库筛选</a-button>
          </div>
        </div>
      </div>
      <EmptyState v-else text="暂无匹配题目，请调整筛选条件" />
    </div>
  </div>
</template>

<script setup>
import { computed, reactive } from 'vue'
import { useRoute } from 'vue-router'
import EmptyState from '@/components/common/EmptyState.vue'
import {
  JIANGSU_CITY_FILTERS,
  JIANGSU_QUESTION_TYPES,
  JIANGSU_YEAR_FILTERS,
  buildJiangsuQuestionItems,
  filterJiangsuQuestionItems,
  getJiangsuJobCategory
} from '@/utils/jiangsuJobs'

const route = useRoute()
const category = computed(() => getJiangsuJobCategory(String(route.params.category || 'a')))
const categoryMeta = computed(() => [category.value.scope, category.value.subtitle].filter(Boolean).join(' · '))
const allItems = computed(() => buildJiangsuQuestionItems(category.value.key))
const filters = reactive({
  city: 'all',
  year: '',
  type: ''
})
const filteredItems = computed(() => filterJiangsuQuestionItems(allItems.value, filters))
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.jiangsu-job-hero {
  padding: 20px;
  border: 1px solid fade(@primary-color, 10%);
  background: linear-gradient(135deg, #ffffff 0%, #edf7ff 100%);
}

.jiangsu-job-hero__back {
  padding: 0;
  margin-bottom: 10px;
}

.jiangsu-job-hero__main {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;

  h1 {
    margin: 4px 0;
    color: @text-primary;
    font-size: @font-size-xxl;
  }

  p {
    margin: 0;
    color: @text-secondary;
    font-size: @font-size-sm;
  }
}

.jiangsu-job-hero__eyebrow {
  color: @primary-color;
  font-size: @font-size-sm;
  font-weight: 600;
}

.jiangsu-job-filters {
  margin-top: 12px;
  padding: 14px 16px;
}

.filter-row {
  display: grid;
  grid-template-columns: 52px minmax(0, 1fr);
  gap: 10px;
  align-items: flex-start;
  padding: 8px 0;

  :deep(.ant-radio-group) {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  :deep(.ant-radio-button-wrapper) {
    border-radius: 6px;
    border-inline-start-width: 1px;
  }

  :deep(.ant-radio-button-wrapper::before) {
    display: none;
  }
}

.filter-row__label {
  color: @text-primary;
  font-size: @font-size-sm;
  font-weight: 600;
  line-height: 24px;
}

.jiangsu-job-list {
  margin-top: 16px;
}

.jiangsu-job-list__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;

  h2 {
    margin: 0;
    color: @text-primary;
    font-size: @font-size-lg;
  }

  span {
    color: @text-secondary;
    font-size: @font-size-xs;
  }
}

.jiangsu-question-card {
  margin-bottom: 10px;
  padding: 14px 16px;

  h3 {
    margin: 8px 0 6px;
    color: @text-primary;
    font-size: @font-size-base;
    font-weight: 700;
  }

  p {
    margin: 0;
    color: @text-regular;
    font-size: @font-size-sm;
    line-height: 1.7;
  }
}

.jiangsu-question-card__top,
.jiangsu-question-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.jiangsu-question-card__actions {
  justify-content: flex-end;
  margin-top: 12px;
}

@media (max-width: 560px) {
  .jiangsu-job-hero__main,
  .jiangsu-job-list__head {
    align-items: flex-start;
    flex-direction: column;
  }

  .filter-row {
    grid-template-columns: 1fr;
  }
}
</style>
