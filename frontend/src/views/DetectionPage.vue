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

    <div class="detection-page">
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

        <!-- 非 Camera：上传区 -->
        <div v-if="mode !== 'camera'" class="phro-module phro-module--grow">
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
          <div v-if="loading" class="phro-module" style="margin-top:12px">
            <div style="display:flex;align-items:center;gap:8px;color:#e67e22">
              <span class="phro-spinner" /> 检测中...
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

        <!-- Camera：控制面板 -->
        <div v-else class="phro-module phro-module--grow">
          <h3 class="phro-module-title">摄像头控制</h3>
          <div class="camera-ctrl-panel">
            <div v-if="cameraRunning" class="camera-stats-box">
              <div class="cam-stat"><span class="cam-stat-val">{{ cameraFps }}</span><span class="cam-stat-lbl">实时 FPS</span></div>
              <div class="cam-stat"><span class="cam-stat-val">{{ camFrameCount }}</span><span class="cam-stat-lbl">已处理帧</span></div>
              <div class="cam-stat"><span class="cam-stat-val">{{ camInferenceTime }}</span><span class="cam-stat-lbl">推理耗时(ms)</span></div>
              <div class="cam-stat"><span class="cam-stat-val">{{ camObjectCount }}</span><span class="cam-stat-lbl">当前目标数</span></div>
            </div>
            <div class="cam-mode-row">
              <span class="cam-mode-label">推理模式</span>
              <el-radio-group v-model="detectMode" :disabled="cameraRunning" size="small">
                <el-radio-button label="cpu">CPU 节能</el-radio-button>
                <el-radio-button label="gpu">GPU 加速</el-radio-button>
              </el-radio-group>
            </div>
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
            <div v-if="cameraRunning" class="cam-status-tags">
              <el-tag :type="wsStatus === 'streaming' ? 'success' : 'warning'" size="small">
                {{ wsStatus === 'idle' ? '未连接' : wsStatus === 'connected' ? '模型加载中...' : wsStatus === 'streaming' ? '检测中' : wsStatus === 'timeout' ? '加载超时' : wsStatus === 'error' ? '连接失败' : wsStatus }}
              </el-tag>
              <el-tag type="success" size="small">FPS: {{ cameraFps }}</el-tag>
              <el-tag type="info" size="small">帧: {{ camFrameCount }}</el-tag>
              <el-tag type="info" size="small">推理: {{ camInferenceTime }}ms</el-tag>
            </div>
          </div>
        </div>
      </aside>

      <!-- ===== Camera 主面板 ===== -->
      <section v-if="mode === 'camera'" class="detection-main camera-layout">
        <div class="camera-preview-panel">
          <div class="camera-video-wrapper">
            <video ref="videoRef" autoplay playsinline muted class="camera-hidden-video" />
            <canvas ref="cameraCanvasRef" class="camera-canvas" />
            <div v-if="!cameraRunning" class="camera-placeholder">点击左侧按钮开启摄像头</div>
          </div>
        </div>
        <div class="camera-result-panel">
          <div class="phro-module">
            <h3 class="phro-module-title">
              当前帧目标列表
              <el-tag size="small" style="margin-left:8px">{{ camDetections.length }} 个目标</el-tag>
            </h3>
            <div v-if="camDetections.length === 0" class="cam-empty">暂无检测目标</div>
            <div v-else class="cam-det-list">
              <div v-for="(det, i) in camDetections" :key="i" class="cam-det-item">
                <div class="cam-det-name">{{ det.class_name }}</div>
                <el-progress :percentage="Math.round(det.confidence * 100)" :stroke-width="6" style="flex:1;margin:0 12px" />
                <div class="cam-det-bbox" :title="`[${det.bbox.map(v => Math.round(v)).join(', ')}]`">[{{ det.bbox.map(v => Math.round(v)).join(', ') }}]</div>
              </div>
            </div>
          </div>
          <!-- 缺陷截图 -->
          <div v-if="camSnapshots.length" class="phro-module">
            <h3 class="phro-module-title">缺陷截图 ({{ camSnapshots.length }})</h3>
            <div class="cam-snapshot-list">
              <img
                v-for="(s, i) in camSnapshots"
                :key="i"
                :src="'data:image/jpeg;base64,' + s"
                class="cam-snapshot-img"
              />
            </div>
          </div>
        </div>
      </section>

      <!-- ===== 非 Camera 主面板 ===== -->
      <section v-else class="detection-main">
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

    <!-- 批量/视频结果概览（非 Camera） -->
    <div v-if="batchResults.length && mode !== 'camera'" class="phro-module batch-card">
      <h3 class="phro-module-title">
        {{ mode === 'video' ? '视频关键帧' : '批量结果概览' }} ({{ batchResults.length }})
        <span style="font-size:11px;color:#999;font-weight:normal;margin-left:6px">点击预览</span>
      </h3>
      <div class="batch-grid-scroll">
        <div class="batch-grid">
          <div
            v-for="(item, idx) in batchResults"
            :key="idx"
            class="batch-item"
            @click="selectBatchItem(item)"
          >
            <div class="batch-thumb">
              <img v-if="item.imageUrl" :src="item.imageUrl" :alt="item.name" />
              <div v-else class="batch-no-img">📋</div>
            </div>
            <span class="batch-name">{{ item.name }}</span>
            <span class="batch-count">{{ item.detections.length }} 个缺陷</span>
          </div>
        </div>
      </div>
    </div>
    </div>
  </PhroPageShell>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage, ElTag, ElProgress } from 'element-plus'
