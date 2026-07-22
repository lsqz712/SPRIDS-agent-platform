/**
 * SPRIDS 前端演示 Mock 服务
 * 后端 API 未就绪或 dev-preview 模式下使用，数据持久化至 localStorage
 */
import { PCB_SCENE, DEFECT_COLORS } from '@/constants/pcbDefects'

const STORAGE_KEY = 'sprids_mock_data'

function loadStore() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch {
    /* ignore */
  }
  return {
    nextTaskId: 1,
    nextTrainingId: 1,
    tasks: [],
    trainingTasks: [],
    trainingMetrics: {},
  }
}

function saveStore(store) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(store))
}

function delay(ms = 600) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function randomBetween(min, max) {
  return min + Math.random() * (max - min)
}

function pickDefectClass() {
  const names = PCB_SCENE.class_names
  const className = names[Math.floor(Math.random() * names.length)]
  return {
    class_name: className,
    class_name_cn: PCB_SCENE.class_names_cn[className],
    class_id: names.indexOf(className),
    color: DEFECT_COLORS[className],
  }
}

function generateBboxes(width, height, count = null) {
  const n = count ?? Math.floor(randomBetween(1, 5))
  const boxes = []
  for (let i = 0; i < n; i++) {
    const w = width * randomBetween(0.06, 0.22)
    const h = height * randomBetween(0.06, 0.22)
    const x1 = randomBetween(0, width - w)
    const y1 = randomBetween(0, height - h)
    const defect = pickDefectClass()
    boxes.push({
      ...defect,
      confidence: Number(randomBetween(0.55, 0.98).toFixed(3)),
      bbox: [
        Math.round(x1),
        Math.round(y1),
        Math.round(x1 + w),
        Math.round(y1 + h),
      ],
    })
  }
  return boxes
}

function imageSizeFromFile(file) {
  return new Promise((resolve) => {
    const img = new Image()
    const url = URL.createObjectURL(file)
    img.onload = () => {
      resolve({ width: img.naturalWidth || 640, height: img.naturalHeight || 480 })
      URL.revokeObjectURL(url)
    }
    img.onerror = () => {
      resolve({ width: 640, height: 480 })
      URL.revokeObjectURL(url)
    }
    img.src = url
  })
}

function createTaskRecord(store, taskType, files, params) {
  const id = store.nextTaskId++
  const now = new Date().toISOString()
  const task = {
    id,
    user_id: 1,
    scene_id: PCB_SCENE.id,
    scene_name: PCB_SCENE.display_name,
    task_type: taskType,
    status: 'processing',
    total_images: files.length,
    total_objects: 0,
    total_inference_time: 0,
    conf_threshold: params.confThreshold,
    iou_threshold: params.iouThreshold,
    created_at: now,
    completed_at: null,
    results: [],
  }
  store.tasks.unshift(task)
  saveStore(store)
  return task
}

async function finalizeTask(task, results) {
  const store = loadStore()
  const idx = store.tasks.findIndex((t) => t.id === task.id)
  if (idx === -1) return task

  const totalObjects = results.length
  const totalTime = results.reduce((s, r) => s + (r.inference_time || 0), 0)

  store.tasks[idx] = {
    ...store.tasks[idx],
    status: 'completed',
    total_objects: totalObjects,
    total_inference_time: totalTime,
    completed_at: new Date().toISOString(),
    results,
  }
  saveStore(store)
  return store.tasks[idx]
}

export async function mockDetectSingle(file, params) {
  const store = loadStore()
  const task = createTaskRecord(store, 'single', [file], params)
  await delay(800)

  const { width, height } = await imageSizeFromFile(file)
  const imageUrl = URL.createObjectURL(file)
  const detections = generateBboxes(width, height).filter(
    (d) => d.confidence >= params.confThreshold,
  )

  const results = detections.map((d, i) => ({
    id: task.id * 1000 + i,
    task_id: task.id,
    image_path: file.name,
    annotated_image_url: imageUrl,
    ...d,
    inference_time: Number(randomBetween(35, 120).toFixed(1)),
    image_width: width,
    image_height: height,
    created_at: new Date().toISOString(),
  }))

  const completed = await finalizeTask(task, results)
  return {
    task: completed,
    results,
    imageUrl,
    width,
    height,
  }
}

