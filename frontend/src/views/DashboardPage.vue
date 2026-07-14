<template>
  <PhroPageShell
    title="数据看板"
    subtitle="检测统计 · 缺陷分布 · 趋势分析"
    scroll-body
  >
    <div class="dashboard-fill">
      <div class="phro-stat-grid overview-stats">
      <div class="phro-stat-item">
        <div class="value">{{ stats.total_tasks ?? '-' }}</div>
        <div class="label">检测任务</div>
      </div>
      <div class="phro-stat-item">
        <div class="value">{{ stats.total_images ?? '-' }}</div>
        <div class="label">检测图像</div>
      </div>
      <div class="phro-stat-item">
        <div class="value">{{ stats.total_objects ?? '-' }}</div>
        <div class="label">缺陷总数</div>
      </div>
      <div class="phro-stat-item">
        <div class="value">{{ avgTime }}</div>
        <div class="label">平均推理 ms</div>
      </div>
      <div class="phro-stat-item">
        <div class="value">{{ yieldRate }}</div>
        <div class="label">批次良品率</div>
      </div>
    </div>

    <div class="dashboard-charts">
      <div class="phro-module chart-card">
        <h3 class="phro-module-title">缺陷类别分布</h3>
        <div ref="pieRef" class="chart-box" />
      </div>
      <div class="phro-module chart-card">
        <h3 class="phro-module-title">检测趋势</h3>
        <div ref="lineRef" class="chart-box" />
      </div>
    </div>

    <div class="phro-module chart-card chart-card--bar">
      <h3 class="phro-module-title">场景分布</h3>
      <div ref="barRef" class="chart-box chart-box--sm" />
    </div>
    </div>
  </PhroPageShell>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import * as echarts from 'echarts/core'
import { PieChart, LineChart, BarChart } from 'echarts/charts'
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import PhroPageShell from '@/components/layout/PhroPageShell.vue'
import { PCB_SCENE, DEFECT_COLORS } from '@/constants/pcbDefects'
import { mockGetStatistics, withApiFallback } from '@/services/spridsMock'
import { getStatisticsApi } from '@/api/history'

echarts.use([
  PieChart,
  LineChart,
  BarChart,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  CanvasRenderer,
])

const stats = ref({})
const pieRef = ref(null)
const lineRef = ref(null)
const barRef = ref(null)
let pieChart = null
let lineChart = null
let barChart = null

const avgTime = computed(() => {
  const v = stats.value.avg_inference_time
  return v != null ? Math.round(v) : '-'
})

const yieldRate = computed(() => {
  const images = stats.value.total_images || 0
  const objects = stats.value.total_objects || 0
  if (!images) return '-'
  const defective = Math.min(objects, images)
  return `${(((images - defective) / images) * 100).toFixed(1)}%`
})

const phroText = { color: '#d4bca8' }

function renderCharts() {
  const dist = stats.value.class_distribution || {}
  const pieData = Object.entries(dist).map(([name, value]) => ({
    name: PCB_SCENE.class_names_cn[name] || name,
    value,
    itemStyle: { color: DEFECT_COLORS[name] },
  }))

  if (pieRef.value) {
    if (!pieChart) pieChart = echarts.init(pieRef.value)
    pieChart.setOption({
      backgroundColor: 'transparent',
      textStyle: phroText,
      tooltip: { trigger: 'item' },
      legend: { bottom: 0, textStyle: phroText },
      series: [{
        type: 'pie',
        radius: ['40%', '68%'],
        center: ['50%', '45%'],
        data: pieData.length ? pieData : [{ name: '暂无数据', value: 1, itemStyle: { color: '#666' } }],
        label: { color: '#d4bca8' },
      }],
    })
  }

  const trend = stats.value.daily_trend || []
  if (lineRef.value) {
    if (!lineChart) lineChart = echarts.init(lineRef.value)
    lineChart.setOption({
      backgroundColor: 'transparent',
      textStyle: phroText,
      tooltip: { trigger: 'axis' },
      grid: { left: 48, right: 20, top: 24, bottom: 32 },
      xAxis: {
        type: 'category',
        data: trend.map((d) => d.date),
        axisLabel: phroText,
        axisLine: { lineStyle: { color: 'rgba(212,175,120,0.4)' } },
      },
      yAxis: {
        type: 'value',
        axisLabel: phroText,
        splitLine: { lineStyle: { color: 'rgba(212,175,120,0.12)' } },
      },
      series: [{
        type: 'line',
        smooth: true,
        data: trend.map((d) => d.count),
        areaStyle: { color: 'rgba(184,48,72,0.2)' },
        lineStyle: { color: '#b83048' },
        itemStyle: { color: '#c9952e' },
      }],
    })
  }

  const sceneDist = stats.value.scene_distribution || {}
  if (barRef.value) {
    if (!barChart) barChart = echarts.init(barRef.value)
    barChart.setOption({
      backgroundColor: 'transparent',
      textStyle: phroText,
      tooltip: { trigger: 'axis' },
      grid: { left: 48, right: 20, top: 24, bottom: 48 },
      xAxis: {
        type: 'category',
        data: Object.keys(sceneDist),
        axisLabel: { color: '#c4a89c', rotate: 15 },
      },
      yAxis: {
        type: 'value',
        axisLabel: phroText,
        splitLine: { lineStyle: { color: 'rgba(212,175,120,0.12)' } },
      },
      series: [{
        type: 'bar',
        data: Object.values(sceneDist),
        itemStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: '#c9952e' },
              { offset: 1, color: '#7a1028' },
            ],
          },
        },
      }],
    })
  }
}

function onResize() {
  pieChart?.resize()
  lineChart?.resize()
  barChart?.resize()
}

async function loadStats() {
  stats.value = await withApiFallback(
    () => getStatisticsApi().then((r) => r?.data || r),
    () => mockGetStatistics(),
  )
  renderCharts()
}

watch(stats, renderCharts, { deep: true })

onMounted(() => {
  loadStats()
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  pieChart?.dispose()
  lineChart?.dispose()
  barChart?.dispose()
})
</script>

<style lang="scss" scoped>
.dashboard-fill {
  display: flex;
  flex-direction: column;
  gap: $phro-module-gap;
  min-height: min-content;
}

.overview-stats {
  flex-shrink: 0;
}

.dashboard-charts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: $phro-module-gap;
}

.chart-card {
  min-height: 320px;
  display: flex;
  flex-direction: column;

  &--bar {
    min-height: 260px;
  }
}

.chart-box {
  flex: 1;
  width: 100%;
  min-height: 240px;

  &--sm {
    min-height: 200px;
  }
}

@media (max-width: 900px) {
  .dashboard-charts {
    grid-template-columns: 1fr;
  }
}
</style>
