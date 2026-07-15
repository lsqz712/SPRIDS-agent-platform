<template>
  <div class="detection-page">
    <div class="page-header">
      <h2>检测工作台</h2>
      <el-radio-group v-model="mode" size="default">
        <el-radio-button value="single">单图</el-radio-button>
        <el-radio-button value="batch">批量</el-radio-button>
        <el-radio-button value="video">视频</el-radio-button>
        <el-radio-button value="camera">摄像头</el-radio-button>
      </el-radio-group>
    </div>

    <!-- ========== 图片/视频上传区域（非 Camera 模式）========== -->
    <el-card v-if="mode !== 'camera'" shadow="never" style="margin-bottom:16px">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span>上传</span>
          <el-button v-if="mode==='batch'" size="small" @click="uploadFolder">上传文件夹</el-button>
        </div>
      </template>
      <input ref="folderInputRef" type="file" webkitdirectory multiple style="position:absolute;opacity:0;width:0;height:0" @change="handleFolder" />
      <el-upload
        drag
        :auto-upload="false"
        :on-change="handleFile"
        :multiple="mode === 'batch'"
        :accept="mode === 'video' ? 'video/*' : mode === 'batch' ? 'image/*,.zip' : 'image/*'"
      >
        <el-icon style="font-size:48px;color:#c0c4cc"><UploadFilled /></el-icon>
        <div style="margin-top:8px">拖拽或 <em>点击上传</em> {{ mode }} 文件</div>
      </el-upload>
      <div v-if="mode === 'batch' && batchFiles.length" style="margin-top:8px">
        <el-tag v-for="(f,i) in batchFiles" :key="i" closable @close="batchFiles.splice(i,1)" style="margin:4px">{{ f.name }}</el-tag>
      </div>
      <div v-else-if="currentFile" style="margin-top:8px">
        <el-tag closable @close="currentFile=null">{{ currentFile.name }}</el-tag>
      </div>
      <el-divider />
      <div class="param-row"><span>置信度</span><el-slider v-model="conf" :min="0.05" :max="0.95" :step="0.05" show-input /></div>
      <el-button type="primary" style="width:100%;margin-top:8px" @click="runDetect" :loading="detecting" :disabled="!currentFile && !batchFiles.length">
        {{ mode === 'video' ? '上传并检测' : '开始检测' }}
      </el-button>
    </el-card>

    <!-- ========== Camera 模式 ========== -->
    <template v-if="mode === 'camera'">
      <div class="main-content">
        <div class="preview-panel">
          <div class="video-wrapper">
            <video ref="videoRef" autoplay playsinline muted style="display:none"></video>
            <canvas ref="canvasRef" class="preview-canvas" :width="canvasWidth" :height="canvasHeight"></canvas>
            <div v-if="!cameraOn" class="placeholder"><p>点击下方按钮开启摄像头</p></div>
          </div>
          <div v-if="cameraOn" class="video-stats">
            <el-tag type="success">FPS: {{ cameraFps }}</el-tag>
            <el-tag type="info">帧: {{ camFrameCount }}</el-tag>
            <el-tag type="info">推理: {{ camInferenceTime }}ms</el-tag>
          </div>
        </div>
        <div class="result-panel">
          <el-card class="stats-card" shadow="never">
            <template #header><span>实时检测统计</span></template>
            <div class="stats-grid">
              <div class="stat-item"><div class="stat-value">{{ camObjectCount }}</div><div class="stat-label">当前目标数</div></div>
              <div class="stat-item"><div class="stat-value">{{ cameraFps }}</div><div class="stat-label">实时 FPS</div></div>
              <div class="stat-item"><div class="stat-value">{{ camInferenceTime }}</div><div class="stat-label">推理耗时(ms)</div></div>
              <div class="stat-item"><div class="stat-value">{{ camFrameCount }}</div><div class="stat-label">已处理帧</div></div>
            </div>
          </el-card>
          <el-card class="detections-card" shadow="never">
            <template #header><div class="card-header"><span>当前帧目标列表</span><el-tag size="small">{{ camDetections.length }} 个目标</el-tag></div></template>
            <div v-if="camDetections.length === 0" class="empty-state">暂无检测目标</div>
            <div v-else class="detection-list">
              <div v-for="(det,i) in camDetections" :key="i" class="detection-item">
                <div class="det-info"><span class="det-class">{{ det.class_name }}</span><el-progress :percentage="Math.round(det.confidence*100)" :stroke-width="6" style="width:120px" /></div>
                <div class="det-bbox">[{{ det.bbox.map(v=>Math.round(v)).join(', ') }}]</div>
              </div>
            </div>
          </el-card>
          <!-- 缺陷截图（多张） -->
          <el-card v-if="camSnapshots.length" class="snapshot-card" shadow="never">
            <template #header><span>缺陷截图 ({{ camSnapshots.length }})</span><el-tag size="small" type="danger" v-if="camObjectCount>0">{{ camObjectCount }} 处缺陷</el-tag></template>
            <div style="display:flex;flex-direction:column;gap:8px">
              <img v-for="(s,i) in camSnapshots" :key="i" :src="'data:image/jpeg;base64,'+s" style="width:100%;border-radius:6px;border:1px solid #e0e0e0" />
            </div>
          </el-card>
        </div>
      </div>
      <div class="control-bar">
        <el-button v-if="!cameraOn" type="primary" size="large" @click="startCamera" :loading="isConnecting">开启摄像头</el-button>
        <el-button v-else type="danger" size="large" @click="stopCamera">停止检测</el-button>
        <el-divider direction="vertical" />
        <span class="control-label">推理模式：</span>
        <el-radio-group v-model="detectMode" :disabled="cameraOn">
          <el-radio-button label="cpu">CPU 节能</el-radio-button>
          <el-radio-button label="gpu">GPU 加速</el-radio-button>
        </el-radio-group>
        <el-divider direction="vertical" />
        <span class="control-label">置信度：</span>
        <el-slider v-model="confThreshold" :min="0.1" :max="0.9" :step="0.05" :disabled="cameraOn" style="width:150px" show-input />
      </div>
    </template>

    <!-- ========== 检测结果（非 Camera）========== -->
    <el-card v-if="result && mode !== 'camera'" shadow="never" style="margin-bottom:16px">
      <template #header>
        <span>结果</span>
        <el-tag type="success" style="margin-left:8px">{{ result.total_objects || 0 }} 目标</el-tag>
        <el-tag type="info" style="margin-left:4px" v-if="result.total_inference_time || result.inference_time">{{ (result.total_inference_time||result.inference_time||0).toFixed(0) }}ms</el-tag>
      </template>
      <!-- 类别标签 -->
      <div v-if="result.class_counts && Object.keys(result.class_counts).length" style="margin-bottom:12px;display:flex;gap:6px;flex-wrap:wrap">
        <el-tag v-for="(cnt,name) in result.class_counts" :key="name" type="warning">{{ name }}: {{ cnt }}</el-tag>
      </div>
      <!-- 单图标注图 -->
      <img v-if="annotatedSrc && !result.annotated_images && !result.key_frames?.length" :src="annotatedSrc" style="max-width:100%;max-height:400px;border-radius:8px;margin-bottom:12px" />
      <!-- 批量标注图 -->
      <div v-if="result.annotated_images?.length" class="annotated-gallery" style="display:flex;flex-wrap:wrap;gap:12px;margin-bottom:12px">
        <div v-for="(img,i) in result.annotated_images" :key="i" style="width:200px">
          <img :src="'data:image/jpeg;base64,'+img.annotated_image_base64" style="width:100%;border-radius:6px" />
          <div style="font-size:11px;color:#909399;text-align:center">{{ (img.image_path||'').split(/[\\/]/).pop() }}</div>
        </div>
      </div>
      <!-- 摄像头截图 -->
      <div v-if="result.snapshot_frames?.length" style="margin-bottom:12px">
        <div style="font-weight:600;margin-bottom:8px">缺陷截图 ({{ result.snapshot_frames.length }})</div>
        <div style="display:flex;flex-wrap:wrap;gap:8px">
          <img v-for="(s,i) in result.snapshot_frames" :key="i" :src="'data:image/jpeg;base64,'+s" style="width:160px;border-radius:6px;border:1px solid #e0e0e0" />
        </div>
      </div>
      <!-- 视频关键帧 -->
      <div v-if="result.key_frames?.length && !result.snapshot_frames?.length" style="margin-bottom:12px">
        <div style="font-weight:600;margin-bottom:8px">关键帧 ({{ result.key_frames.length }})</div>
        <div style="display:flex;flex-wrap:wrap;gap:12px">
          <div v-for="(kf,i) in result.key_frames.filter(k=>k.annotated_image_base64)" :key="i" style="width:200px">
            <img :src="'data:image/jpeg;base64,'+kf.annotated_image_base64" style="width:100%;border-radius:6px" />
            <div style="font-size:11px;color:#909399;text-align:center">帧_{{ kf.frame_index }} ({{ kf.object_count }} obj)</div>
          </div>
        </div>
      </div>
      <!-- 检测列表 -->
      <el-table :data="detectionsFlat" stripe size="small" max-height="300">
        <el-table-column label="图片" width="160">
          <template #default="{row}">{{ (row.image_path || result.filename || '').split(/[\\/]/).pop() || '-' }}</template>
        </el-table-column>
        <el-table-column prop="class_name" label="类别" width="140" />
        <el-table-column label="置信度" width="100">
          <template #default="{row}">{{ (row.confidence*100).toFixed(1) }}%</template>
        </el-table-column>
        <el-table-column label="BBox">
          <template #default="{row}">{{ row.bbox?.map(Math.round).join(', ') }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- ========== 历史记录 ========== -->
    <el-card v-if="history.length" shadow="never">
      <template #header>
        <div style="display:flex;justify-content:space-between"><span>检测历史</span><el-button text @click="fetchHistory">刷新</el-button></div>
      </template>
      <el-table :data="history" stripe size="small" @row-click="goDetail">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="task_type" label="类型" width="70" />
        <el-table-column prop="total_objects" label="目标数" width="80" />
        <el-table-column label="类别">
          <template #default="{row}">{{ row.class_names?.join(', ') }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="170" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { detectSingle, detectBatch, detectZip, detectVideo, getVideoStatus, listDetections } from '@/api/detection'
