# Doxa Connex — AI 多智能体架构

> **版本：** 1.0 | **日期：** 2026年4月9日 | **状态：** 最终版 — 可实施
>
> 本文档描述了为 Doxa Connex 平台新增 AI 聊天功能的架构。系统使用多个专属智能体来回答有关发票、实体、采购和付款的问题，
> 同时保留平台现有的认证和 RBAC 模型，对生产服务不做任何改动。

---

## 目录

1. [执行摘要](#执行摘要)
2. [决策摘要](#决策摘要)
3. [架构概述](#架构概述)
4. [流量如何流转 — 两条独立路径](#流量如何流转--两条独立路径)
5. [内部 VPC 网络 — 智能体到服务](#内部-vpc-网络--智能体到服务)
6. [用户流程](#用户流程)
7. [认证与授权 — 零妥协](#认证与授权--零妥协)
8. [A2A 协议 — 智能体通信](#a2a-协议--智能体通信)
9. [LLM 集成 — AWS Bedrock](#llm-集成--aws-bedrock)
10. [RAG — Pinecone 向量数据库](#rag--pinecone-向量数据库)
11. [数据存储 — Aurora PostgreSQL Serverless v2](#数据存储--aurora-postgresql-serverless-v2)
12. [基础设施组件](#基础设施组件)
13. [网络安全](#网络安全)
14. [为何选择此架构 — 考虑的备选方案](#为何选择此架构--考虑的备选方案)
15. [部署管道](#部署管道)
16. [可观察性](#可观察性)
17. [实施阶段](#实施阶段)
18. [关键文件参考](#关键文件参考)

---

## 执行摘要

### 我们要构建的内容

一个嵌入现有 Doxa Connex UI 的聊天式 AI 助手。用户可以用自然语言提问（"显示公司 X 的未结发票"、"供应商 ABC 的付款条款是什么？"），并获得来自实时平台数据和上传文档的实时答案。

### 关键原则

| 原则 | 实现方式 |
|-----------|-------------------|
| **对生产系统零影响** | 聊天基础设施完全独立 — 不同的 AWS 服务、不同的集群、不同的数据库 |
| **与 UI 相同的安全性** | 智能体使用已登录用户的 JWT。每个 API 调用都通过现有完整认证链 |
| **从不离开 VPC** | 智能体到服务调用通过内部 NLB 直接路由到 Zuul Gateway — 无互联网跳转 |
| **可扩展且成本高效** | ECS Fargate 在空闲时自动缩容到 0。无需 GPU 服务器。按 LLM token 付费 |
| **开放协议** | 智能体使用 A2A 标准（Google 的 Agent-to-Agent 协议）进行通信，以便未来扩展 |

### 现有基础设施的变更

| 现有组件 | 所需变更 |
|-------------------|----------------|
| EKS 集群 | 无 |
| NGINX Ingress 控制器 | 无 |
| Zuul Gateway 代码 | 无 |
| 所有下游服务 | 无 |
| 现有数据库 | 无 |
| **唯一新增** | 一个新的 Kubernetes `Service` 资源（类型 `LoadBalancer`，内部），指向现有 Zuul Gateway pod — 在 VPC 内创建私有 NLB |
| **唯一安全组变更** | EKS 工作节点上新增一条入口规则，允许来自新内部 NLB 的 8080 端口 |

---

## 决策摘要

| 决策 | 选择 | 依据 |
|----------|--------|-----------|
| 智能体运行时 | **ECS Fargate（Python）** | 适合 AI/LLM，独立于 EKS，可缩容到 0 |
| WebSocket 层 | **AWS API Gateway WebSocket API** | 客户端连接可在任务重启时保持，AWS 托管 |
| 智能体通信 | **A2A 协议（HTTP 上的 JSON-RPC）** | 多智能体标准协议，支持 AgentCard 发现 |
| 智能体发现 | **AWS Cloud Map** | VPC 内私有 DNS 服务发现 |
| 智能体→服务通信 | **内部 NLB → Zuul Gateway（VPC 内部）** | 无互联网跳转，约 2ms 延迟，无 NAT 成本，保留完整 RBAC |
| 智能体→服务认证 | **每次请求传递用户 JWT** | 完整 RBAC 强制执行 — 智能体权限与用户一致 |
| LLM 提供商 | **AWS Bedrock（Claude, Titan）** | 托管服务，无 GPU 基础设施，IAM 原生认证，VPC 端点 |
| 向量数据库 | **Pinecone（Serverless）** | 托管 RAG 向量 DB，支持公司隔离的元数据过滤 |
| 状态与检查点 | **Aurora PostgreSQL Serverless v2** | LangGraph 原生检查点，ACID，团队已使用 PostgreSQL |
| 对现有系统的影响 | **几乎为零** | 一个 K8s Service + 一条 SG 规则。没有现有服务代码改动 |

---

## 架构概述

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              Internet                                        │
└──────────┬───────────────────────────────────────────┬───────────────────────┘
           │                                           │
  wss://chat.doxa-holdings.com                https://api-connex.doxa-holdings.com
   (chat WebSocket traffic)                    (existing browser/API traffic)
           │                                           │
┌──────────▼────────────────────┐        ┌─────────────▼──────────────────┐
│  AWS API Gateway WebSocket    │        │  NGINX Ingress (existing)      │
│  (AWS-managed, never restarts)│        │  (unchanged)                   │
│                               │        │                                │
│  $connect  → Lambda auth      │        │  /* → Zuul Gateway → services  │
│  sendMessage → VPC Link       │        └────────────────────────────────┘
│  $disconnect → VPC Link       │
└──────────┬────────────────────┘
           │ VPC Link (private)
┌──────────▼────────────────────┐
│  Internal NLB (for agents)    │
└──────────┬────────────────────┘
           │
┌──────────▼──────────────────────────────────────────────────────────────────┐
│  ECS Cluster (Fargate) — NEW                                                │
│                                                                             │
│  ┌───────────────────────────────┐    ┌──────────────────────────────────┐  │
│  │  Orchestrator Agent           │    │  Shared Services                 │  │
│  │  (Python, LangGraph)          │    │                                  │  │
│  │                               │    │  → Aurora PostgreSQL (state)     │  │
│  │  POST /connect                │    │  → Bedrock via VPC Endpoint      │  │
│  │  POST /message  ──push──┐    │    │  → Pinecone via NAT Gateway      │  │
│  │  POST /disconnect       │    │    └──────────────────────────────────┘  │
│  └────────────┬────────────│────┘                                          │
│               │ A2A        │ API GW Management API                         │
│       ┌───────┼────────┬───│──────┐                                        │
│       ▼       ▼        ▼   │      ▼                                        │
│  invoice   entity  purchasing  payment                                      │
│  agent     agent   agent       agent                                        │
│  (Python)  (Python)(Python)    (Python)                                     │
│       │       │        │          │                                         │
│       │   All agents use Bedrock (LLM) + Pinecone (RAG)                    │
│       │       │        │          │                                         │
└───────┼───────┼────────┼──────────┼─────────────────────────────────────────┘
        │       │        │          │                                    │
        │  HTTP + JWT (internal VPC — never leaves the network)         │
        │       │        │          │                                    │
┌───────▼───────▼────────▼──────────▼────────────────────────────────┐  │
│  Internal NLB (for service calls) — NEW                            │  │
│  api-internal.doxa-holdings.com (Route 53 Private Hosted Zone)     │  │
└───────────────────────┬────────────────────────────────────────────┘  │
                        │                                               │
┌───────────────────────▼────────────────────────────────────────────┐  │
│  EKS Cluster (existing, unchanged)                                 │  │
│                                                                    │  │
│  Zuul Gateway (receives agent calls directly, skipping NGINX)      │  │
│    → OAuth2AuthenticationProcessingFilter (token validation)       │  │
│    → /introspect token check       → JWT validation via JWKS      │  │
│    → CustomActiveUserFilter        → DoxaAuthenticationManager    │  │
│    → doxa-oauth2          (auth)   → doxa-connex-entity (entity)  │  │
│    → doxa-invoices     (invoices)  → doxa-purchasing   (POs)      │  │
│    → doxa-payment      (payments)  → doxa-connex-media (media)    │  │
└────────────────────────────────────────────────────────────────────┘  │
                                                                       │
┌────────────────────────────────────────────────────────────────────┐  │
│  Browser (Chat UI)  ◄──── WSS ──── API Gateway ◄─────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

---

## 流量如何流转 — 两条独立路径

```
PATH 1 — 现有浏览器流量（不变）:
  Browser → Internet → NLB (public) → NGINX Ingress → Zuul Gateway → Services
  (TLS 在 NGINX 终止，完整认证链，所有现有路由)

PATH 2 — 智能体聊天流量（新增，完全隔离）:
  Browser → WSS → API Gateway WebSocket → VPC Link → Internal NLB → Orchestrator (ECS)
  Orchestrator → A2A → Service Agent (ECS) → Internal NLB → Zuul Gateway → Services
  (VPC 内部，未经过互联网，JWT 每次调用都携带)
```

这两条路径**绝不交叉**。聊天系统的问题不会影响现有浏览器流量。

---

## 内部 VPC 网络 — 智能体到服务

### 为什么要使用内部网络（而不是公网）

ECS（智能体）和 EKS（服务）运行在**同一个 VPC**内。若让智能体调用走公网，则既浪费又不安全：

| 因素 | 公网路径 | 内部 VPC 路径（选择） |
|--------|---------------------|---------------------------|
| 延迟 | +50-100ms（互联网往返） | **~2-5ms** |
| NAT 网关出站成本 | ~$0.045/GB | **$0** |
| TLS 开销 | 每次请求完整 TLS 握手 | **不需要**（私有网络） |
| 攻击面 | 流量暴露于互联网 | **零互联网暴露** |
| 认证执行 | 7 层（NGINX + Zuul + 服务） | **6 层**（Zuul + 服务 — NGINX 跳过，NGINX 无认证逻辑） |

### 工作原理

一个新的 Kubernetes Service 创建一个私有 NLB，指向现有 Zuul Gateway pod：

```yaml
# internal-zuul-service.yml — deployed in EKS, zero changes to existing resources
apiVersion: v1
kind: Service
metadata:
  name: zuul-gateway-internal
  namespace: default
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
    service.beta.kubernetes.io/aws-load-balancer-internal: "true"
    service.beta.kubernetes.io/aws-load-balancer-scheme: "internal"
spec:
  type: LoadBalancer
  selector:
    app: zuul-gateway              # same selector as existing Zuul Service
  ports:
    - name: http
      port: 80
      targetPort: 8080             # Zuul container port
      protocol: TCP
```

**通过 Route 53 私有托管区域实现私有 DNS：**

```
Zone:   internal.doxa-holdings.com (与 VPC 关联，非公开)
Record: api-internal.doxa-holdings.com → ALIAS → Internal NLB DNS
```

### 智能体代码 — 之前与之后

```python
# Before (public internet — unnecessary):
response = requests.get(
    "https://api-connex-dev.doxa-holdings.com/invoice/api/invoices",
    headers={"Authorization": f"Bearer {user_jwt}"},
    params={"companyUuid": company_uuid, "status": "PENDING"}
)

# After (internal VPC — faster, cheaper, more secure):
response = requests.get(
    "http://api-internal.doxa-holdings.com/invoice/api/invoices",
    headers={"Authorization": f"Bearer {user_jwt}"},   # same JWT, same RBAC
    params={"companyUuid": company_uuid, "status": "PENDING"}
)
```

### 认证链对比 — 检查项

| 检查点 | 浏览器（公网） | 智能体（内部 VPC） | 一致？ |
|---|---|---|---|
| NGINX Ingress | ✓ TLS + 路由 | **跳过**（不需要） | — |
| Zuul `OAuth2AuthenticationProcessingFilter` | ✓ | **✓** | ✅ |
| Zuul → `/introspect` 令牌校验 | ✓ | **✓** | ✅ |
| Zuul 预过滤器（客户端凭证注入） | ✓ | **✓** | ✅ |
| 服务 JWT 通过 JWKS 校验 | ✓ | **✓** | ✅ |
| `CustomActiveUserFilter` | ✓ | **✓** | ✅ |
| `DoxaAuthenticationManager` RBAC | ✓ | **✓** | ✅ |

**保留了 6 层中的 7 层。唯一跳过的是 NGINX，其仅执行 TLS 终止和路由 — 无任何认证逻辑。**

---

## 用户流程

### 流程 1：用户打开聊天（WebSocket 连接）

```
步骤 1：用户已登录（持有 doxa-oauth2 的 JWT）
        JWT 包含：sub、name、user_id、roles、companies[]、exp

步骤 2：前端打开 WebSocket
        wss://chat.doxa-holdings.com/ws/chat?token=<jwt_access_token>

步骤 3：API Gateway 的 $connect 路由触发 Lambda 授权器
        Lambda：
          a. 解析查询参数中的 JWT
          b. 从 doxa-oauth2 JWKS 端点获取公钥
          c. 验证 RSA256 签名、过期时间、颁发者
          d. 提取声明：userId、name、companies、roles
          e. 返回带用户上下文的 Allow 策略

步骤 4：API Gateway 通过 VPC Link 将 $connect 转发给 orchestrator 智能体
        POST http://orchestrator-agent.agents.local:8080/api/chat/connect
        Headers：
          connectionId: abc123
          userId: <uuid>
          userName: John Doe
          companies: [{"uuid":"xyz","roles":"ENTITY_ADMIN","authorities":"INVOICE:read..."}]
          roles: ENTITY_ADMIN

步骤 5：Orchestrator 智能体将连接信息存储到 PostgreSQL
        INSERT INTO chat_connections (connection_id, user_id, user_name,
          companies, roles, user_jwt, connected_at)
        VALUES ('abc123', <uuid>, 'John Doe', <json>, 'ENTITY_ADMIN', <jwt>, NOW())

步骤 6：WebSocket 连接建立
        客户端收到：{"type": "CONNECTED", "sessionId": "abc123"}
```

### 流程 2：用户发送聊天消息

```
步骤 1：用户输入 "Show me all pending invoices for company X"
         前端通过 WebSocket 发送：
         {
           "action": "sendMessage",
           "conversationId": "conv-789",
           "companyUuid": "company-x-uuid",
           "message": "Show me all pending invoices for company X"
         }

步骤 2：API Gateway 通过 VPC Link 路由到 orchestrator
         POST http://orchestrator-agent.agents.local:8080/api/chat/message
         Headers: connectionId: abc123
         Body: （上述消息）

步骤 3：Orchestrator 从 PostgreSQL 加载用户上下文
         SELECT * FROM chat_connections WHERE connection_id = 'abc123'
         获取：userId、companies、roles、userJwt

步骤 4：RBAC 预检查 — 用户是否属于公司 X？
         从存储的 JWT 声明中读取 companies[]
         验证 company-x-uuid 是否存在于用户公司列表中
         验证用户是否对该公司具有相关角色
         如果不满足 → 推送错误给客户端，停止处理

步骤 5：Orchestrator 使用 AWS Bedrock（Claude Haiku，快速）分类意图
         bedrock.invoke_model(modelId="anthropic.claude-3-haiku...", body=prompt)
         结果：intent="query-invoices", target_agent="invoice-agent"

步骤 6：Orchestrator 向 invoice agent 发送 A2A 任务
         POST http://invoice-agent.agents.local:8080/a2a
         {
           "jsonrpc": "2.0",
           "method": "tasks/send",
           "params": {
             "id": "task-456",
             "message": {
               "role": "user",
               "parts": [{"type": "text", "text": "Show all pending invoices for company X"}]
             },
             "metadata": {
               "user_jwt": "<user's JWT>",
               "user_id": "<uuid>",
               "company_uuid": "company-x-uuid",
               "roles": "ENTITY_ADMIN",
               "authorities": "INVOICE:read INVOICE:write"
             }
           }
         }

步骤 7：Invoice agent 通过内部 VPC 路径调用发票服务
         GET http://api-internal.doxa-holdings.com/invoice/api/invoices
             ?companyUuid=company-x-uuid&status=PENDING
         Headers:
           Authorization: Bearer <user's JWT>

步骤 8：请求通过现有认证链流转（Zuul → 服务）：
         Internal NLB → Zuul Gateway
           → OAuth2AuthenticationProcessingFilter
             → RemoteTokenServices → doxa-oauth2 /introspect（验证令牌）
           → Zuul 代理到 invoice service
             → JWTSecurityConfig: oauth2ResourceServer(jwt) 通过 JWKS 验证
             → CustomActiveUserFilter：检查用户是否仍然激活
             → Controller 处理请求，返回发票数据

         *** 完整的认证和授权得到执行 ***
         *** 智能体具有与用户完全相同的权限 ***

步骤 9：Invoice agent 处理响应
         接收来自服务的发票数据
         可选地查询 Pinecone 以获取相关文档上下文（RAG）
         使用 AWS Bedrock（Claude Sonnet）格式化为可读摘要
         返回 A2A 响应给 orchestrator

步骤 10：Orchestrator 通过 API Gateway Management API 推送响应给客户端
         POST https://{api-id}.execute-api.{region}.amazonaws.com/{stage}/@connections/abc123
         Body: {
           "type": "AGENT_RESPONSE",
           "conversationId": "conv-789",
           "message": "I found 5 pending invoices for Company X totaling $45,230...",
           "metadata": {"agentName": "invoice-agent", "taskId": "task-456"}
         }

步骤 11：将聊天记录保存到 PostgreSQL
         INSERT INTO chat_messages (conversation_id, user_id, role, content,
           agent_name, company_uuid, task_id, created_at)
         VALUES ('conv-789', <userId>, 'agent', 'I found 5 pending...',
           'invoice-agent', 'company-x-uuid', 'task-456', NOW())
         LangGraph checkpointer 自动将智能体状态保存到 checkpoints 表中

步骤 12：客户端在聊天 UI 中呈现响应
```

### 流程 3：活动聊天期间令牌过期

```
步骤 1：用户已聊天约 45 分钟，JWT 接近过期。

步骤 2：用户发送消息 → invoice agent 调用发票服务
        发票服务返回 401 Unauthorized（JWT 过期）

步骤 3：Invoice agent 检测到 401，返回错误给 orchestrator
        { "status": "error", "error": "TOKEN_EXPIRED" }

步骤 4：Orchestrator 推送令牌刷新请求给客户端
        { "type": "TOKEN_REFRESH_NEEDED" }

步骤 5：前端使用现有 OAuth2 刷新流程刷新令牌
        POST /auth/token (grant_type=refresh_token)
        收到新的 access_token + refresh_token

步骤 6：前端通过 WebSocket 发送刷新后的令牌
        { "action": "sendMessage", "type": "TOKEN_REFRESH", "token": "<new JWT>" }

步骤 7：Orchestrator 验证新 JWT 并更新 PostgreSQL
        UPDATE chat_connections SET user_jwt = '<new JWT>' WHERE connection_id = 'abc123'
        重试原始失败请求，使用新令牌

步骤 8：用户看到响应 — 不会察觉令牌刷新发生
```

### 流程 4：ECS 任务重启期间的活动聊天

```
步骤 1：用户正在进行对话
        Browser ──WSS──► API Gateway ──HTTP──► orchestrator-task-0

步骤 2：ECS 部署新版本 → orchestrator-task-0 收到 SIGTERM

步骤 3：任务优雅退出（完成正在处理的工作）
        不需要通知 WebSocket 客户端（API Gateway 持有连接）

步骤 4：orchestrator-task-1 启动，健康检查通过，注册到 Cloud Map

步骤 5：用户发送下一条消息 → API GW 路由到 orchestrator-task-1

步骤 6：orchestrator-task-1 从 PostgreSQL 加载上下文
        LangGraph checkpointer 自动从上一个检查点恢复
        聊天历史从 chat_messages 表加载

步骤 7：正常处理消息，通过 Management API 推送响应
        *** WebSocket 连接始终未被中断 ***
        *** 无需重新连接，无需重新认证 ***
```

### 流程 5：API Gateway 空闲超时 / 最长时长

```
步骤 1：前端每 5 分钟发送 ping 以保持连接活跃
        （API Gateway 空闲超时为 10 分钟）

步骤 2：大约 1 小时 50 分钟后（接近 2 小时最大时长）
        前端主动关闭并重新打开连接
        新 connectionId 分配，并在 PostgreSQL 中映射到相同 conversationId
        *** 用户无感知 — 前端透明处理重连 ***
```

---

## 认证与授权 — 零妥协

### 三重安全层

```
Layer 1: WebSocket Connection (API Gateway)
  ├── JWT validated by Lambda Authorizer at $connect
  ├── Same RSA256 keys from doxa-oauth2 JWKS
  ├── Same issuer, expiration, signature validation
  └── Unauthenticated connections are rejected with 401

Layer 2: Agent-to-Agent Communication (A2A within ECS)
  ├── Internal VPC traffic only (not internet-accessible)
  ├── Security groups restrict to ECS cluster + VPC Link only
  ├── User's JWT passed as metadata (not as agent auth)
  └── Agents don't authenticate to each other (trusted internal network)

Layer 3: Agent-to-Service Communication (ECS → Zuul → EKS Services)
  ├── Routed through Internal NLB → Zuul Gateway (VPC-internal)
  ├── User's JWT used in Authorization header
  ├── Flows through FULL existing auth chain:
  │   ├── Zuul: OAuth2AuthenticationProcessingFilter
  │   ├── Zuul: Token introspection via doxa-oauth2 /introspect
  │   ├── Service: JWT validation via JWKS
  │   ├── Service: CustomActiveUserFilter (active user check)
  │   └── Service: DoxaAuthenticationManager (RBAC from JWT claims)
  └── Agent can NEVER exceed user's permissions
```

### 授权检查点（7 层）

| # | 位置 | 检查内容 |
|---|-------|----------------|
| 1 | API GW `$connect`（Lambda） | JWT 签名、过期、颁发者。无效则 401，拒绝连接 |
| 2 | Orchestrator Agent | 用户是否属于请求公司（JWT companies[] 声明） |
| 3 | Service Agent | 用户是否具备功能权限（`authorities` 声明，例如 `INVOICE:read`） |
| 4 | Zuul Gateway | 通过 `/introspect` 检查令牌是否处于激活状态、未被撤销 |
| 5 | 下游服务 | 通过 JWKS 本地验证 JWT：签名、过期、颁发者 |
| 6 | CustomActiveUserFilter | 用户仍在系统中处于激活状态（未被禁用） |
| 7 | DoxaAuthenticationManager | 强制执行 JWT 中的 RBAC 声明（公司、角色、权限） |

**每次智能体操作共有 7 层检查。**与直接浏览器请求相同：路径 4-7 保持一致，智能体路径额外增加 1-3 层（更强的安全性）。

### 智能体永远不能执行的动作

| 禁止操作 | 阻止点 |
|-----------------|-----------|
| 访问另一个公司的数据 | 检查点 #2（orchestrator）+ #7（服务 RBAC） |
| 执行用户角色不允许的操作 | 检查点 #3（agent）+ #7（服务 RBAC） |
| 在用户停用后继续操作 | 检查点 #6（CustomActiveUserFilter） |
| 使用过期或被撤销令牌 | 检查点 #1（Lambda）+ #4（introspection）+ #5（JWKS） |
| 访问 `/private/**` 内部端点 | 智能体仅调用 Zuul Gateway（仅公开路由） |
| 提权 | JWT 使用 RSA256 签名 — 智能体无法修改声明 |

---

## A2A 协议 — 智能体通信

### 通过 AgentCard 进行智能体发现

每个智能体在 `/.well-known/agent.json` 发布一个 [AgentCard](https://google.github.io/A2A/)：

```json
{
  "name": "invoice-agent",
  "description": "Handles invoice queries, creation, and approval workflows",
  "url": "http://invoice-agent.agents.local:8080",
  "version": "1.0.0",
  "capabilities": { "streaming": true, "pushNotifications": false },
  "skills": [
    { "id": "query-invoices", "name": "Query Invoices",
      "description": "Search, filter, and summarize invoices by status, date, company" },
    { "id": "create-invoice", "name": "Create Invoice",
      "description": "Create a new invoice from a purchase order" },
    { "id": "approve-invoice", "name": "Approve Invoice",
      "description": "Approve or reject pending invoices" }
  ],
  "authentication": { "schemes": ["none"] }
}
```

Orchestrator agent 在启动时通过 Cloud Map DNS (`*.agents.local`) 读取所有 AgentCard，用于将用户意图路由到正确的智能体。

### A2A 任务格式

```
Orchestrator → Agent:
  POST http://invoice-agent.agents.local:8080/a2a
  {
    "jsonrpc": "2.0", "method": "tasks/send", "id": "req-001",
    "params": {
      "id": "task-456",
      "message": {
        "role": "user",
        "parts": [{"type": "text", "text": "Show pending invoices for company X"}]
      },
      "metadata": {
        "user_jwt": "<jwt>", "user_id": "uuid-abc", "company_uuid": "uuid-xyz",
        "roles": "ENTITY_ADMIN", "authorities": "INVOICE:read INVOICE:write INVOICE:approve"
      }
    }
  }

Agent → Orchestrator:
  {
    "jsonrpc": "2.0", "id": "req-001",
    "result": {
      "id": "task-456", "status": {"state": "completed"},
      "artifacts": [{
        "parts": [{"type": "text", "text": "Found 5 pending invoices for Company X:\n1. INV-2026-001 - $12,500\n..."}]
      }]
    }
  }
```

---

## LLM 集成 — AWS Bedrock

### 为什么选择 Bedrock

| 优势 | 细节 |
|---------|--------|
| 无需 GPU 基础设施 | 完全托管，按 token 计费 |
| IAM 原生认证 | ECS 任务角色获取 `bedrock:InvokeModel` 权限 — 无需轮转 API Key |
| VPC 端点 | LLM 调用保持在 AWS 网络内，无互联网出站 |
| 模型选择 | Claude 3.5 Sonnet（推理）、Claude 3 Haiku（快速分类）、Titan Embeddings v2（RAG） |
| 延迟 | ECS 任务到 Bedrock <50ms（同区域） |

### 各智能体的模型使用

| 智能体 | 模型 | 用途 |
|-------|-------|---------|
| Orchestrator | Claude 3 Haiku | 意图分类、路由（快速、廉价） |
| Orchestrator | Claude 3.5 Sonnet | 复杂多步规划 |
| Service Agents | Claude 3.5 Sonnet | 数据摘要、文档分析 |
| Embedding Pipeline | Titan Embeddings v2 | 文档转向量用于 Pinecone |

### 集成模式

```python
import boto3, json

bedrock = boto3.client("bedrock-runtime", region_name="ap-southeast-1")

# Standard invocation
def invoke_llm(prompt: str, model: str = "anthropic.claude-3-5-sonnet-20241022-v2:0") -> str:
    response = bedrock.invoke_model(
        modelId=model, contentType="application/json", accept="application/json",
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}]
        })
    )
    return json.loads(response["body"].read())["content"][0]["text"]

# Streaming (real-time token delivery to chat UI)
def invoke_llm_stream(prompt: str):
    response = bedrock.invoke_model_with_response_stream(
        modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31", "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}], "stream": True
        })
    )
    for event in response["body"]:
        chunk = json.loads(event["chunk"]["bytes"])
        if chunk["type"] == "content_block_delta":
            yield chunk["delta"]["text"]
```

### IAM 策略（ECS 任务角色）

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
    "Resource": [
      "arn:aws:bedrock:ap-southeast-1::foundation-model/anthropic.claude-3-5-sonnet-*",
      "arn:aws:bedrock:ap-southeast-1::foundation-model/anthropic.claude-3-haiku-*",
      "arn:aws:bedrock:ap-southeast-1::foundation-model/amazon.titan-embed-text-v2*"
    ]
  }]
}
```

### VPC 端点

```
ECS Task → VPC Endpoint (com.amazonaws.ap-southeast-1.bedrock-runtime) → Bedrock API
Traffic stays within AWS backbone. No NAT Gateway needed for LLM calls.
```

---

## RAG — Pinecone 向量数据库

### 为什么选择 Pinecone

| 优势 | 细节 |
|---------|--------|
| 托管无服务器 | 无基础设施，自动扩展 |
| 低延迟 | 相似度搜索 <50ms |
| 元数据过滤 | 支持按 `company_uuid` 过滤 — RAG 的 RBAC 关键 |
| Python 原生 | `pinecone-client` 与 LangChain/LangGraph 集成 |

### 嵌入内容

| 来源 | 切片方式 | 元数据过滤 |
|--------|----------|-----------------|
| 发票 PDF | 512 token，重叠 | companyUuid, invoiceStatus |
| 采购订单 | 512 token，重叠 | companyUuid, poStatus |
| 合同 | 1024 token（更长上下文） | companyUuid, contractId |
| 公司政策 | 1024 token | companyUuid, policyType |
| 帮助文档 | 512 token | global（无公司过滤） |

### 嵌入管道

```
Document Upload (via existing media service)
    │
    ▼
Embedding Worker (ECS task, triggered by SQS)
    ├── 1. Fetch document from S3
    ├── 2. Extract text (PyPDF2/python-docx)
    ├── 3. Chunk (LangChain RecursiveCharacterTextSplitter)
    ├── 4. Embed via Bedrock Titan Embeddings v2 (1024 dimensions)
    └── 5. Upsert to Pinecone with company_uuid metadata
```

### RAG 查询流程

```python
def rag_query(query: str, company_uuid: str, doc_type: str = None) -> str:
    # 1. Embed query via Bedrock Titan
    query_embedding = get_embedding(query)

    # 2. Search Pinecone WITH company filter (RBAC enforcement)
    filter_dict = {"company_uuid": {"$eq": company_uuid}}
    if doc_type:
        filter_dict["doc_type"] = {"$eq": doc_type}

    results = index.query(
        vector=query_embedding, top_k=5,
        include_metadata=True, filter=filter_dict   # ← only this company's documents
    )

    # 3. Build context + call Bedrock
    context = "\n\n".join([m["metadata"]["chunk_text"] for m in results["matches"]])
    return invoke_llm(f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer based only on context.")
```

---

## 向量 RBAC（公司级隔离）

```
CRITICAL: Every vector in Pinecone includes company_uuid in metadata.
Every query MUST filter by the user's company_uuid.

  ✓ Company A's documents are NEVER returned for Company B's users
  ✓ Even if an agent has a bug, Pinecone metadata filter prevents data leakage
  ✓ Combined with Layer 7 (DoxaAuthenticationManager) in downstream services

Security chain:
  1. Orchestrator verifies user belongs to company (JWT companies[] claim)
  2. Agent passes company_uuid to Pinecone filter
  3. Pinecone returns ONLY that company's chunks
  4. If agent also calls service APIs, JWT RBAC enforces again
```
```

### 索引配置

```
Index:         doxa-agents
Metric:        cosine
Dimensions:    1024 (Titan Embeddings v2)
Cloud/Region:  AWS / us-east-1 (Pinecone serverless)
Namespaces:    invoices, contracts, purchasing, policies, help-docs
```

---

## 数据存储 — Aurora PostgreSQL Serverless v2

### 为什么选 PostgreSQL（而不是 DynamoDB）

| 因素 | Aurora PostgreSQL（选择） | DynamoDB |
|--------|--------------------------|----------|
| LangGraph 检查点 | **原生支持**（`langgraph-checkpoint-postgres`） | 社区维护，不够成熟 |
| 团队经验 | **相同引擎**，已有经验 | 新的运维知识 |
| 智能体状态 | **ACID 事务** — 无部分写入损坏 | 最终一致 |
| 聊天历史查询 | **丰富 SQL** — join、聚合、全文搜索 | GSI 限制 |
| 分析 | 直接 SQL 查询 | 需要导出 Athena |
| 成本 | ~$58-80/月（0.5 ACU 最低 + RDS Proxy） | ~$5-25/月 |

### 模式

```sql
-- Database: doxa_agents (Aurora PostgreSQL Serverless v2)
-- Accessed via RDS Proxy from ECS tasks

-- Connection tracking
CREATE TABLE chat_connections (
    connection_id   VARCHAR(128) PRIMARY KEY,
    user_id         UUID NOT NULL,
    user_name       VARCHAR(255) NOT NULL,
    companies       JSONB NOT NULL,                -- CompanyJWT claims array
    roles           VARCHAR(512) NOT NULL,
    user_jwt        TEXT NOT NULL,                  -- updated on refresh
    connected_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_active_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_connections_user ON chat_connections (user_id);

-- Chat messages
CREATE TABLE chat_messages (
    id              BIGSERIAL PRIMARY KEY,
    conversation_id VARCHAR(64) NOT NULL,
    user_id         UUID NOT NULL,
    role            VARCHAR(16) NOT NULL,           -- 'user' or 'agent'
    content         TEXT NOT NULL,
    agent_name      VARCHAR(64),
    company_uuid    UUID,
    task_id         VARCHAR(64),                    -- A2A task ID for tracing
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_messages_conversation ON chat_messages (conversation_id, created_at);
CREATE INDEX idx_messages_user ON chat_messages (user_id, created_at);

-- Conversations metadata
CREATE TABLE conversations (
    conversation_id VARCHAR(64) PRIMARY KEY,
    user_id         UUID NOT NULL,
    company_uuid    UUID,
    title           VARCHAR(512),                   -- LLM-generated summary
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_conversations_user ON conversations (user_id, updated_at DESC);

-- LangGraph checkpointer tables (auto-created by langgraph-checkpoint-postgres):
--   checkpoints, checkpoint_writes, checkpoint_migrations
-- Usage:
--   from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
--   async with AsyncPostgresSaver.from_conn_string(DATABASE_URL) as checkpointer:
--       await checkpointer.setup()
--       graph = workflow.compile(checkpointer=checkpointer)
```

---

## 基础设施组件

### 新增 AWS 资源

> 有关成本预估，请参阅 [INFRASTRUCTURE_COSTS.md](INFRASTRUCTURE_COSTS.md)。

| 资源 | 目的 |
|----------|--------|
| API Gateway WebSocket API | 持有客户端 WebSocket 连接 |
| Lambda（授权器） | 仅在 `$connect` 层验证 JWT |
| VPC Link | API GW → ECS 的私有连通性 |
| 内部 NLB（智能体入口） | 将流量从 VPC Link 路由到 ECS orchestrator |
| 内部 NLB（服务入口） | 将 ECS 智能体流量路由到 Zuul Gateway |
| ECS 集群（Fargate） | 运行所有 Python 智能体任务 |
| Cloud Map 命名空间 | 智能体发现 DNS (`*.agents.local`) |
| Aurora PostgreSQL Serverless v2 | 检查点、连接和聊天历史 |
| RDS Proxy | ECS → Aurora 的连接池 |
| AWS Bedrock（Claude + Titan） | LLM 推理 + 嵌入 |
| Pinecone（Serverless） | RAG 文档块的向量数据库 |
| VPC Endpoint | 私有访问 Bedrock，免互联网出站 |
| Route 53 私有托管区域 | `api-internal.doxa-holdings.com` 的内部 NLB DNS |
| ECR 仓库 | 智能体容器镜像 |
| CloudWatch Logs | 智能体日志 |

### 现有资源 — 新增内容

| 现有资源 | 变更 | 风险 |
|------------------|--------|------|
| EKS 集群 | 一个新的 K8s Service（`zuul-gateway-internal`） | **无** — 追加，使用相同 pod selector |
| EKS Worker SG | 新增一条入站规则（来自内部 NLB 的 8080） | **最小** — 仅限一个来源 |
| 其他所有 | **无变更** | **零** |

### ECS 任务定义

| 智能体 | vCPU | 内存 | 最少任务数 | 最多任务数 | 缩放指标 |
|-------|------|--------|-----------|-----------|---------------|
| Orchestrator | 1.0 | 2 GB | 2 | 10 | 活跃连接数 |
| Invoice Agent | 0.5 | 1 GB | 1 | 5 | A2A 任务队列深度 |
| Entity Agent | 0.5 | 1 GB | 1 | 5 | A2A 任务队列深度 |
| Purchasing Agent | 0.5 | 1 GB | 1 | 5 | A2A 任务队列深度 |
| Payment Agent | 0.5 | 1 GB | 1 | 5 | A2A 任务队列深度 |

---

## 网络安全

```
Security Groups:

  sg-apigw-vpclink:
    Inbound:  443 from API Gateway managed IPs
    Outbound: 8080 to sg-orchestrator

  sg-orchestrator:
    Inbound:  8080 from sg-apigw-vpclink
    Outbound: 8080 to sg-service-agents (A2A calls)
    Outbound: 80   to sg-internal-nlb-zuul (service calls via internal NLB)
    Outbound: 443  to execute-api.amazonaws.com (Management API push to client)
    Outbound: 443  to VPC Endpoint (bedrock-runtime)
    Outbound: 443  to api.pinecone.io (via NAT Gateway)
    Outbound: 5432 to sg-aurora (PostgreSQL via RDS Proxy)

  sg-service-agents:
    Inbound:  8080 from sg-orchestrator only
    Outbound: 80   to sg-internal-nlb-zuul (service calls via internal NLB)
    Outbound: 443  to VPC Endpoint (bedrock-runtime)
    Outbound: 443  to api.pinecone.io (via NAT Gateway)
    Outbound: 5432 to sg-aurora (PostgreSQL via RDS Proxy)

  sg-internal-nlb-zuul (NEW):
    Inbound:  80 from sg-orchestrator and sg-service-agents only
    Outbound: 8080 to EKS worker nodes (Zuul Gateway pods)

  sg-eks-workers (EXISTING — one rule added):
    Inbound:  8080 from sg-internal-nlb-zuul    ← ONLY NEW RULE
    (all other existing rules unchanged)

  sg-aurora (NEW):
    Inbound:  5432 from sg-orchestrator and sg-service-agents only
    Outbound: none

  No agent is directly accessible from the internet.
  Agent traffic to services stays entirely within the VPC.
```

---

## 为何选择此架构 — 考虑的备选方案

### WebSocket：API Gateway vs NGINX Ingress

| 因素 | API Gateway（选择） | NGINX Ingress |
|--------|---------------------|-----------------|
| 任务/Pod 重启丢失连接 | **否** | 是 |
| 与现有流量共享资源 | **否** | 是 |
| 生产风险 | **零** | 中等 |

### 智能体到服务：内部 VPC vs 公网

| 因素 | 内部 NLB（选择） | 公网 |
|--------|----------------------|-----------------|
| 延迟 | **~2-5ms** | 50-100ms |
| NAT 成本 | **$0** | ~$0.045/GB |
| 攻击面 | **零** | 暴露 |
| 认证执行 | **6 of 7 layers**（NGINX 跳过 — 无认证） | 7 层 |

### 存储：Aurora PostgreSQL vs DynamoDB

| 因素 | Aurora PostgreSQL（选择） | DynamoDB |
|--------|--------------------------|----------|
| LangGraph 检查点 | **原生** | 社区 |
| 团队经验 | **相同引擎** | 新技术 |
| ACID | **是** | 最终一致 |
| SQL 查询 | **是** | GSI 限制 |

### 智能体运行时：ECS Fargate vs EKS Node Groups

| 因素 | ECS Fargate（选择） | EKS Node Groups |
|--------|---------------------|-----------------|
| 语言 | **Python** | Java/混合 |
| 空闲成本 | **$0**（可缩容到 0） | EC2 24/7 |
| 影响范围 | **隔离** 每个任务 | 共享节点 |
| 部署 | **独立** 管道 | 与服务耦合 |

### 热路径：HTTP 集成 vs Lambda

| 因素 | HTTP → ECS（选择） | Lambda 每条消息 |
|--------|---------------------|-------------------|
| 冷启动 | **无** | 200-500ms |
| 流式传输 | **直接** | 每块 Management API |
| A2A 支持 | **原生** | 每次调用引导 |

---

## 部署管道

```
Agent Code (Python) → GitHub → CI/CD Pipeline
                                    │
                          ┌─────────▼─────────┐
                          │  Build & Test      │
                          │  pytest + lint     │
                          └─────────┬─────────┘
                                    │
                          ┌─────────▼─────────┐
                          │  Docker Build      │
                          │  Push to ECR       │
                          └─────────┬─────────┘
                                    │
                          ┌─────────▼─────────┐
                          │  Update ECS Task   │
                          │  Definition        │
                          │  Rolling Update    │
                          └─────────┬─────────┘
                                    │
                          ┌─────────▼─────────┐
                          │  Health Check      │
                          │  passes → done     │
                          │  fails → rollback  │
                          └───────────────────┘

Existing services: Completely untouched. No rebuild, no redeploy.
```

---

## 可观察性

### 跟踪（端到端）

```
Client message → API GW (requestId=R1, connectionId=abc123)
  → Orchestrator (taskId=T1, agent=invoice-agent)
    → Invoice agent (taskId=T1, serviceCall=GET /invoice/api/invoices)
      → Invoice service (traceId from header, userId from JWT)
```

### 指标

| 类别 | 指标 |
|----------|---------|
| WebSocket | 活跃连接数、消息吞吐量 |
| 智能体 | A2A 任务延迟、各智能体错误率 |
| 服务 | 智能体 → Zuul → 服务 调用延迟 |
| LLM | Bedrock 调用延迟、token 使用、限流错误 |
| RAG | Pinecone 查询延迟、结果数量 |
| 数据库 | RDS Proxy 池使用率、Aurora ACU 使用、检查点写入延迟 |

### 警报

| 警报 | 触发条件 |
|-------|---------|
| 聊天过载 | WebSocket 连接数超过阈值 |
| 智能体失败 | A2A 错误率 > 5% |
| 认证风暴 | 服务调用 401 率飙升 |
| LLM 限流 | Bedrock 限流率 > 0 |
| RAG 性能下降 | Pinecone 查询延迟 > 200ms |
| 数据库压力 | Aurora ACU > 80% 最大值，RDS Proxy 池耗尽 |
| 稳定性 | ECS 任务崩溃/重启循环 |

---

## 实施阶段

### 阶段 1：基础（第 1-2 周）
- 预置 API Gateway WebSocket API + Lambda 授权器
- 设置 ECS Fargate 集群 + Cloud Map 命名空间
- 部署 `zuul-gateway-internal` K8s Service + 内部 NLB + Route 53 私有区
- 预置 Aurora PostgreSQL Serverless v2 + RDS Proxy
- 运行 LangGraph 检查点迁移
- 启用 AWS Bedrock 模型访问 + 创建 VPC 端点
- 构建 orchestrator agent 骨架（connect / message / disconnect）
- 前端 WebSocket 客户端，实现 ping 和自动重连

### 阶段 2：首个智能体 + RAG（第 3-4 周）
- 构建发票智能体，支持 A2A 协议
- 实现内部 VPC 服务调用的 JWT 透传
- 智能体 Card 发布与发现
- 设置 Pinecone 索引及元数据模式
- 构建嵌入管道（文档 → 切片 → Bedrock Titan → Pinecone）
- 端到端流程：用户 → 聊天 → 发票智能体 → 发票服务 → 响应
- 端到端 RAG 流程：用户问题 → Pinecone → Bedrock → 响应

### 阶段 3：新增智能体（第 5-6 周）
- 实体智能体、采购智能体、付款智能体
- Orchestrator 通过 Bedrock Claude Haiku 进行意图分类
- 多智能体任务编排（跨多个服务查询）
- 扩展 Pinecone 语料库（合同、采购订单、公司政策）

### 阶段 4：生产硬化（第 7-8 周）
- 令牌刷新流（对用户透明）
- 会话历史与恢复（LangGraph 检查点重放）
- 限流与滥用防护
- Bedrock 使用预算和限流警报
- Pinecone RBAC 审计（验证所有查询按 `company_uuid` 过滤）
- 完整可观察性与警报设置
- 压力测试
- 安全评审

---

## 关键文件参考（现有系统）

| 组件 | 文件 |
|-----------|------|
| OAuth2 安全配置 | `doxa-oauth2/.../config/oauth2/WebSecurityConfiguration.java` |
| JWT 生成 | `doxa-oauth2/.../serviceImpl/JsonWebTokenService.java` |
| JWT 密钥（RSA256） | `doxa-oauth2/.../components/JwtPki.java` |
| 令牌端点 | `doxa-oauth2/.../controllers/oauth2/TokenEndpoint.java` |
| 令牌检查 | `doxa-oauth2/.../controllers/oauth2/IntrospectionController.java` |
| RBAC 声明构建器 | `doxa-oauth2/.../serviceImpl/AuthorityService.java` |
| 认证管理器（声明读取） | `doxa-oauth2/.../common/DoxaAuthenticationManager.java` |
| 网关安全 | `doxa-connex-gateway/.../config/SecurityTokenConfig.java` |
| 网关 Zuul 过滤器 | `doxa-connex-gateway/.../config/DoxaZuulFilter.java` |
| 网关路由 | `doxa-connex-gateway/src/main/resources/application.properties` |
| 实体 JWT 配置 | `doxa-connex-entity/.../config/JWTSecurityConfig.java` |
| 活跃用户过滤器 | `doxa-connex-entity/.../config/CustomActiveUserFilter.java` |
| NGINX Ingress（开发） | `doxa-connex-gateway/deployment/gateway.ingress-development.yml` |
| NGINX Ingress（生产） | `doxa-connex-gateway/deployment/gateway.ingress-production.yml` |
