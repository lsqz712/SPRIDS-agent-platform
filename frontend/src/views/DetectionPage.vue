<template>
  <PhroPageShell
    title="检测工作台"
    subtitle="SPRIDS · PCB SMT 缺陷自动光学检测（AOI）"
  >
    <template #actions>
      <div class="phro-tabs">
        <button
          v-for="tab in TASK_TYPES"
          :key="tab.key"
          type="button"
          class="phro-tab"
          :class="{ active: mode === tab.key }"
          @click="mode = tab.key"
        >
          {{ tab.label }}
        </button>
      </div>
    </template>

    <div class="detection-layout">
      <aside class="detection-side phro-panel-sections">
        <div class="phro-module">
          <h3 class="phro-module-title">检测场景</h3>
          <p class="scene-name">{{ scene?.display_name || 'PCB SMT 缺陷检测' }}</p>
          <div class="class-tags">
            <span
              v-for="name in scene?.class_names || defaultClasses"
              :key="name"
              class="phro-tag"
            >
              {{ classCn(name) }}
            </span>
          </div>
        </div>

        <div class="phro-module">
          <h3 class="phro-module-title">检测参数</h3>
          <DetectionParams v-model="params" />
        </div>

        <div class="phro-module phro-module--grow">
          <h3 class="phro-module-title">上传</h3>
          <div class="phro-module-body">
          <ImageUploader
            v-if="mode === 'single'"
            :disabled="loading"
            title="上传单张 PCB 图像"
            @select="handleSingle"
          />
          <ImageUploader
            v-else-if="mode === 'batch'"
            multiple
            :disabled="loading"
            title="批量上传 PCB 图像"
            hint="可多选，支持 JPG / PNG / WEBP"
            @select="handleBatch"
          />
          <ImageUploader
            v-else-if="mode === 'video'"
            accept="video/*"
            :disabled="loading"
            title="上传检测视频"
            hint="支持 MP4 / WEBM"
            @select="handleVideo"
          />
          <div v-else class="camera-panel">
            <video ref="videoRef" class="camera-video" autoplay playsinline muted />
            <canvas ref="cameraCanvasRef" class="camera-overlay" />
            <div class="camera-actions">
              <button
                type="button"
                class="phro-btn phro-btn--primary"
                :disabled="cameraRunning"
                @click="startCamera"
              >
                开启摄像头
              </button>
              <button
                type="button"
                class="phro-btn"
                :disabled="!cameraRunning"
                @click="stopCamera"
              >
                停止
              </button>
            </div>
          </div>
          <el-progress
            v-if="videoProgress > 0 && videoProgress < 100"
            :percentage="videoProgress"
            :stroke-width="8"
            class="video-progress"
          />
          </div>
        </div>
      </aside>

      <section class="detection-main">
        <div class="phro-module phro-module--grow preview-card">
          <h3 class="phro-module-title">检测结果预览</h3>
          <div class="phro-module-body">
            <BboxCanvas
              :image-src="previewImage"
              :detections="currentDetections"
              :active-index="activeDetection"
            />
          </div>
        </div>

        <div class="phro-module result-card">
          <h3 class="phro-module-title">目标列表</h3>
          <DetectionResultPanel
            :detections="currentDetections"
            :active-index="activeDetection"
            :summary="resultSummary"
            @select="activeDetection = $event"
          />
        </div>
      </section>
    </div>

    <div v-if="batchResults.length" class="phro-module batch-card">
      <h3 class="phro-module-title">批量结果概览</h3>
      <div class="batch-grid">
        <div
          v-for="(item, idx) in batchResults"
          :key="idx"
          class="batch-item"
          @click="selectBatchItem(item)"
        >
          <img :src="item.imageUrl" :alt="item.name" />
          <span>{{ item.name }}</span>
          <span class="batch-count">{{ item.detections.length }} 个缺陷</span>
        </div>
      </div>
    </div>
  </PhroPageShell>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import PhroPageShell from '@/components/layout/PhroPageShell.vue'
