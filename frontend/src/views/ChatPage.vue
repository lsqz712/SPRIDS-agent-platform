<template>
  <div class="chat-page">
    <!-- 消息列表区域 -->
    <div class="message-list" ref="messageListRef">
      <div
        v-for="(msg, index) in agentStore.messages"
        :key="index"
        :class="['message-item', `message-${msg.role}`]"
      >
        <!-- 用户消息 -->
        <div v-if="msg.role === 'user'" class="message-bubble user-bubble">
          <div class="message-content">{{ msg.content }}</div>
          <!-- 单张图片附件 -->
          <div v-if="msg.image" class="message-attachment">
            <img :src="msg.imagePreview" alt="附件图片" />
          </div>
          <!-- 多图附件（批量检测） -->
          <div v-if="msg.images && msg.images.length" class="message-attachments-grid">
            <img v-for="(src, i) in msg.images" :key="i" :src="src" alt="附件图片" />
          </div>
        </div>

        <!-- AI 消息 -->
        <div v-else-if="msg.role === 'assistant'" class="message-bubble assistant-bubble">
          <div v-if="msg.loading" class="typing-indicator">
            <span></span><span></span><span></span>
          </div>
          <div
            v-else
            class="message-content markdown-body"
            v-html="renderMarkdown(msg.content)"
          ></div>
          <!-- 检测结果卡片 -->
          <DetectionResultCard v-if="msg.detectionResult" :result="msg.detectionResult" />
        </div>

        <!-- 工具调用提示 -->
        <div v-if="msg.toolCall" class="tool-call-info">
          <el-tag size="small" type="info">
            调用工具: {{ msg.toolCall.tool }}
          </el-tag>
        </div>
      </div>
    </div>

    <!-- 快捷操作栏 -->
    <div class="quick-actions">
      <el-button
        @click="handleQuickDetect('single')"
        :disabled="agentStore.isLoading"
      >
        单图检测
      </el-button>
      <el-button
        @click="handleQuickDetect('batch')"
        :disabled="agentStore.isLoading"
      >
        批量/ZIP
      </el-button>
      <el-button @click="handleQuickDetect('video')" :disabled="agentStore.isLoading">视频</el-button>
      <el-button @click="handleQuickDetect('camera')" :disabled="agentStore.isLoading">摄像头</el-button>
    </div>

    <!-- 输入区域 -->
    <div class="input-area">
      <!-- 附件按钮 -->
      <el-button
        class="attach-btn"
        @click="triggerFileInput"
        :disabled="agentStore.isLoading"
        circle
      >
        <!-- 图标占位 -->
      </el-button>
      <input
        ref="fileInputRef"
        type="file"
        accept="image/*,.zip"
        style="display: none"
        @change="handleFileSelect"
      />
      <!-- 文本输入框 -->
      <el-input
        v-model="inputText"
        placeholder="输入消息，或拖拽图片/ZIP 到这里..."
        @keyup.enter="sendMessage"
        :disabled="agentStore.isLoading"
      />
      <!-- 发送/停止按钮 -->
      <el-button
        v-if="!agentStore.isLoading"
        type="primary"
        @click="sendMessage"
        :disabled="!inputText.trim() && !selectedFile"
      >
        发送
      </el-button>
      <el-button v-else type="danger" @click="handleStop">停止</el-button>
    </div>
  </div>
</template>

<script setup>
/**
 * ChatPage.vue — 智能对话界面
 *
 * 功能：
 *   - 消息气泡（用户/AI 区分）
 *   - 文件附件上传（图片/ZIP 拖拽或选择）
 *   - SSE 流式渲染 AI 回复
 *   - 检测结果卡片展示
 *   - 快捷操作栏（单图/批量/视频/摄像头）
 *   - 中断当前对话
 */
import { detectBatch, detectSingle, detectVideo, detectZip, getVideoStatus } from '@/api/detection'
import DetectionResultCard from '@/components/DetectionResultCard.vue'
import { useAgentStore } from '@/stores/agent'
import { renderMarkdown } from '@/utils/markdown'
import request from '@/utils/request'
import { streamChat } from '@/utils/stream'
import { ElMessage } from 'element-plus'
import { computed, nextTick, onMounted, ref } from 'vue'

// ── Store ──
const agentStore = useAgentStore()

// ── 响应式状态 ──
const inputText = ref('')
const selectedFile = ref(null)
const messageListRef = ref(null)
const fileInputRef = ref(null)

// ── 计算属性 ──
const canSend = computed(() => {
  return inputText.value.trim() || selectedFile.value
})

// ── 方法 ──