import PhroPageShell from '@/components/layout/PhroPageShell.vue'
import ImageUploader from '@/components/detection/ImageUploader.vue'
import BboxCanvas from '@/components/detection/BboxCanvas.vue'
import DetectionParams from '@/components/detection/DetectionParams.vue'
import DetectionResultPanel from '@/components/detection/DetectionResultPanel.vue'
import { TASK_TYPES, PCB_SCENE } from '@/constants/pcbDefects'
import { getScenesApi, detectSingleApi, detectBatchApi, detectZipApi, detectVideoApi, getVideoStatusApi } from '@/api/detection'
import { createCameraWs } from '@/utils/cameraWs'

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

const defaultClasses = PCB_SCENE.class_names

function classCn(name) {
  return PCB_SCENE.class_names_cn[name] || name
}

async function loadScene() {
  try {
    const res = await getScenesApi()
    const data = Array.isArray(res?.data) ? res.data : (Array.isArray(res) ? res : [res])
    if (data.length) scene.value = data[0]
  } catch (e) { console.warn('Load scene failed, using default') }
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

// ── Single ──
async function handleSingle(file) {
  loading.value = true
  batchResults.value = []
  try {
    const fd = new FormData(); fd.append('file', file)
    fd.append('conf', params.value.confThreshold)
    fd.append('iou', params.value.iouThreshold)
    const res = await detectSingleApi(fd)
    const data = res.data || res
    const defects = data.defects || data.results || []
    const imgUrl = data.raw_image_base64
      ? 'data:image/jpeg;base64,' + data.raw_image_base64
      : (data.annotated_image_base64
        ? 'data:image/jpeg;base64,' + data.annotated_image_base64
        : URL.createObjectURL(file))
    setResult(imgUrl, defects, data.inference_time || 0)
    ElMessage.success(`检测完成，发现 ${defects.length} 个缺陷`)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || e.message || '检测失败')
  } finally {
    loading.value = false
  }
}

