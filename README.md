# SPRIDS-agent-platform
小学期

# Quick Start

## Docker服务
'''
修改docker-compose.yml相关内容
bash
..\SPRIDS-agent-platform
docker compose up -d
'''

## 后端启动
'''
..\SPRIDS-agent-platform\backend
复制.env.example为.env
修改.env相关内容
bash
python -m venv .venv
.venv\Scripts\activate
python.exe -m pip install --upgrade pip
pip install -r requirements
python main.py
'''

## 前端启动
'''
..\SPRIDS-agent-platform\frontend
npm install element-plus @element-plus/icons-vue
npm audit fix --force
npm install vue-router@4 pinia
npm install axios
npm install markdown-it
npm install -D sass
npm run dev
```
