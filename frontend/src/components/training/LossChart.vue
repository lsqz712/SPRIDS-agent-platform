<template>
  <div ref="chartRef" class="loss-chart" />
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  metrics: { type: Array, default: () => [] },
})

const chartRef = ref(null)
let chart = null

function buildOption(metrics) {
  const epochs = metrics.map((m) => m.epoch)
  return {
    backgroundColor: 'transparent',
    textStyle: { color: '#d4bca8', fontFamily: 'Noto Sans SC, sans-serif' },
    tooltip: { trigger: 'axis' },
    legend: {
      data: ['box_loss', 'cls_loss', 'mAP50'],
      textStyle: { color: '#d4bca8' },
      bottom: 0,
    },
    grid: { left: 48, right: 20, top: 24, bottom: 48 },
    xAxis: {
      type: 'category',
      data: epochs,
      name: 'Epoch',
      axisLine: { lineStyle: { color: 'rgba(212,175,120,0.4)' } },
      axisLabel: { color: '#c4a89c' },
    },
    yAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: 'rgba(212,175,120,0.4)' } },
      splitLine: { lineStyle: { color: 'rgba(212,175,120,0.12)' } },
      axisLabel: { color: '#c4a89c' },
    },
    series: [
      {
        name: 'box_loss',
        type: 'line',
        smooth: true,
        data: metrics.map((m) => m.box_loss),
        lineStyle: { color: '#b83048' },
        itemStyle: { color: '#b83048' },
      },
      {
        name: 'cls_loss',
        type: 'line',
        smooth: true,
        data: metrics.map((m) => m.cls_loss),
        lineStyle: { color: '#c9952e' },
        itemStyle: { color: '#c9952e' },
      },
      {
        name: 'mAP50',
        type: 'line',
        smooth: true,
        data: metrics.map((m) => m.map50),
        lineStyle: { color: '#1abc9c' },
        itemStyle: { color: '#1abc9c' },
      },
    ],
  }
}

function render() {
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)
  chart.setOption(buildOption(props.metrics), true)
}

watch(() => props.metrics, render, { deep: true })

onMounted(() => {
  render()
  window.addEventListener('resize', render)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', render)
  chart?.dispose()
})
</script>

<style scoped>
.loss-chart {
  flex: 1;
  width: 100%;
  min-height: 200px;
}
</style>