// ── Batch ──
async function handleBatch(files) {
  loading.value = true
  batchResults.value = []
  try {
    const isZip = files.length === 1 && files[0].name.endsWith('.zip')
    let res
    if (isZip) {
      const fd = new FormData(); fd.append('file', files[0])
      fd.append('conf', params.value.confThreshold)
      res = await detectZipApi(fd)
    } else {
      const fd = new FormData()
      files.forEach(f => fd.append('files', f))
      fd.append('conf', params.value.confThreshold)
      res = await detectBatchApi(fd)
    }
    const data = res.data || res
    const results = data.results || []
    const grouped = {}
    results.forEach((r, idx) => {
      const path = r.image_path || ''
      let basename = path.split('/').pop() || path.split('\\').pop() || `图片_${idx + 1}`
      const key = basename
      if (!grouped[key]) {
        let imgUrl = ''
        if (r.raw_image_base64) imgUrl = 'data:image/jpeg;base64,' + r.raw_image_base64
        else if (r.annotated_image_base64) imgUrl = 'data:image/jpeg;base64,' + r.annotated_image_base64
        else if (!isZip && files[idx]) imgUrl = URL.createObjectURL(files[idx])
        let shortName = basename.replace(/\.rf\.[a-f0-9]+/, '')
        grouped[key] = { name: shortName, imageUrl: imgUrl, detections: [] }
      }
      grouped[key].detections.push(...(r.defects || [r]))
    })
    batchResults.value = Object.values(grouped)
    if (batchResults.value.length) selectBatchItem(batchResults.value[0])
    const totalDefs = batchResults.value.reduce((s, b) => s + (b.detections?.length || 0), 0)
    ElMessage.success(`批量检测完成，共 ${totalDefs} 个缺陷`)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || e.message || '批量检测失败')
  } finally {
    loading.value = false
  }
}

function selectBatchItem(item) {
  setResult(item.imageUrl, item.detections)
}

// ── Video ──
async function handleVideo(file) {
  loading.value = true
  videoProgress.value = 0
  batchResults.value = []
  try {
    const fd = new FormData(); fd.append('file', file)
    fd.append('conf', params.value.confThreshold)
    const taskRes = await detectVideoApi(fd)
    const taskData = taskRes.data || taskRes
    const taskId = taskData.task_id
    if (!taskId) { ElMessage.error('视频上传失败'); loading.value = false; return }
    ElMessage.info('视频处理中...')
    let data = null
    for (let i = 0; i < 120; i++) {
      await new Promise(r => setTimeout(r, 2000))
      videoProgress.value = Math.min(90, i * 2)
      try {
        const st = await getVideoStatusApi(taskId)
        const sd = st.data || st
        if (sd.status === 'COMPLETED' || sd.status === 'completed') {
          data = sd.result || sd; break
        } else if (sd.status === 'FAILED' || sd.status === 'failed') {
          throw new Error(sd.message || '视频检测失败')
        }
      } catch(e) { if (e.message.includes('失败')) throw e }
    }
    if (!data) { ElMessage.warning('视频超时'); loading.value = false; return }
    videoProgress.value = 100
    const frames = data.key_frames || []
    let allDefects = []
    frames.forEach(f => {
      ;(f.detections || []).forEach(d => { d.frame_index = f.frame_index; d.timestamp = f.timestamp })
      allDefects.push(...(f.detections || []))
    })
    if (!allDefects.length) allDefects = data.results || []
    const kfImgs = frames.filter(f => f.annotated_image_base64)
    if (kfImgs.length) previewImage.value = 'data:image/jpeg;base64,' + kfImgs[0].annotated_image_base64
    batchResults.value = frames.map((kf, i) => ({
      name: `帧 ${kf.frame_index} (${kf.timestamp}s)`,
      imageUrl: kf.annotated_image_base64
        ? 'data:image/jpeg;base64,' + kf.annotated_image_base64 : '',
      detections: kf.detections || [],
    }))
    currentDetections.value = allDefects.slice(0, 50)
    resultSummary.value = {
      totalObjects: data.total_objects || allDefects.length,
      inferenceTime: data.total_inference_time || 0,
      processedFrames: data.processed_frames || frames.length,
    }
    ElMessage.success(`视频检测完成，${frames.length} 关键帧，${data.total_objects || allDefects.length} 个目标`)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || e.message || '视频检测失败')
  } finally {
    loading.value = false
    setTimeout(() => { videoProgress.value = 0 }, 1500)
  }
}

