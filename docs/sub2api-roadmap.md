# ChatGPT Mirror 向 Sub2API 产品模型演进任务表

## 目标

把当前项目从“聊天镜像站”收敛为“站内用户体系 + 后台统一账号池 + 后续可接套餐/计费”的平台。

核心产品原则：

- 用户只负责注册、登录、使用
- 官方账号和中转站账号只在后台维护
- 前台用户不接触 Access Token、Session Token、Refresh Token
- 后续收费、配额、API Key 都建立在站内用户体系之上

## 当前仓库关键落点

- 后端用户与登录：
  - `backend/app/accounts/models.py`
  - `backend/app/accounts/serializers.py`
  - `backend/app/accounts/views/__init__.py`
  - `backend/app/accounts/views/login.py`
- 后端账号池与代理：
  - `backend/app/chatgpt/models.py`
  - `backend/app/chatgpt/serializers/__init__.py`
  - `backend/app/chatgpt/views/chatgpt.py`
  - `backend/app/chatgpt/views/gptcar.py`
  - `backend/app/chatgpt/views/proxy.py`
  - `backend/app/chatgpt/relay.py`
- 前端管理端：
  - `frontend/src/pages/account/user.vue`
  - `frontend/src/pages/account/chatgpt.vue`
  - `frontend/src/pages/account/gptcar.vue`
  - `frontend/src/router/modules/homepage.ts`
- 前端 C 端入口：
  - `frontend/src/pages/login/index.vue`
  - `frontend/src/utils/direct-chat.ts`

## P0

### P0-1 用户访问模型显式化

目标：

- 不再用 `gptcar_list = []` 隐式表示“公共池”
- 显式区分站点公共池、指定号池、专属账号三种模式

数据表：

- 扩展 `accounts.User`
  - `status`
  - `email_verified`
  - `pool_mode`
  - `plan_id`
  - `quota_snapshot`
- 新增 `UserPoolBinding`
  - `user`
  - `gptcar`

接口：

- 改造 `POST /0x/user/register`
- 改造 `POST /0x/user/login`
- 改造 `GET /0x/user/get-mirror-token`
- 改造 `POST /0x/user/relat-gptcar`
- 改造 `GET/POST /0x/user/`
- 新增 `GET /0x/user/me`

页面：

- 改造 `frontend/src/pages/account/user.vue`
- 后续新增 C 端账户页，消费 `/0x/user/me`

验收标准：

- 管理员能明确配置公共池或指定池用户
- 用户访问逻辑不再依赖空数组约定

### P0-2 上游账号注册表升级

目标：

- 官方账号和 relay 账号统一纳管
- 后台能配置模型支持、权重、优先级、并发、健康状态

数据表：

- 扩展 `chatgpt.ChatgptAccount`
  - `source_type`
  - `supported_models`
  - `priority`
  - `weight`
  - `health_status`
  - `max_concurrency`
  - `rpm_limit`
  - `tpm_limit`
  - `unit_cost`
  - `enabled_for_web`
  - `enabled_for_api`
- 扩展 `chatgpt.ChatgptCar`
  - `pool_type`
  - `enabled`
  - `remark_tags`

接口：

- 改造 `GET/POST/PUT/DELETE /0x/chatgpt/`
- 改造 `GET /0x/chatgpt/enum`
- 改造 `GET/POST /0x/chatgpt/car`
- 改造 `GET /0x/chatgpt/car-enum`

页面：

- 改造 `frontend/src/pages/account/chatgpt.vue`
- 改造 `frontend/src/pages/account/gptcar.vue`

### P0-3 统一调度器

目标：

- `get-mirror-token`、网页登录、API 代理共用同一套选路逻辑

数据表：

- 新增 `DispatcherDecisionLog`

接口：

- 统一收敛：
  - `GET /0x/user/get-mirror-token`
  - `POST /0x/chatgpt/login`
  - `POST /v1/chat/completions`

代码模块：

- 新增 `backend/app/chatgpt/dispatcher.py`

### P0-4 用量账本

目标：

- 为套餐、计费、风控打基础

数据表：

- 新增 `UsageLedger`
  - `user_id`
  - `account_id`
  - `model_name`
  - `request_type`
  - `prompt_tokens`
  - `completion_tokens`
  - `total_tokens`
  - `estimated_cost`
  - `status_code`
  - `error_code`
  - `created_at`

接口：

- 在 `POST /v1/chat/completions` 链路里落账
- 新增：
  - `GET /0x/user/usage-summary`
  - `GET /0x/system/usage-summary`
  - `GET /0x/system/usage-detail`