import { createCameraWs } from '@/utils/cameraWs'
import request from '@/utils/request'

// ── 模式 ──
const mode = ref('single')
const conf = ref(0.25)

// ── 上传 ──
const currentFile = ref(null)
const batchFiles = ref([])
const folderInputRef = ref(null)
const detecting = ref(false)
const result = ref(null)
const annotatedSrc = ref(null)
const history = ref([])

const detectionsFlat = computed(() => {
  const r = result.value
  if (!r) return []
  if (r.detections) return r.detections
  if (r.objects) return r.objects
  if (r.frames) return r.frames.flatMap(f => f.objects || [])
  return []
})

// ── Camera ──
const videoRef = ref(null)
const canvasRef = ref(null)
const cameraOn = ref(false)
const isConnecting = ref(false)
const detectMode = ref('cpu')
const confThreshold = ref(0.25)
const cameraFps = ref(0)
const camFrameCount = ref(0)
const camInferenceTime = ref(0)
const camObjectCount = ref(0)
const camDetections = ref([])
const camSnapshots = ref([])
const canvasWidth = ref(640)
const canvasHeight = ref(480)
let cameraWs = null
let mediaStream = null

onMounted(() => { fetchHistory() })
onBeforeUnmount(() => { stopCamera() })

// ── 文件处理 ──
function handleFile(f) {
  if (mode.value === 'batch') { batchFiles.value.push(f.raw) }
  else { currentFile.value = f.raw }
}
async function uploadFolder() {
  try {
    // 优先使用现代 showDirectoryPicker API
    const dirHandle = await window.showDirectoryPicker()
    const files = []
    async function collect(handle, prefix = '') {
      for await (const [name, entry] of handle.entries()) {
        if (entry.kind === 'file') {
          const file = await entry.getFile()
          file._folderPath = prefix + name
          files.push(file)
        } else if (entry.kind === 'directory') {
          await collect(entry, prefix + name + '/')
        }
      }
    }
    await collect(dirHandle)
    if (!files.length) { ElMessage.warning('文件夹中无文件'); return }
    batchFiles.value.push(...files)
    ElMessage.success(`已添加 ${files.length} 个文件（检测时自动过滤非图片）`)
  } catch (e) {
    // 降级：webkitdirectory
    if (e.name === 'AbortError') return
    folderInputRef.value?.click()
  }
}
function handleFolder(e) {
  const files = Array.from(e.target.files || [])
  e.target.value = ''
  files.forEach(f => { f._folderPath = f.webkitRelativePath || f.name })
  if (!files.length) { ElMessage.warning('文件夹为空'); return }
  batchFiles.value.push(...files)
  ElMessage.success(`已添加 ${files.length} 个文件`)
}