// ── Camera（与本地 SPRIDS-team 一致）──
const videoRef = ref(null)
const cameraCanvasRef = ref(null)
const cameraRunning = ref(false)
const detectMode = ref('cpu')
const cameraFps = ref(0)
const camFrameCount = ref(0)
const camInferenceTime = ref(0)
const camObjectCount = ref(0)
const camDetections = ref([])
const camSnapshots = ref([])
const wsStatus = ref('idle') // idle | connected | streaming | disconnected | error | timeout
let cameraWs = null
let mediaStream = null

function sendCameraFrame() {
  if (!cameraWs || !cameraWs.isConnected || !videoRef.value) return
  if (videoRef.value.readyState < 2) {
    requestAnimationFrame(sendCameraFrame)
    return
  }
  const c = document.createElement('canvas')
  c.width = 416; c.height = 416
  const ctx = c.getContext('2d')
  const vw = videoRef.value.videoWidth || 640; const vh = videoRef.value.videoHeight || 480
  const s = Math.min(416 / vw, 416 / vh)
  ctx.drawImage(videoRef.value, (416 - vw * s) / 2, (416 - vh * s) / 2, vw * s, vh * s)
  cameraWs.sendFrame(c.toDataURL('image/jpeg', 0.6).split(',')[1])
}

async function startCamera() {
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' }, audio: false })
    videoRef.value.srcObject = mediaStream
    await videoRef.value.play()
    // 等待视频解码出第一帧后再建连，确保 sendCameraFrame 能抓到画面
    if (videoRef.value.readyState < 2) {
      await new Promise((resolve) => { videoRef.value.oncanplay = resolve })
    }
    cameraRunning.value = true
    cameraWs = createCameraWs({
      mode: detectMode.value, conf: params.value.confThreshold, iou: params.value.iouThreshold,
      onResult: (d) => {
        // 隐藏原始视频，只显示标注画面
        if (videoRef.value) videoRef.value.style.display = 'none'
        // 实时标注画面画在 camera canvas 上
        const img = new Image()
        img.onload = () => {
          const canvas = cameraCanvasRef.value
          if (!canvas) return
          canvas.width = img.width; canvas.height = img.height
          canvas.getContext('2d').drawImage(img, 0, 0)
          // 响应驱动：收到结果后才发下一帧
          requestAnimationFrame(sendCameraFrame)
        }
        img.src = 'data:image/jpeg;base64,' + d.annotatedFrame
        // 更新统计
        cameraFps.value = d.fps
        camFrameCount.value = d.frameCount
        camInferenceTime.value = d.inferenceTime
        camObjectCount.value = d.objectCount
        camDetections.value = d.detections || []
        // 收集缺陷截图
        if (d.objectCount > 0 && camSnapshots.value.length < 10) {
          camSnapshots.value.push(d.annotatedFrame)
        }
      },
      onStatusChange: (s) => { wsStatus.value = s },
      onConfigOk: () => { requestAnimationFrame(sendCameraFrame) },
      onError: (m) => { ElMessage.error(m); wsStatus.value = 'error' },
      onClose: () => {},
    })
    cameraWs.connect()
    ElMessage.success('摄像头已开启')
  } catch (e) {
    ElMessage.error('摄像头失败: ' + (e.message || '请检查权限'))
    stopCamera()
  }
}

function stopCamera() {
  if (cameraWs) { cameraWs.close(); cameraWs = null }
  if (mediaStream) { mediaStream.getTracks().forEach(t => t.stop()); mediaStream = null }
  cameraRunning.value = false
  wsStatus.value = 'idle'
  cameraFps.value = 0
  camFrameCount.value = 0
  camInferenceTime.value = 0
  camObjectCount.value = 0
  camDetections.value = []
  camSnapshots.value = []
  if (cameraCanvasRef.value) {
    const ctx = cameraCanvasRef.value.getContext('2d')
    ctx.clearRect(0, 0, cameraCanvasRef.value.width, cameraCanvasRef.value.height)
  }
}

onMounted(loadScene)
onBeforeUnmount(() => { stopCamera() })
</script>

