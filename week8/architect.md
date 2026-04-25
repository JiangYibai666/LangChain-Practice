# 系统架构

## 根目录
- a2a-poc/

## 前端层
- frontend/stop
  - index.html // 仪表盘 UI · 对话 · A2A流可视化 · 日志面板

## 启动 + 路由层
- main.py // 唯一入口：init DB → launcher → CLI loop
- cli.py // readline 自然语言交互循环
- launcher.py // asyncio 统一启动三个智能体服务

## A2A 协议层
- a2a/
  - protocol.py 
  - router.py // 进程内消息路由，替代 HTTP，保留协议语义

## 智能体层
- agents/
  - orchestrator.py 
  - flight_agent.py
  - hotel_agent.py 

## 工具层
- tools/
  - flight_search.py 
  - hotel_search.py 
## 数据库层
- db/
  - models.py 
  - session.py 
  - state_store.py 
## Mock 数据
- mock_data/
  - flights.json 
  - hotels.json 
## 配置 + 基础设施
- .env 
- docker-compose.yml 
- requirements.txt 
- README.md // 启动说明 · 架构概览