/** 发送消息 */
async function sendMessage() {
  if (!canSend.value) return

  const message = inputText.value.trim()
  // 在清空之前保存文件引用
  const fileToSend = selectedFile.value
  const imagePreview = fileToSend ? URL.createObjectURL(fileToSend) : null

  // 添加用户消息到列表
  agentStore.addMessage({
    role: 'user',
    content: message,
    image: fileToSend ? fileToSend.name : null,
    imagePreview
  })

  // 清空输入
  inputText.value = ''
  selectedFile.value = null

  // 添加 AI 加载占位
  agentStore.addMessage({
    role: 'assistant',
    content: '',
    loading: true
  })

  scrollToBottom()

  // 如果有附件图片，先上传到服务端获取真实路径
  let serverImagePath = null
  if (fileToSend) {
    try {
      const formData = new FormData()
      formData.append('file', fileToSend)
      const uploadResult = await request.post('/chat/upload', formData)
      serverImagePath = uploadResult.image_path
    } catch (err) {
      console.error('[图片上传失败]', err.response?.data || err.message || err)
      const lastMsg = agentStore.messages[agentStore.messages.length - 1]
      lastMsg.content = `图片上传失败：${err.response?.data?.detail || err.message || '未知错误'}，请重试`
      lastMsg.loading = false
      lastMsg.error = true
      return
    }
  }

  // 发起 SSE 流式请求
  const requestBody = {
    message,
    ...(serverImagePath ? { image_path: serverImagePath } : {})
  }

  let fullContent = ''
  const stop = streamChat('/api/chat/stream', requestBody, {
    onMessage: (data) => {
      console.log('[SSE事件]', data.type, data.type === 'tool_result' ? data : '')

      if (data.type === 'text_chunk') {
        fullContent += data.content
        agentStore.updateLastAssistantMessage(fullContent)
        scrollToBottom()
      } else if (data.type === 'tool_call') {
        const lastMsg = agentStore.messages[agentStore.messages.length - 1]
        lastMsg.toolCall = { tool: data.tool, input: data.input }
      } else if (data.type === 'tool_result') {
        const lastMsg = agentStore.messages[agentStore.messages.length - 1]
        console.log('[工具结果] tool:', data.tool, 'result长度:', data.result?.length)
        try {
          const result = JSON.parse(data.result)
          console.log('[工具结果解析]', 'total_objects:', result.total_objects, 'detections:', result.detections?.length)
          if (result.detections) {
            lastMsg.detectionResult = result
            lastMsg.loading = false
            console.log('[检测结果卡片已设置]', lastMsg.detectionResult)
          }
        } catch (e) {
          console.warn('[工具结果解析失败]', e.message, '原始数据:', data.result?.substring(0, 200))
          lastMsg.content += `\n[工具结果: ${data.result?.substring(0, 100)}...]`
        }
        scrollToBottom()
      } else if (data.type === 'error') {
        const lastMsg = agentStore.messages[agentStore.messages.length - 1]
        lastMsg.content = data.content
        lastMsg.loading = false
        lastMsg.error = true
      }
    },
    onDone: () => {
      const lastMsg = agentStore.messages[agentStore.messages.length - 1]
      if (lastMsg.loading) {
        lastMsg.loading = false
      }
      agentStore.setLoading(false)
    },
    onError: (err) => {
      const lastMsg = agentStore.messages[agentStore.messages.length - 1]
      lastMsg.content = `抱歉，处理出错了：${err.message}`
      lastMsg.loading = false
      lastMsg.error = true
      agentStore.setLoading(false)
      ElMessage.error('对话请求失败，请重试')
    }
  })

  // 保存中断函数到 store
  agentStore.abortController = stop
}

/** 停止生成 */
function handleStop() {
  agentStore.abort()
  const lastMsg = agentStore.messages[agentStore.messages.length - 1]
  if (lastMsg.loading) {
    lastMsg.loading = false
    lastMsg.content += '\n[已停止生成]'
  }
}

/** 触发文件选择框 */
function triggerFileInput() {
  fileInputRef.value?.click()
}

/** 文件选择回调 */
function handleFileSelect(event) {
  const file = event.target.files[0]
  if (file) {
    selectedFile.value = file
    file._tempPath = URL.createObjectURL(file)
    ElMessage.info(`${file.name} 已选择`)
  }
}

/** 滚动到底部 */
function scrollToBottom() {
  nextTick(() => {
    if (messageListRef.value) {
      messageListRef.value.scrollTop = messageListRef.value.scrollHeight
    }
  })
}

/**
 * 快捷单图检测流程
 */
