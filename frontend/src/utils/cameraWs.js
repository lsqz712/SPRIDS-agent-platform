/**
 * cameraWs.js — 摄像头实时检测 WebSocket 工具
 */

class CameraWs {
  constructor(options) {
    this.ws = null;
    this.isConnected = false;
    this._closing = false;
    this._configTimer = null;

    this.mode = options.mode || 'cpu';
    this.conf = options.conf || 0.25;
    this.iou = options.iou || 0.45;
    this.sceneId = options.sceneId;

    this.onResult = options.onResult || (() => {});
    this.onConfigOk = options.onConfigOk || (() => {});
    this.onError = options.onError || (() => {});
    this.onClose = options.onClose || (() => {});
    this.onStatusChange = options.onStatusChange || (() => {});
  }

  connect() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.warn('[CameraWs] 已存在活跃连接');
      return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const token = localStorage.getItem('SPRIDS_token') || localStorage.getItem('rsod_token') || '';
    const wsUrl = `${protocol}//${host}/api/detection/camera?token=${token}`;

    console.log('[CameraWs] 正在连接:', wsUrl.replace(token, '***'));
    this.onStatusChange('connecting');
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      this.isConnected = true;
      console.log('[CameraWs] 连接已建立，发送配置...');
      this.ws.send(JSON.stringify({
        type: 'config', mode: this.mode, conf: this.conf,
        iou: this.iou, scene_id: this.sceneId,
      }));
      this.onStatusChange('loading');
      // 30秒超时检测
      this._configTimer = setTimeout(() => {
        console.error('[CameraWs] config_ok 超时（30秒未响应），后端可能未启动或模型加载失败');
        this.onStatusChange('timeout');
        this.onError('模型加载超时，请检查后端服务');
      }, 30000);
    };

    this.ws.onmessage = (event) => {
      if (this._closing) return;
      try {
        const data = JSON.parse(event.data);
        console.log('[CameraWs] 收到消息:', data.type);
        this._handleMessage(data);
      } catch (err) {
        console.error('[CameraWs] 消息解析失败:', err);
      }
    };

    this.ws.onclose = () => {
      this.isConnected = false;
      this.ws = null;
      if (this._configTimer) { clearTimeout(this._configTimer); this._configTimer = null; }
      console.log('[CameraWs] 连接已关闭');
      this.onStatusChange('disconnected');
      this.onClose();
    };

    this.ws.onerror = (err) => {
      console.error('[CameraWs] 连接错误:', err);
      this.onError('WebSocket 连接失败，请检查后端服务');
    };
  }

  sendFrame(base64Data) {
    if (this._closing) return false;
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('[CameraWs] 连接未建立');
      return false;
    }
    if (!base64Data) return false;
    this.ws.send(JSON.stringify({ type: 'frame', data: base64Data }));
    return true;
  }

  close() {
    this._closing = true;
    if (this._configTimer) { clearTimeout(this._configTimer); this._configTimer = null; }
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      try { this.ws.send(JSON.stringify({ type: 'close' })); } catch {}
      setTimeout(() => {
        try { if (this.ws && this.ws.readyState === WebSocket.OPEN) this.ws.close(); } catch {}
      }, 500);
    }
  }

  updateConfig(config) {
    this.mode = config.mode || this.mode;
    this.conf = config.conf || this.conf;
    this.iou = config.iou || this.iou;
    this.sceneId = config.sceneId;
  }

  _handleMessage(data) {
    switch (data.type) {
      case 'result':
        this.onResult({
          annotatedFrame: data.annotated_frame,
          detections: data.detections || [],
          objectCount: data.object_count || 0,
          inferenceTime: data.inference_time || 0,
          fps: data.fps || 0,
          frameCount: data.frame_count || 0,
        });
        break;
      case 'config_ok':
        if (this._configTimer) { clearTimeout(this._configTimer); this._configTimer = null; }
        console.log('[CameraWs] 配置确认:', data.message);
        this.onStatusChange('detecting');
        this.onConfigOk(data);
        break;
      case 'close_ok':
        console.log('[CameraWs] 历史已保存:', data.task_id, data.total_objects, '个目标');
        this.onClose(data);
        break;
      case 'error':
        console.error('[CameraWs] 服务端错误:', data.message);
        this.onError(data.message);
        break;
      default:
        console.warn('[CameraWs] 未知消息类型:', data.type);
    }
  }
}

export function createCameraWs(options) {
  return new CameraWs(options);
}