// ── 检测 ──
async function runDetect() {
  if (!currentFile.value && !batchFiles.value.length) return

  // 文件类型校验
  const imageExts = ['.jpg','.jpeg','.png','.bmp','.webp']
  const videoExts = ['.mp4','.avi','.mov','.mkv','.wmv','.flv']
  if (mode.value === 'single') {
    const ext = '.' + currentFile.value.name.split('.').pop()?.toLowerCase()
    if (!imageExts.includes(ext)) { ElMessage.error('单图检测仅支持图片格式: '+imageExts.join(', ')); return }
  } else if (mode.value === 'batch') {
    // 自动过滤非图片文件
    const imageExtsLower = ['.jpg','.jpeg','.png','.bmp','.webp','.tif','.tiff']
    const valid = batchFiles.value.filter(f => {
      const name = f._folderPath || f.name || ''
      const baseName = name.split('/').pop()  // 取文件名部分
      const ext = '.' + (baseName.includes('.') ? baseName.split('.').pop() : '').toLowerCase()
      return imageExtsLower.includes(ext) || ext === '.zip'
    })
    const skipped = batchFiles.value.length - valid.length
    if (!valid.length) {
      const names = batchFiles.value.map(f => f.name).join(', ')
      ElMessage.error(`没有有效的图片文件。文件列表: ${names}`)
      return
    }
    batchFiles.value = valid
    if (skipped > 0) ElMessage.warning(`已跳过 ${skipped} 个非图片文件`)
  } else if (mode.value === 'video') {
    const ext = '.' + currentFile.value.name.split('.').pop()?.toLowerCase()
    if (!videoExts.includes(ext)) { ElMessage.error('视频检测仅支持: '+videoExts.join(', ')); return }
  }

  detecting.value = true; result.value = null; annotatedSrc.value = null
  try {
    let res
    if (mode.value === 'single') {
      const fd = new FormData(); fd.append('file', currentFile.value); fd.append('conf', conf.value)
      res = await detectSingle(fd)
    } else if (mode.value === 'batch') {
      const isZip = batchFiles.value.length === 1 && batchFiles.value[0].name.endsWith('.zip')
      if (isZip) {
        const fd = new FormData(); fd.append('file', batchFiles.value[0]); fd.append('conf', conf.value)
        res = await detectZip(fd)
      } else {
        const fd = new FormData(); batchFiles.value.forEach(f => fd.append('files', f)); fd.append('conf', conf.value)
        res = await detectBatch(fd)
      }
    } else if (mode.value === 'video') {
      const fd = new FormData(); fd.append('file', currentFile.value); fd.append('conf', conf.value)
      const taskRes = await detectVideo(fd)
      const taskId = taskRes.task_id
      if (taskId) {
        ElMessage.info('视频处理中...')
        for (let i = 0; i < 120; i++) {
          await new Promise(r => setTimeout(r, 2000))
          try {
            const st = await getVideoStatus(taskId)
            if (st.status === 'completed') {
              res = st.result || {}
              break
            } else if (st.status === 'failed') {
              ElMessage.error(st.message || '视频检测失败')
              detecting.value = false; return
            }
          } catch (e) { /* continue polling */ }
        }
        if (!res) { ElMessage.warning('视频超时'); detecting.value = false; return }
      } else {
        res = taskRes
      }
    }
    const data = res.data || res
    result.value = data
    if (data.annotated_image_base64 && !data.annotated_images) annotatedSrc.value = 'data:image/jpeg;base64,' + data.annotated_image_base64
    ElMessage.success((data.total_objects || 0) + ' 个目标')
    fetchHistory()
  } catch (e) { ElMessage.error('检测失败: ' + (e.message || e)) }
  finally { detecting.value = false }
}