async function handleQuickDetect(type) {
  if (type === 'single') {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = 'image/*'
    input.onchange = async (e) => {
      const file = e.target.files[0]
      if (!file) return

      agentStore.addMessage({
        role: 'user',
        content: `[快捷检测] ${file.name}`,
        image: file.name,
        imagePreview: URL.createObjectURL(file)
      })

      agentStore.addMessage({
        role: 'assistant',
        content: '正在检测中...',
        loading: true
      })

      const formData = new FormData()
      formData.append('file', file)
      try {
        const result = await detectSingle(formData)
        const lastMsg = agentStore.messages[agentStore.messages.length - 1]
        lastMsg.content = `检测完成！发现 ${result.total_objects} 个目标。`
        lastMsg.loading = false
        lastMsg.detectionResult = result
      } catch (err) {
        const lastMsg = agentStore.messages[agentStore.messages.length - 1]
        lastMsg.content = '检测失败，请重试'
        lastMsg.loading = false
      }
    }
    input.click()
  } else if (type === 'batch') {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = 'image/*,.zip'
    input.multiple = true
    input.onchange = async (e) => {
      const files = Array.from(e.target.files)
      if (!files.length) return

      const isZip = files.some((f) => f.name.endsWith('.zip'))
      const formData = new FormData()

      if (isZip && files.length === 1) {
        formData.append('file', files[0])
        agentStore.addMessage({
          role: 'user',
          content: `[快捷检测] ZIP: ${files[0].name}`
        })
      } else {
        files.forEach((f) => formData.append('files', f))
        const imagePreviews = files.map((f) => URL.createObjectURL(f))
        agentStore.addMessage({
          role: 'user',
          content: `[快捷检测] ${files.length} 张图片`,
          images: imagePreviews
        })
      }

      agentStore.addMessage({
        role: 'assistant',
        content: '正在批量检测中...',
        loading: true
      })

      try {
        const apiCall = isZip ? detectZip(formData) : detectBatch(formData)
        const result = await apiCall
        const lastMsg = agentStore.messages[agentStore.messages.length - 1]
        if (result.error) {
          lastMsg.content = `批量检测失败：${result.error}`
          lastMsg.loading = false
          lastMsg.error = true
          return
        }
        const totalObjects = result.total_objects ?? 0
        lastMsg.content = `批量检测完成！共 ${totalObjects} 个目标。`
        lastMsg.loading = false
        lastMsg.detectionResult = result
        console.log('[批量检测结果]', result)
      } catch (err) {
        console.error('[批量检测异常]', err)
        const lastMsg = agentStore.messages[agentStore.messages.length - 1]
        lastMsg.content = `批量检测失败：${err.message || err}`
        lastMsg.loading = false
        lastMsg.error = true
      }
    }
    input.click()
  } else if (type === 'video') {
    handleVideoDetect()
  } else if (type === 'camera') {
    // 跳转到检测工作台页面
    window.location.hash = '#/detection'
  }
}

/**
 * 视频检测流程：
 * 1. 用户点击 "🎬 视频" 按钮
 * 2. 弹出文件选择框（限制视频格式）
 * 3. 选择视频后，上传到后端
 * 4. 后端返回 task_id，前端开始轮询进度
 * 5. 处理完成后，展示关键帧结果卡片
 */
async function handleVideoDetect() {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = "video/mp4,video/avi,video/quicktime,video/x-msvideo";
  input.onchange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // 校验文件大小（50MB）
    const maxSize = 50 * 1024 * 1024;
    if (file.size > maxSize) {
      ElMessage.warning("视频文件不能超过 50MB");
      return;
    }

    // 创建视频的 Blob URL 用于预览
    const videoUrl = URL.createObjectURL(file);

    // 添加用户消息
    agentStore.addMessage({
      role: "user",
      content: `[视频检测] ${file.name} (${(file.size / (1024 * 1024)).toFixed(1)}MB)`,
      videoUrl,
    });

    // 添加加载占位
    agentStore.addMessage({
      role: "assistant",
      content: "正在上传视频...",
      loading: true,
    });

    // 上传视频
    const formData = new FormData();
    formData.append("file", file);

    try {
      const uploadResult = await detectVideo(formData);
      const taskId = uploadResult.task_id;

      // 更新加载消息
      const lastMsg = agentStore.messages[agentStore.messages.length - 1];
      lastMsg.content = "视频已上传，正在处理中...";

      // 开始轮询进度
      await pollVideoProgress(taskId);
    } catch (err) {
      console.error("[视频检测失败]", err);
      const lastMsg = agentStore.messages[agentStore.messages.length - 1];
      lastMsg.content = `视频检测失败：${err.message || err}`;
      lastMsg.loading = false;
      lastMsg.error = true;
    }
  };
  input.click();
}

