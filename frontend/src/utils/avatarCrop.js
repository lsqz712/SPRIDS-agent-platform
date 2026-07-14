const CROP_VIEWPORT_SIZE = 280
const CROP_OUTPUT_SIZE = 512
const CROP_CANVAS_BG = '#f9efec'

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

export function computeBaseScale(imageWidth, imageHeight, viewportSize = CROP_VIEWPORT_SIZE) {
  return Math.max(viewportSize / imageWidth, viewportSize / imageHeight)
}

export function clampCropOffset(image, scale, offsetX, offsetY, viewportSize = CROP_VIEWPORT_SIZE) {
  const drawW = image.width * scale
  const drawH = image.height * scale
  const maxOffsetX = Math.max(0, (drawW - viewportSize) / 2)
  const maxOffsetY = Math.max(0, (drawH - viewportSize) / 2)

  return {
    offsetX: clamp(offsetX, -maxOffsetX, maxOffsetX),
    offsetY: clamp(offsetY, -maxOffsetY, maxOffsetY),
  }
}

export function drawCropViewport(ctx, image, state, viewportSize = CROP_VIEWPORT_SIZE) {
  const { scale, offsetX, offsetY } = state

  ctx.clearRect(0, 0, viewportSize, viewportSize)
  ctx.fillStyle = CROP_CANVAS_BG
  ctx.fillRect(0, 0, viewportSize, viewportSize)

  const drawW = image.width * scale
  const drawH = image.height * scale
  const x = viewportSize / 2 + offsetX - drawW / 2
  const y = viewportSize / 2 + offsetY - drawH / 2

  ctx.drawImage(image, x, y, drawW, drawH)
}

export function loadImageFromSrc(src) {
  return new Promise((resolve, reject) => {
    const image = new Image()
    image.onload = () => resolve(image)
    image.onerror = () => reject(new Error('图片加载失败'))
    image.src = src
  })
}

export function cropAvatarToBlob(image, state, options = {}) {
  const viewportSize = options.viewportSize || CROP_VIEWPORT_SIZE
  const outputSize = options.outputSize || CROP_OUTPUT_SIZE
  const quality = options.quality ?? 0.92
  const ratio = outputSize / viewportSize
  const { scale, offsetX, offsetY } = state

  const canvas = document.createElement('canvas')
  canvas.width = outputSize
  canvas.height = outputSize
  const ctx = canvas.getContext('2d')

  ctx.beginPath()
  ctx.arc(outputSize / 2, outputSize / 2, outputSize / 2, 0, Math.PI * 2)
  ctx.closePath()
  ctx.clip()

  ctx.fillStyle = options.backgroundColor || CROP_CANVAS_BG
  ctx.fillRect(0, 0, outputSize, outputSize)

  const drawW = image.width * scale * ratio
  const drawH = image.height * scale * ratio
  const x = outputSize / 2 + offsetX * ratio - drawW / 2
  const y = outputSize / 2 + offsetY * ratio - drawH / 2

  ctx.drawImage(image, x, y, drawW, drawH)

  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (blob) resolve(blob)
        else reject(new Error('裁剪失败'))
      },
      'image/jpeg',
      quality,
    )
  })
}

export { CROP_CANVAS_BG, CROP_OUTPUT_SIZE, CROP_VIEWPORT_SIZE }