页面：

- 新增 `frontend/src/pages/system/usage.vue`

### P0-5 清理旧产品语义

目标：

- 去掉用户自带 Token、免费体验、用户手选底层账号这几条旧路径

接口：

- 默认关闭 `POST /0x/user/login-free`
- 保留 `POST /0x/chatgpt/login` 仅作内部兼容，不再作为主流程
- 清理删账号时按 `reg_` 号池删除用户的旧逻辑

页面：

- 登录页不出现任何 Token 获取说明
- 对外不再依赖邀请码注册逻辑

### P0-6 最小 C 端账户中心

目标：

- 用户登录后能看到自己的账号状态、到期时间、最近用量

接口：

- `GET /0x/user/me`
- `GET /0x/user/usage-summary`
- `GET /0x/user/session-summary`

页面：

- 新增 `frontend/src/pages/customer/home.vue`
- 新增 `frontend/src/pages/customer/account.vue`

## P1

### P1-1 套餐与配额引擎

数据表：

- `ServicePlan`
- `UserSubscription`
- `QuotaRule`

接口：

- `GET/POST/PUT /0x/plan/`
- `POST /0x/user/assign-plan`
- 套餐校验接入 `POST /v1/chat/completions`

页面：

- 新增 `frontend/src/pages/account/plan.vue`

### P1-2 账号健康检查和自动摘除

数据表：

- `AccountHealthLog`

接口：

- `POST /0x/chatgpt/health-check`
- `GET /0x/chatgpt/health-log`

页面：

- 扩展 `frontend/src/pages/account/chatgpt.vue`

### P1-3 粘性会话与并发控制

数据表：

- `SessionRouteBinding`

接口：

- 调度链路增加会话粘性和并发控制

页面：

- 新增或扩展系统流量页

### P1-4 邮箱验证与找回密码

数据表：

- `EmailVerificationCode`
- `PasswordResetToken`

接口：

- `POST /0x/user/send-email-code`
- `POST /0x/user/verify-email`
- `POST /0x/user/forgot-password`
- `POST /0x/user/reset-password`

页面：

- 扩展 `frontend/src/pages/login/index.vue`
- 新增 `frontend/src/pages/login/reset-password.vue`

### P1-5 运营看板

接口：

- `GET /0x/system/dashboard`
- `GET /0x/system/trend`
- `GET /0x/system/account-cost`

页面：

- 新增 `frontend/src/pages/system/dashboard.vue`

### P1-6 用户分组和批量运维

数据表：

- `UserGroup`
- `UserGroupBinding`

接口：

- `GET/POST /0x/user-group/`
- `POST /0x/user-group/assign-plan`
- `POST /0x/user-group/assign-pool`

页面：

- 新增 `frontend/src/pages/account/group.vue`

## P2

### P2-1 充值、订单、账本

数据表：

- `Wallet`
- `BalanceLedger`
- `Order`
- `PaymentRecord`
- `PlanPrice`

接口：

- `GET /0x/billing/me`
- `POST /0x/billing/create-order`
- `POST /0x/billing/webhook/*`
- `POST /0x/admin/billing/manual-adjust`

页面：

- 新增 `frontend/src/pages/customer/billing.vue`
- 新增 `frontend/src/pages/system/billing.vue`

### P2-2 API Key 产品线

数据表：

- `ApiKey`
- `ApiKeyScope`
- `ApiAccessLog`

接口：

- 扩展 `POST /v1/chat/completions`
- 新增 `GET/POST/DELETE /0x/api-key/`

页面：

- 新增 `frontend/src/pages/customer/api-keys.vue`

### P2-3 风控与审计

数据表：

- `AdminAuditLog`
- `RiskEvent`
- `LoginAttempt`

接口：

- `GET /0x/system/audit-log`
- `GET /0x/system/risk-events`

页面：

- 新增 `frontend/src/pages/system/audit.vue`

### P2-4 基础设施升级

目标：

- 数据库从 SQLite 迁移到 PostgreSQL
- 并发、限流、粘性会话迁移到 Redis

## 建议执行顺序

1. 先做 `P0-1`、`P0-2`、`P0-3`、`P0-5`
2. 再做 `P0-4` 和 `P1-1`
3. 然后做 `P1-2`、`P1-3`、`P1-4`、`P1-5`
4. 最后再做 `P2`

## 当前开始实施的范围

本轮先落：

- `P0-1 用户访问模型显式化`
- `GET /0x/user/me`
- 管理端用户页支持公共池 / 指定池