import ImageUploader from '@/components/detection/ImageUploader.vue'
import BboxCanvas from '@/components/detection/BboxCanvas.vue'
import DetectionParams from '@/components/detection/DetectionParams.vue'
import DetectionResultPanel from '@/components/detection/DetectionResultPanel.vue'
import { TASK_TYPES, PCB_SCENE } from '@/constants/pcbDefects'
import {
  mockDetectSingle,
  mockDetectBatch,
  mockDetectVideo,
  mockGenerateFrameDetections,
  mockGetScenes,
  withApiFallback,
} from '@/services/spridsMock'
import { getScenesApi } from '@/api/detection'

const mode = ref('single')
const loading = ref(false)
const scene = ref(PCB_SCENE)
const params = ref({ confThreshold: 0.25, iouThreshold: 0.45 })
const previewImage = ref('')
const currentDetections = ref([])
const activeDetection = ref(-1)
const resultSummary = ref(null)
const batchResults = ref([])
const videoProgress = ref(0)

const videoRef = ref(null)
const cameraCanvasRef = ref(null)
const cameraRunning = ref(false)
let cameraStream = null
let cameraTimer = null

const defaultClasses = PCB_SCENE.class_names

function classCn(name) {
  return PCB_SCENE.class_names_cn[name] || name
}

async function loadScene() {
  scene.value = await withApiFallback(
    async () => {
      const res = await getScenesApi()
      return Array.isArray(res?.data) ? res.data[0] : res?.[0]
    },
    () => mockGetScenes().then((s) => s[0]),
  )
}

function setResult(imageUrl, detections, inferenceTime = 0) {
  previewImage.value = imageUrl
  currentDetections.value = detections
  activeDetection.value = detections.length ? 0 : -1
  resultSummary.value = {
    totalObjects: detections.length,
    inferenceTime: Math.round(inferenceTime || detections.reduce((s, d) => s + (d.inference_time || 0), 0)),
  }
}

async function handleSingle(file) {
  loading.value = true
  batchResults.value = []
  try {
    const res = await mockDetectSingle(file, params.value)
    setResult(res.imageUrl, res.results, res.task?.total_inference_time)
    ElMessage.success(`检测完成，发现 ${res.results.length} 个缺陷`)
  } catch (e) {
    ElMessage.error(e.message || '检测失败')
  } finally {
    loading.value = false
  }
}

async function handleBatch(files) {
  loading.value = true
  try {
    const res = await mockDetectBatch(files, params.value)
    const grouped = {}
    res.results.forEach((r) => {
      if (!grouped[r.image_path]) {
        grouped[r.image_path] = {
          name: r.image_path,
          imageUrl: r.annotated_image_url,
          detections: [],
        }
      }
      grouped[r.image_path].detections.push(r)
    })
    batchResults.value = Object.values(grouped)
    if (batchResults.value.length) {
      selectBatchItem(batchResults.value[0])
    }
    ElMessage.success(`批量检测完成，共 ${res.results.length} 个缺陷`)
  } catch (e) {
    ElMessage.error(e.message || '批量检测失败')
  } finally {
    loading.value = false
  }
}

function selectBatchItem(item) {
  setResult(item.imageUrl, item.detections)
}

async function handleVideo(file) {
  loading.value = true
  videoProgress.value = 0
  batchResults.value = []
  try {
    const res = await mockDetectVideo(file, params.value, (p) => {
      videoProgress.value = p
    })
    videoProgress.value = 100
    currentDetections.value = res.results
    previewImage.value = ''
    resultSummary.value = {
      totalObjects: res.results.length,
      inferenceTime: res.task?.total_inference_time || 0,
    }
    ElMessage.success(`视频检测完成：${file.name}`)
  } catch (e) {
    ElMessage.error(e.message || '视频检测失败')
  } finally {
    loading.value = false
    setTimeout(() => { videoProgress.value = 0 }, 1500)
  }
}