// ── 历史 ──
async function fetchHistory() {
  try { const res = await listDetections(); history.value = res.items || [] } catch (e) { console.error(e) }
}
async function goDetail(row) {
  try {
    const res = await request.get('/detection/detail/' + row.id)
    const data = { ...row, detections: res.results, key_frames: res.key_frames, snapshot_frames: res.snapshot_frames, total_objects: row.total_objects, class_counts: {} }
    ;(res.results||[]).forEach(r => { data.class_counts[r.class_name] = (data.class_counts[r.class_name]||0)+1 })
    result.value = data; annotatedSrc.value = null
    ElMessage.success('已加载 #' + row.id)
  } catch (e) { ElMessage.error('加载失败') }
}

// ── Camera ──
async function startCamera() {
  try {
    isConnecting.value = true
    mediaStream = await navigator.mediaDevices.getUserMedia({ video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' }, audio: false })
    videoRef.value.srcObject = mediaStream; await videoRef.value.play()
    canvasWidth.value = videoRef.value.videoWidth || 640; canvasHeight.value = videoRef.value.videoHeight || 480
    cameraWs = createCameraWs({
      mode: detectMode.value, conf: confThreshold.value,
      onResult: (d) => {
        const img = new Image()
        img.onload = () => { const ctx = canvasRef.value.getContext('2d'); canvasRef.value.width = img.width; canvasRef.value.height = img.height; ctx.drawImage(img,0,0); requestAnimationFrame(sendFrame) }
        img.src = 'data:image/jpeg;base64,' + d.annotatedFrame
        cameraFps.value = d.fps; camFrameCount.value = d.frameCount; camInferenceTime.value = d.inferenceTime
        camObjectCount.value = d.objectCount; camDetections.value = d.detections
        if (d.objectCount > 0 && camSnapshots.value.length < 10) camSnapshots.value.push(d.annotatedFrame)
      },
      onConfigOk: () => { requestAnimationFrame(sendFrame) },
      onError: (m) => { ElMessage.error(m); isConnecting.value = false },
      onClose: (data) => { isConnecting.value = false; if (data?.task_id) fetchHistory() },
    })
    cameraWs.connect()
    cameraOn.value = true; ElMessage.success('摄像头已开启')
  } catch (e) { ElMessage.error('摄像头失败: ' + e.message); stopCamera() }
}
function sendFrame() {
  if (!cameraWs || !cameraWs.isConnected || !videoRef.value || videoRef.value.readyState < 2) return
  const t = detectMode.value === 'cpu' ? 416 : 640
  const c = document.createElement('canvas'); c.width = t; c.height = t
  const ctx = c.getContext('2d')
  const vw = videoRef.value.videoWidth; const vh = videoRef.value.videoHeight
  const s = Math.min(t/vw, t/vh)
  ctx.drawImage(videoRef.value, (t-vw*s)/2, (t-vh*s)/2, vw*s, vh*s)
  cameraWs.sendFrame(c.toDataURL('image/jpeg',0.6).split(',')[1])
}
function stopCamera() {
  if (cameraWs) { cameraWs.close(); cameraWs = null }
  if (mediaStream) { mediaStream.getTracks().forEach(t=>t.stop()); mediaStream = null }
  cameraOn.value = false; isConnecting.value = false
  cameraFps.value = 0; camFrameCount.value = 0; camInferenceTime.value = 0; camObjectCount.value = 0; camDetections.value = []
  camSnapshots.value = []
  if (canvasRef.value) { const ctx = canvasRef.value.getContext('2d'); ctx.clearRect(0,0,canvasRef.value.width,canvasRef.value.height) }
}
</script>

<style lang="scss" scoped>
.detection-page { padding:24px; }
.page-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; }
.page-header h2 { margin:0; font-size:20px; }
.param-row { display:flex; align-items:center; gap:12px; margin-bottom:4px; }
.param-row span { width:90px; flex-shrink:0; font-size:13px; color:#606266; }
.param-row .el-slider { flex:1; }
.main-content { display:flex; gap:20px; flex:1; overflow:hidden; }
.preview-panel { flex:3; display:flex; flex-direction:column; gap:12px; }
.video-wrapper { position:relative; background:#000; border-radius:8px; overflow:hidden; min-height:400px; display:flex; align-items:center; justify-content:center; }
.preview-canvas { width:100%; height:auto; display:block; }
.placeholder { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; color:#999; font-size:16px; }
.video-stats { display:flex; gap:8px; }
.result-panel { flex:2; display:flex; flex-direction:column; gap:12px; overflow-y:auto; }
.stats-grid { display:grid; grid-template-columns:repeat(2,1fr); gap:12px; }
.stat-item { text-align:center; padding:12px; background:#f9f9f9; border-radius:8px; }
.stat-value { font-size:24px; font-weight:700; color:#409eff; }
.stat-label { font-size:12px; color:#999; margin-top:4px; }
.card-header { display:flex; align-items:center; justify-content:space-between; }
.empty-state { text-align:center; color:#999; padding:20px; }
.detection-list { max-height:300px; overflow-y:auto; }
.detection-item { display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid #f0f0f0; }
.detection-item:last-child { border-bottom:none; }
.det-info { display:flex; align-items:center; gap:12px; }
.det-class { font-weight:600; min-width:80px; }
.det-bbox { font-size:12px; color:#999; font-family:monospace; }
.control-bar { display:flex; align-items:center; gap:16px; padding:16px 0; border-top:1px solid #e0e0e0; margin-top:16px; }
.control-label { font-size:14px; color:#666; white-space:nowrap; }
</style>