/**
 * 轮询视频检测进度
 */
async function pollVideoProgress(taskId) {
  const maxAttempts = 120; // 最多轮询 120 次（4 分钟）
  for (let i = 0; i < maxAttempts; i++) {
    await new Promise((r) => setTimeout(r, 2000)); // 每 2 秒轮询一次
    try {
      const status = await getVideoStatus(taskId);

      if (status.status === "completed") {
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        const result = status.result || {};
        lastMsg.content = `视频检测完成！共处理 ${result.processed_frames || 0} 帧，发现 ${result.total_objects || 0} 个目标。`;
        lastMsg.loading = false;
        lastMsg.detectionResult = result;
        return;
      } else if (status.status === "failed") {
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        lastMsg.content = `视频检测失败：${status.message || "未知错误"}`;
        lastMsg.loading = false;
        lastMsg.error = true;
        return;
      }

      // 更新进度提示
      const lastMsg = agentStore.messages[agentStore.messages.length - 1];
      lastMsg.content = `视频处理中... (${status.message || ""})`;
    } catch (err) {
      console.error("[轮询进度失败]", err);
    }
  }

  // 超时
  const lastMsg = agentStore.messages[agentStore.messages.length - 1];
  lastMsg.content = "视频检测超时，请稍后在历史记录中查看结果";
  lastMsg.loading = false;
}

onMounted(() => {
  if (agentStore.messages.length === 0) {
    agentStore.addMessage({
      role: 'assistant',
      content:
        '你好！我是 SPRIDS 目标检测智能体助手。\n\n你可以：\n- 上传一张图片，让我帮你检测目标\n- 使用下方的快捷按钮直接触发检测\n- 用自然语言描述你的需求\n\n试试发一张图片给我吧！'
    })
  }
})
</script>

<style lang="scss" scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f5f5f5;
}

/* 消息列表 */
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.message-item {
  display: flex;
  margin-bottom: 16px;

  &.message-user {
    justify-content: flex-end;
  }
  &.message-assistant {
    justify-content: flex-start;
  }
}

.message-bubble {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.5;
  word-break: break-word;
}

.user-bubble {
  background: #409eff;
  color: white;
  border-bottom-right-radius: 4px;
}

.assistant-bubble {
  background: white;
  border: 1px solid #e0e0e0;
  border-bottom-left-radius: 4px;
}

.message-content {
  white-space: pre-wrap;
}

.markdown-body {
  /* markdown 渲染后的 HTML 样式 */
  h1,
  h2,
  h3 {
    margin-top: 8px;
    margin-bottom: 4px;
  }
  table {
    border-collapse: collapse;
    width: 100%;
    margin: 8px 0;
  }
  th,
  td {
    border: 1px solid #e0e0e0;
    padding: 4px 8px;
  }
  code {
    background: #f0f0f0;
    padding: 2px 4px;
    border-radius: 3px;
  }
}

.typing-indicator {
  display: flex;
  gap: 4px;

  span {
    width: 6px;
    height: 6px;
    background: #999;
    border-radius: 50%;
    animation: typing 1.2s infinite;

    &:nth-child(2) {
      animation-delay: 0.2s;
    }
    &:nth-child(3) {
      animation-delay: 0.4s;
    }
  }
}

/* 快捷操作栏 */
.quick-actions {
  display: flex;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid #e0e0e0;
  background: white;
}

/* 输入区域 */
.input-area {
  display: flex;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid #e0e0e0;
  background: white;

  .el-input {
    flex: 1;
  }
}

/* 附件预览 */
.message-attachment {
  margin-top: 8px;

  img {
    max-width: 200px;
    border-radius: 8px;
    border: 1px solid #e0e0e0;
  }
}

/* 多图附件网格 */
.message-attachments-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
  gap: 8px;
  margin-top: 8px;

  img {
    width: 100%;
    height: 80px;
    object-fit: cover;
    border-radius: 6px;
    border: 1px solid #e0e0e0;
  }
}

/* 工具调用信息 */
.tool-call-info {
  margin-top: 8px;
  padding: 4px 8px;
  background: #f5f5f5;
  border-radius: 4px;
  font-size: 12px;
  color: #666;
}

@keyframes typing {
  0%,
  60%,
  100% {
    opacity: 0.3;
    transform: translateY(0);
  }
  30% {
    opacity: 1;
    transform: translateY(-4px);
  }
}
</style>