<style lang="scss" scoped>
@use '@/assets/styles/phro-theme.scss' as phro;

/* 整页填满窗口：预览吃掉剩余高度，批量条固定底部，杜绝预览被压成细条 */
.detection-page {
  flex: 1;
  min-height: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: $phro-module-gap;
  overflow: hidden;
}

.detection-layout {
  flex: 1 1 0;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(220px, 280px) minmax(0, 1fr);
  gap: $phro-module-gap;
  overflow: hidden;
}

.detection-side {
  min-height: 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow-x: hidden;
  overflow-y: auto;
}

.detection-main {
  min-height: 0;
  min-width: 0;
  height: 100%;
  display: grid;
  grid-template-rows: minmax(0, 1fr) 168px;
  gap: $phro-module-gap;
  overflow: hidden;
}

.preview-card {
  min-height: 0;
  height: 100%;
  display: flex !important;
  flex-direction: column;
  overflow: hidden;

  .phro-module-body {
    flex: 1 1 0;
    min-height: 0;
    height: auto;
    overflow: hidden;
  }

  :deep(.bbox-canvas-wrap) {
    flex: 1 1 0;
    width: 100%;
    height: 100%;
    min-height: 0;
  }
}

.result-card {
  min-height: 0;
  min-width: 0;
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.batch-card {
  flex: 0 0 auto;
  flex-shrink: 0;
  min-width: 0;
  width: 100%;
  max-height: 220px;
  display: flex;
  flex-direction: column;
  overflow: hidden;

  .phro-module-title {
    flex-shrink: 0;
  }
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

// ── Camera 控制面板（左侧边栏）──
.camera-ctrl-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.camera-stats-box {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.cam-stat {
  text-align: center;
  padding: 8px 4px;
  background: rgba($phro-gold, 0.08);
  border-radius: $phro-radius-sm;
}

.cam-stat-val {
  display: block;
  font-size: 20px;
  font-weight: 700;
  color: $phro-gold;
}

.cam-stat-lbl {
  display: block;
  font-size: 10px;
  color: $phro-text-mid;
  margin-top: 2px;
}

.cam-mode-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;

  :deep(.el-radio-button__inner) {
    background: transparent;
    border-color: rgba($phro-gold, 0.3);
    color: $phro-text-mid;
  }

  :deep(.el-radio-button.is-active .el-radio-button__inner) {
    background: rgba($phro-gold, 0.2);
    border-color: $phro-gold;
    color: $phro-gold;
    box-shadow: none;
  }

  :deep(.el-radio-button:hover:not(.is-disabled) .el-radio-button__inner) {
    color: $phro-gold;
    border-color: rgba($phro-gold, 0.5);
  }
}

.cam-mode-label {
  font-size: 12px;
  color: $phro-text-mid;
  white-space: nowrap;
}

.camera-actions {
  display: flex;
  gap: 8px;
}

.cam-status-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

// ── Camera 主面板（右侧）──
.camera-layout {
  display: flex !important;
  gap: $phro-module-gap;
  grid-template-rows: none !important;
}

.camera-preview-panel {
  flex: 3;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.camera-video-wrapper {
  position: relative;
  flex: 1;
  background: #000;
  border-radius: $phro-radius-sm;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}

.camera-hidden-video {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
  pointer-events: none;
}

.camera-canvas {
  width: 100%;
  height: auto;
  display: block;
}

.camera-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
  font-size: 16px;
}

.camera-result-panel {
  flex: 2;
  display: flex;
  flex-direction: column;
  gap: $phro-module-gap;
  overflow-y: auto;
}

.cam-empty {
  text-align: center;
  color: $phro-text-mid;
  padding: 20px;
  font-size: 13px;
}

// 统一 Element Plus tag 与 Phro 主题色
.camera-result-panel {
  :deep(.el-tag) {
    background: rgba($phro-gold, 0.12);
    border-color: rgba($phro-gold, 0.25);
    color: $phro-gold;
  }

  :deep(.el-tag--success) {
    background: rgba($phro-gold, 0.15);
    border-color: rgba($phro-gold, 0.3);
    color: $phro-gold;
  }

  :deep(.el-tag--info) {
    background: rgba($phro-text-mid, 0.1);
    border-color: rgba($phro-text-mid, 0.2);
    color: $phro-text-mid;
  }
}

.cam-status-tags {
  :deep(.el-tag) {
    background: rgba($phro-gold, 0.12);
    border-color: rgba($phro-gold, 0.25);
    color: $phro-gold;
  }
}

.cam-det-list {
  max-height: 280px;
  overflow-y: auto;
}

.cam-det-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  border-bottom: 1px solid rgba($phro-rose, 0.08);
  min-width: 0;
}

.cam-det-item:last-child {
  border-bottom: none;
}

.cam-det-name {
  font-weight: 600;
  min-width: 72px;
  max-width: 100px;
  font-size: 12px;
  color: $phro-text-deep;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex-shrink: 0;
}

.cam-det-bbox {
  font-size: 11px;
  color: $phro-text-mid;
  font-family: monospace;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
  flex: 0 1 auto;
  max-width: 40%;
}

.cam-snapshot-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.cam-snapshot-img {
  width: 100%;
  border-radius: $phro-radius-sm;
  border: 1px solid rgba($phro-gold, 0.2);
}

// ── 非 Camera 样式 ──
.video-progress {
  margin-top: 12px;
}

.batch-grid {
  display: flex;
  flex-wrap: nowrap;
  gap: 12px;
  width: max-content;
  min-width: 100%;
}

.batch-grid-scroll {
  flex: 1 1 auto;
  min-width: 0;
  width: 100%;
  overflow-x: scroll;
  overflow-y: hidden;
  padding-bottom: 6px;
  /* Firefox */
  scrollbar-width: thin;
  scrollbar-color: rgba($phro-gold, 0.55) rgba($phro-rose, 0.12);

  /* Chromium / Safari：始终显示可拖动的横向滑动条 */
  &::-webkit-scrollbar {
    height: 10px;
  }

  &::-webkit-scrollbar-track {
    background: rgba($phro-rose, 0.12);
    border-radius: 5px;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba($phro-gold, 0.55);
    border-radius: 5px;
    border: 2px solid transparent;
    background-clip: padding-box;

    &:hover {
      background: rgba($phro-gold, 0.75);
      background-clip: padding-box;
    }
  }
}

.batch-item {
  @include phro.phro-module-box;
  flex: 0 0 132px;
  width: 132px;
  padding: 8px;
  cursor: pointer;
  text-align: center;
  font-size: 12px;
  color: $phro-text-deep;
  transition: border-color 0.2s;

  .batch-thumb {
    width: 100%;
    height: 88px;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    border-radius: 4px;
    margin-bottom: 4px;
    background: var(--phro-panel-bg, #f5f5f5);

    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
  }

  .batch-no-img {
    font-size: 32px;
    opacity: 0.3;
  }

  .batch-name {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &:hover {
    border-color: rgba($phro-gold, 0.55);
  }

  .batch-count {
    display: block;
    color: $phro-gold;
    margin-top: 4px;
  }
}

@media (max-width: 960px) {
  .detection-page {
    overflow-y: auto;
  }

  .detection-layout {
    grid-template-columns: 1fr;
    flex: 1 1 auto;
    min-height: 520px;
    overflow: visible;
  }

  .detection-main {
    grid-template-rows: minmax(320px, 55vh) 168px;
    height: auto;
    overflow: visible;
  }

  .preview-card {
    min-height: 320px;
  }

  .batch-card {
    max-height: none;
  }

  .camera-layout {
    flex-direction: column !important;
  }
}

@media (max-height: 700px) {
  .detection-main {
    grid-template-rows: minmax(0, 1fr) 140px;
  }

  .batch-card {
    max-height: 150px;
  }

  .batch-item {
    flex-basis: 120px;
    width: 120px;

    .batch-thumb {
      height: 72px;
    }
  }
}
</style>