function drawCameraOverlay() {
  const video = videoRef.value
  const canvas = cameraCanvasRef.value
  if (!video || !canvas || !cameraRunning.value) return

  const w = video.videoWidth || 640
  const h = video.videoHeight || 480
  canvas.width = w
  canvas.height = h
  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, w, h)

  const detections = mockGenerateFrameDetections(w, h, params.value)
  currentDetections.value = detections.map((d, i) => ({
    ...d,
    id: i,
    inference_time: 16,
  }))
  resultSummary.value = {
    totalObjects: detections.length,
    inferenceTime: 16,
  }

  detections.forEach((det) => {
    const [x1, y1, x2, y2] = det.bbox
    ctx.strokeStyle = det.color || '#e74c3c'
    ctx.lineWidth = 2
    ctx.strokeRect(x1, y1, x2 - x1, y2 - y1)
    const label = `${det.class_name_cn} ${(det.confidence * 100).toFixed(0)}%`
    ctx.fillStyle = det.color || '#e74c3c'
    ctx.fillRect(x1, Math.max(0, y1 - 18), ctx.measureText(label).width + 8, 18)
    ctx.fillStyle = '#fff'
    ctx.font = '12px sans-serif'
    ctx.fillText(label, x1 + 4, Math.max(12, y1 - 5))
  })
}

async function startCamera() {
  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({ video: true })
    videoRef.value.srcObject = cameraStream
    cameraRunning.value = true
    previewImage.value = ''
    cameraTimer = setInterval(drawCameraOverlay, 500)
    ElMessage.success('摄像头已开启')
  } catch {
    ElMessage.error('无法访问摄像头，请检查权限')
  }
}

function stopCamera() {
  cameraRunning.value = false
  if (cameraTimer) {
    clearInterval(cameraTimer)
    cameraTimer = null
  }
  cameraStream?.getTracks().forEach((t) => t.stop())
  cameraStream = null
  if (videoRef.value) videoRef.value.srcObject = null
  const canvas = cameraCanvasRef.value
  canvas?.getContext('2d')?.clearRect(0, 0, canvas.width, canvas.height)
}

onMounted(loadScene)
onBeforeUnmount(stopCamera)
</script>

<style lang="scss" scoped>
@use '@/assets/styles/phro-theme.scss' as phro;

.detection-layout {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(260px, 300px) 1fr;
  gap: $phro-module-gap;
}

.detection-side {
  min-height: 0;
}

.detection-main {
  min-height: 0;
  display: grid;
  grid-template-rows: 1fr minmax(160px, 220px);
  gap: $phro-module-gap;
}

.preview-card {
  min-height: 0;
}

.result-card {
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.scene-name {
  font-size: 14px;
  color: $phro-text-deep;
  margin: 0 0 10px;
}

.class-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.camera-panel {
  position: relative;
  border-radius: $phro-radius-sm;
  overflow: hidden;
  background: #000;
}

.camera-video,
.camera-overlay {
  width: 100%;
  display: block;
}

.camera-overlay {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.camera-actions {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.video-progress {
  margin-top: 12px;
}

.batch-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
}

.batch-item {
  @include phro.phro-module-box;
  padding: 8px;
  cursor: pointer;
  text-align: center;
  font-size: 12px;
  color: $phro-text-deep;
  transition: border-color 0.2s;

  &:hover {
    border-color: rgba($phro-gold, 0.55);
  }

  img {
    width: 100%;
    height: 80px;
    object-fit: cover;
    border-radius: 4px;
    margin-bottom: 6px;
  }

  .batch-count {
    display: block;
    color: $phro-gold;
    margin-top: 4px;
  }
}

@media (max-width: 960px) {
  .detection-layout {
    grid-template-columns: 1fr;
  }
}
</style>