export async function mockDetectBatch(files, params) {
  const store = loadStore()
  const task = createTaskRecord(store, 'batch', files, params)
  await delay(1200)

  const allResults = []
  for (const file of files) {
    const { width, height } = await imageSizeFromFile(file)
    const imageUrl = URL.createObjectURL(file)
    const detections = generateBboxes(width, height, Math.floor(randomBetween(0, 4))).filter(
      (d) => d.confidence >= params.confThreshold,
    )
    detections.forEach((d, i) => {
      allResults.push({
        id: task.id * 1000 + allResults.length,
        task_id: task.id,
        image_path: file.name,
        annotated_image_url: imageUrl,
        ...d,
        inference_time: Number(randomBetween(30, 100).toFixed(1)),
        image_width: width,
        image_height: height,
        created_at: new Date().toISOString(),
      })
    })
  }

  const completed = await finalizeTask(task, allResults)
  return { task: completed, results: allResults }
}

export async function mockDetectVideo(file, params, onProgress) {
  const store = loadStore()
  const task = createTaskRecord(store, 'video', [file], params)
  const steps = 20
  for (let i = 1; i <= steps; i++) {
    await delay(150)
    onProgress?.(Math.round((i / steps) * 100))
  }

  const results = Array.from({ length: 8 }, (_, i) => {
    const defect = pickDefectClass()
    return {
      id: task.id * 1000 + i,
      task_id: task.id,
      image_path: `${file.name}#frame_${i * 30}`,
      class_name: defect.class_name,
      class_name_cn: defect.class_name_cn,
      class_id: defect.class_id,
      confidence: Number(randomBetween(0.6, 0.95).toFixed(3)),
      bbox: [40, 40, 180, 140],
      inference_time: 28,
      image_width: 1280,
      image_height: 720,
      created_at: new Date().toISOString(),
    }
  }).filter((d) => d.confidence >= params.confThreshold)

  const completed = await finalizeTask(task, results)
  return { task: completed, results, videoName: file.name }
}

export function mockGenerateFrameDetections(width, height, params) {
  return generateBboxes(width, height, Math.floor(randomBetween(0, 3))).filter(
    (d) => d.confidence >= params.confThreshold,
  )
}

export async function mockGetScenes() {
  await delay(200)
  return [PCB_SCENE]
}

export async function mockGetHistory(params = {}) {
  await delay(300)
  const store = loadStore()
  let items = [...store.tasks]

  if (params.task_type) {
    items = items.filter((t) => t.task_type === params.task_type)
  }
  if (params.status) {
    items = items.filter((t) => t.status === params.status)
  }
  if (params.keyword) {
    const kw = params.keyword.toLowerCase()
    items = items.filter(
      (t) =>
        String(t.id).includes(kw) ||
        t.scene_name?.toLowerCase().includes(kw),
    )
  }

  const page = params.page || 1
  const pageSize = params.page_size || 10
  const total = items.length
  const start = (page - 1) * pageSize
  const pageItems = items.slice(start, start + pageSize)

  return {
    total,
    page,
    page_size: pageSize,
    total_pages: Math.max(1, Math.ceil(total / pageSize)),
    items: pageItems.map(({ results, ...task }) => task),
  }
}

export async function mockGetTaskDetail(taskId) {
  await delay(200)
  const store = loadStore()
  const task = store.tasks.find((t) => t.id === Number(taskId))
  if (!task) throw new Error('任务不存在')
  return {
    task: { ...task, results: undefined },
    results: task.results || [],
  }
}

export async function mockGetStatistics() {
  await delay(300)
  const store = loadStore()
  const tasks = store.tasks.filter((t) => t.status === 'completed')

  const classDistribution = {}
  PCB_SCENE.class_names.forEach((n) => {
    classDistribution[n] = 0
  })
  let totalObjects = 0
  let totalImages = 0
  let totalTime = 0

  tasks.forEach((t) => {
    totalImages += t.total_images || 0
    totalObjects += t.total_objects || 0
    totalTime += t.total_inference_time || 0
    ;(t.results || []).forEach((r) => {
      classDistribution[r.class_name] = (classDistribution[r.class_name] || 0) + 1
    })
  })

  const dailyMap = {}
  tasks.forEach((t) => {
    const day = t.created_at?.slice(0, 10) || 'unknown'
    dailyMap[day] = (dailyMap[day] || 0) + 1
  })
  const dailyTrend = Object.entries(dailyMap)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, count]) => ({ date, count }))

  if (dailyTrend.length === 0) {
    const today = new Date().toISOString().slice(0, 10)
    dailyTrend.push({ date: today, count: 0 })
  }

  return {
    total_tasks: tasks.length,
    total_images: totalImages,
    total_objects: totalObjects,
    avg_inference_time: totalObjects ? totalTime / totalObjects : 0,
    class_distribution: classDistribution,
    daily_trend: dailyTrend,
    scene_distribution: { [PCB_SCENE.display_name]: tasks.length },
  }
}

export async function mockCreateTraining(config) {
  const store = loadStore()
  const id = store.nextTrainingId++
  const task = {
    id,
    user_id: 1,
    scene_id: config.scene_id || PCB_SCENE.id,
    scene_name: PCB_SCENE.display_name,
    task_uuid: `train-${Date.now()}`,
    status: 'processing',
    model_name: config.model_name,
    epochs: config.epochs,
    current_epoch: 0,
    progress: 0,
    img_size: config.img_size,
    batch_size: config.batch_size,
    device: config.device,
    created_at: new Date().toISOString(),
    started_at: new Date().toISOString(),
    completed_at: null,
  }
  store.trainingTasks.unshift(task)
  store.trainingMetrics[id] = []
  saveStore(store)
  return task
}

export async function mockPollTraining(taskId) {
  const store = loadStore()
  const idx = store.trainingTasks.findIndex((t) => t.id === Number(taskId))
  if (idx === -1) throw new Error('训练任务不存在')

  const task = store.trainingTasks[idx]
  if (task.status !== 'processing') {
    return { task, metrics: store.trainingMetrics[taskId] || [] }
  }

  const nextEpoch = Math.min(task.current_epoch + 1, task.epochs)
  const progress = Math.round((nextEpoch / task.epochs) * 100)
  const boxLoss = Number((2.5 * Math.exp(-nextEpoch / 30) + randomBetween(0, 0.15)).toFixed(4))
  const clsLoss = Number((1.8 * Math.exp(-nextEpoch / 25) + randomBetween(0, 0.1)).toFixed(4))
  const map50 = Number(Math.min(0.92, 0.35 + nextEpoch * 0.008 + randomBetween(-0.02, 0.02)).toFixed(4))

  const metric = {
    epoch: nextEpoch,
    box_loss: boxLoss,
    cls_loss: clsLoss,
    dfl_loss: Number((1.2 * Math.exp(-nextEpoch / 28)).toFixed(4)),
    precision: Number(Math.min(0.95, map50 + 0.05).toFixed(4)),
    recall: Number(Math.min(0.93, map50).toFixed(4)),
    map50,
    map50_95: Number((map50 * 0.78).toFixed(4)),
    lr: Number((0.01 * Math.pow(0.95, nextEpoch)).toFixed(6)),
  }

  store.trainingMetrics[taskId].push(metric)
  store.trainingTasks[idx] = {
    ...task,
    current_epoch: nextEpoch,
    progress,
    status: nextEpoch >= task.epochs ? 'completed' : 'processing',
    completed_at: nextEpoch >= task.epochs ? new Date().toISOString() : null,
  }
  saveStore(store)

  return {
    task: store.trainingTasks[idx],
    metrics: store.trainingMetrics[taskId],
  }
}

export async function mockListTraining() {
  await delay(200)
  const store = loadStore()
  return store.trainingTasks
}

export async function mockGetTrainingMetrics(taskId) {
  await delay(150)
  const store = loadStore()
  return store.trainingMetrics[taskId] || []
}

export function isMockMode() {
  const token = localStorage.getItem('rsod_token')
  return token === 'dev-preview' || import.meta.env.VITE_USE_MOCK === 'true'
}

export async function withApiFallback(apiFn, mockFn) {
  if (isMockMode()) return mockFn()
  try {
    return await apiFn()
  } catch (err) {
    if (err?.response?.status === 404 || err?.code === 'ERR_NETWORK') {
      return mockFn()
    }
    throw err
  }
}
