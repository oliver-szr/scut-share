# 华园易享 · SCUT Share

创新思维与实践课程项目，面向华南理工大学学生的校园闲置物品二手交易与免费共享平台。

**让闲置物品流动起来，让校园互助自然发生。**

二手交易与免费借还是并列的核心业务。交易通过自主咨询、协商和线下交接完成；免费借还覆盖申请、协商交接、双方借出确认和双方归还确认。兴趣标签、站内文字聊天、免费转赠、挂牌价格参考与基础举报申诉已开放。初期面向班级熟人圈，不实现班级邀请码或独立社交系统。

## 当前范围

Phase 1 已实现注册、登录、退出、刷新恢复有效会话、个人信息查看、后端身份校验、数据库迁移和测试。Phase 2 已实现物品发布、编辑、下架、公开浏览、筛选搜索、详情、兴趣标签与本地图片上传。Phase 3 已实现二手购买意向、卖家接受/拒绝、商品预留、取消、双方成交确认与私有交易记录。Phase 4 已实现免费借用申请、物主审核、双方交接/归还确认、取消、重复借出和私有借还历史。Phase 5 已实现二手咨询、获同意借还聊天、私有会话列表、持久化文字消息、历史分页和当前会话轮询。Phase 6 已实现人工举报处理、一次复核申诉、免费转赠闭环和当前挂牌价格参考。Phase 7 完成首页入口、窄屏导航、状态提示和隔离演示数据脚本收束。保留 Phase 0 中文响应式首页及真实健康接口连接状态。

页面：`/`、`/register`、`/login`、`/profile`、`/items`、`/items/:id`、`/items/new`、`/my-items`、`/my-trades`、`/my-borrows`、`/messages`、`/my-gifts`、`/my-reports`、`/admin/reports`。个人中心、发布、我的发布、我的交易、我的借还及我的消息、我的转赠、举报记录要求登录，举报管理仅管理员可访问；服务器不可达时显示明确错误。

二手交易通过真实 API 记录状态，付款与交付在线下完成，平台不处理在线支付或资金托管。免费借还完全免费，无租金、押金或手续费；交接由双方自行协商，借出与归还都需要双方确认。站内文字聊天支持双方自主沟通，聊天不会改变交易/借还状态；举报申诉提供人工记录和复核，不自动处罚或改变历史业务状态。本阶段不支持资料修改、头像上传、密码修改、账号恢复或官方校园认证，不提供公开用户查询接口。

**学号由用户自行填写，仅作为内部登录账号，不代表通过学校统一身份认证。** 注册响应不包含学号，登录和个人接口只返回脱敏学号。

## 技术栈与依赖用途

| 依赖 | 已验证版本 | 用途 |
| --- | --- | --- |
| React / React DOM | 19.3.0 | 页面与组件 |
| React Router DOM | 7.18.4 | Phase 1 新增：注册、登录、个人中心及受保护路由 |
| Vite / React 插件 | 8.3.4 / 6.1.2 | 开发服务、热更新、生产构建 |
| TypeScript | 5.9.3 | 严格类型检查 |
| Tailwind CSS / Vite 插件 | 4.3.3 | 响应式样式与设计变量 |
| Vitest | 5.0.3 | 前端测试 |
| React Testing Library / jest-dom | 16.3.3 / 6.9.1 | 页面交互与语义断言 |
| jsdom | 27.0.1 | 测试 DOM 环境 |
| Python | 3.12.15 | Conda 环境 scut_share_env |
| FastAPI | 0.143.0 | REST API 与请求校验 |
| SQLAlchemy | 2.0.54 | SQLite Engine、Session 与 ORM |
| Alembic | 1.20.0 | Phase 1 新增：数据库版本迁移 |
| argon2-cffi | 25.1.0 | Phase 1 新增：Argon2id 密码哈希与验证 |
| Pydantic / pydantic-settings | 2.14.1 / 2.15.0 | API Schema 与集中配置 |
| Uvicorn | 0.54.0 | ASGI 服务 |
| pytest / HTTPX | 9.1.1 / 0.28.1 | 后端测试与 TestClient |
| Starlette | 0.52.1 | FastAPI 底层；维持 HTTPX 0.x TestClient 兼容范围 |

Node.js 24.13.0、npm 11.6.2。推荐 Node.js 24 LTS，支持范围见 frontend/package.json。Phase 1 没有无理由升级已有依赖。插画复用项目内 SVG，不使用外部字体或图片服务。

前端精确依赖树在 frontend/package-lock.json；后端 requirements.in 记录直接依赖范围，requirements.txt 锁定已验证完整环境。运行和测试依赖目前一起安装。

## 主要目录

```text
scut-share/
├── AGENTS.md / README.md / .gitignore
├── docs/
│   ├── phase0-verification.md / phase1-verification.md / phase2-verification.md / phase3-verification.md / phase4-verification.md / phase5-verification.md / phase6-verification.md / phase7-verification.md / demo-guide.md
│   └── phase0-*.jpg / phase1-*.jpg
├── frontend/
│   ├── .env.example
│   ├── package.json / package-lock.json
│   ├── tsconfig.json / vite.config.ts
│   └── src/
│       ├── main.tsx / App.tsx / AppRoutes.tsx
│       ├── App.test.tsx / styles.css
│       ├── api/{client,health,auth,items,trades,borrows,conversations,reports,gifts}.ts
│       ├── config/env.ts
│       ├── auth/{AuthContext,ProtectedRoute,Auth.test}.tsx
│       ├── auth/validation.ts
│       ├── pages/{RegisterPage,LoginPage,ProfilePage,ItemsPage,ItemDetailPage,ItemFormPage,MyItemsPage,MyTradesPage,MyBorrowsPage,MessagesPage,ReportsPage,MyGiftsPage}.tsx
│       ├── components/{SiteHeader,AuthLayout,ConnectionStatus,ShareIllustration,ItemCard,ItemForm,BorrowRequestForm,ContactButton,ReportButton,PriceReference}.tsx
│       └── test/setup.ts
└── backend/
    ├── .env.example
    ├── requirements.in / requirements.txt / pyproject.toml
    ├── alembic.ini
    ├── migrations/
    │   ├── env.py / script.py.mako
    │   └── versions/20261012_{01_users_and_sessions,02_items,03_trade_intents,04_borrow_requests,05_conversations,06_reports,07_gifts}.py
    ├── app/
    │   ├── main.py / application.py / admin_cli.py
    │   ├── api/{router,dependencies}.py
    │   ├── api/routes/{health,auth,items,trades,borrows,conversations,reports,gifts,prices}.py
    │   ├── core/{config,constants,security}.py
    │   ├── db/session.py
    │   ├── models/{user,auth_session,item,trade_intent,borrow_request,conversation,report,gift_request}.py
    │   └── schemas/{auth,item,trade,borrow,conversation,report,gift}.py
    └── tests/
        ├── conftest.py
        └── test_{health,database,config,auth,items,trades,borrows,conversations,phase6,migrations}.py
```

运行时的 backend/data/、.local/、测试临时文件、node_modules/、dist/ 和 .env 均不纳入 Git。

## Windows PowerShell 安装

使用已有 Conda 环境，不安装到 base。以下路径对应当前电脑；其他电脑请替换 Anaconda 路径。已初始化 Conda 的 PowerShell 可使用 `conda activate scut_share_env` 后运行 `python -m ...`，下方直接指定解释器以避免 PATH 歧义。

```powershell
Set-Location E:\homework\scut-share\backend
$ProjectPython = Join-Path $env:USERPROFILE 'anaconda3\envs\scut_share_env\python.exe'
& $ProjectPython --version
& $ProjectPython -m pip install -r requirements.txt --index-url https://pypi.org/simple
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
& $ProjectPython -m alembic upgrade head

Set-Location ..\frontend
npm.cmd ci --registry=https://registry.npmjs.org
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

其他电脑若尚无环境，先创建一次：

```powershell
$CondaPython = Join-Path $env:USERPROFILE 'anaconda3\python.exe'
& $CondaPython -m conda create --name scut_share_env python=3.12 pip --yes
```

索引参数仅影响本条命令，不修改全局配置。使用 npm.cmd 可避免 PowerShell 对 npm.ps1 的执行策略限制。

## 数据库迁移

正式应用不会自动建表、删除数据或重建数据库。首次启动和获取新迁移后，先运行：

```powershell
Set-Location E:\homework\scut-share\backend
$ProjectPython = Join-Path $env:USERPROFILE 'anaconda3\envs\scut_share_env\python.exe'
& $ProjectPython -m alembic upgrade head
& $ProjectPython -m alembic current
& $ProjectPython -m alembic check
```

当前 head 为 `20261012_07`。Phase 6 的 `20261012_06` 增加管理员字段及 reports/report_appeals，`20261012_07` 扩展 gift 模式并增加 gift_requests。SQLite 物品表约束通过迁移专用连接在事务中重建，避免外键级联删除，并检查迁移后外键完整性；API 连接继续启用外键。保留已有账号、物品、图片、交易、借还、会话及消息数据。重复升级到 head 保留数据。已有数据时先停止服务并备份 SQLite 文件；不要将 `downgrade base` 当作日常启动命令，它会删除表及数据。本次开发只迁移隔离验收库；启动现有开发库前需自行执行上述 upgrade 命令。

迁移复用集中数据库路径和 Engine 创建函数。应用启动只执行 SELECT 1，退出释放连接；健康接口表示应用可响应，不持续监控数据库或证明业务可用。

## 启动

打开两个 PowerShell 窗口。

后端：

```powershell
Set-Location E:\homework\scut-share\backend
$ProjectPython = Join-Path $env:USERPROFILE 'anaconda3\envs\scut_share_env\python.exe'
& $ProjectPython -m alembic upgrade head
& $ProjectPython -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

前端：

```powershell
Set-Location E:\homework\scut-share\frontend
npm.cmd run dev
```

- 首页：http://127.0.0.1:5173/
- 注册：http://127.0.0.1:5173/register
- 登录：http://127.0.0.1:5173/login
- 个人中心：http://127.0.0.1:5173/profile
- 我的交易：http://127.0.0.1:5173/my-trades
- 我的借还：http://127.0.0.1:5173/my-borrows
- 我的消息：http://127.0.0.1:5173/messages
- 我的转赠：http://127.0.0.1:5173/my-gifts
- 我的举报：http://127.0.0.1:5173/my-reports
- 举报管理：http://127.0.0.1:5173/admin/reports
- 健康接口：http://127.0.0.1:8000/api/health
- API 文档：http://127.0.0.1:8000/docs

**前后端必须使用同一主机名。** 默认都使用 127.0.0.1；不要用 localhost:5173 配合 127.0.0.1:8000，否则 SameSite Cookie 无法正确保持会话。若改用 localhost，需同时将 VITE_API_BASE_URL 改为 http://localhost:8000/api。

Vite 固定端口并启用 strictPort，端口占用时明确报错。两个服务只监听本机，Ctrl+C 停止。

## 课程演示数据

课程答辩可使用隔离演示库，不会修改 `backend/data/scut_share.db`：

```powershell
Set-Location E:\homework\scut-share\backend
$ProjectPython = Join-Path $env:USERPROFILE 'anaconda3\envs\scut_share_env\python.exe'
& $ProjectPython -m app.demo_seed --reset
```

演示账户、建议流程和重置方法见 [`docs/demo-guide.md`](docs/demo-guide.md)。演示脚本只允许在独立路径使用 `--reset`，不会代表官方校园身份认证。

## 用户模型、API 与字段规则

User 保存内部 id、nickname、student_no、password_hash、campus、is_admin（默认 false）、created_at、updated_at。学号有数据库唯一约束，校区有数据库 CHECK 约束。AuthSession 保存 token_hash、user_id、创建和过期时间，外键关联用户。ORM 与响应 Schema 分离。

| 字段 | 规则 |
| --- | --- |
| 昵称 | 必填，去首尾空格后 2～30 字符，允许重复 |
| 学号 | 必填，去首尾空格后 3～32 位 ASCII 字母、数字、下划线或连字符；区分大小写，不假设学校固定长度 |
| 校区 | 五山校区、大学城校区、广州国际校区 |
| 注册密码 | 8～128 字符，保留空格，不要求额外注册字段 |

所有规则均在后端验证，前端校验只用于提示。登录请求接受 1～128 字符密码，错误凭证统一返回相同的 401 文案。

| 方法与路径 | 行为 | 主要响应 |
| --- | --- | --- |
| GET `/api/health` | 应用健康检查 | 200 `{"status":"ok"}` |
| POST `/api/auth/register` | 创建用户，不自动登录 | 201 基本用户信息；重复学号 409；非法输入 422 |
| POST `/api/auth/login` | 验证凭证、设置会话 Cookie | 200 基本信息与脱敏学号；错误凭证 401 |
| POST `/api/auth/logout` | 撤销当前会话、清除 Cookie | 204 无正文，可重复调用 |
| GET `/api/auth/me` | 从当前会话确定用户，忽略外部用户 id | 200 当前用户信息；匿名或过期 401 |

基本用户响应为 id、nickname、campus、created_at；登录和 me 额外含 student_no_masked 和只读 is_admin；注册响应不含管理员角色。不返回完整学号、密码哈希或会话令牌。

错误格式为 `{"detail":"中文提示"}`；422 的 detail 为仅含 loc、msg、type 的校验列表，移除原始输入，避免回显密码。数据库异常返回通用 503，不输出 SQL 参数或堆栈。

## 认证与安全边界

- 密码使用 Argon2id：内存 64 MiB、time_cost=3、parallelism=4，每个密码有独立随机盐。未知账号也执行密码哈希验证，错误账号与密码返回相同信息。
- 会话令牌使用 32 随机字节，数据库仅存 SHA-256 哈希。默认绝对有效期 7 天，不滚动续期；同一浏览器再次登录会旋转并撤销旧令牌，退出立即撤销当前会话。不同浏览器的会话独立。
- Cookie 为 HttpOnly、SameSite=Lax、host-only、Path=/api，含 Max-Age 与 Expires。前端只通过 credentials: include 携带 Cookie，不读取令牌，不存入 localStorage。
- 所有认证 POST（包括注册和登录）必须携带与 CORS_ORIGINS 精确匹配的 Origin，缺失或不可信来源返回 403。CORS 使用明确来源和 credentials，不使用通配符。
- 前端统一由 AuthContext 恢复身份，页面切换不重复查询；私有请求 401 后清除身份并提示重新登录。网络失败显示重试；会话过期通过后续请求或刷新识别，认证本身没有后台轮询。
- APP_ENV=production 要求 Secure Cookie 与 HTTPS 来源，否则配置校验失败。当前来源配置仍限本地回环地址；远程部署需要另行设计 HTTPS、可信域名、代理及限流，不代表已经具备生产部署条件。

Swagger 文档在后端源打开，认证 POST 默认不满足前端 Origin 校验。请使用前端页面验证；CLI 调用需显式提供例如 Origin: http://127.0.0.1:5173 并使用会话 Cookie 容器。不要为 Swagger 放宽可信源。

## Phase 3 二手交易

`TradeIntent` 独立保存物品、买卖双方、提交时的分单位价格快照、最长 300 字备注、状态、双方确认时间、创建/更新时间及完成时间。买卖双方 ID 从会话和物品所有权确定；客户端不能指定身份。交易响应只向参与者提供，用户资料只有 ID 和昵称，不返回学号或认证信息。Phase 3 无新增依赖或依赖升级。

| 方法与路径 | 行为 |
| --- | --- |
| POST `/api/items/{id}/trade-intents` | 登录买家对他人的正常二手商品发起意向，可传 `{ "note": "备注" }` 或 `{}` |
| GET `/api/trades/mine` | 当前用户参与的交易；可用 `role=buyer/seller`，`page`，`page_size`（最多 50） |
| POST `/api/trades/{id}/accept` | 卖家接受待处理申请，并原子拒绝同商品其余待处理申请 |
| POST `/api/trades/{id}/reject` | 卖家拒绝待处理申请 |
| POST `/api/trades/{id}/cancel` | 买家取消待处理申请；双方均未确认时任一参与方可取消预留 |
| POST `/api/trades/{id}/confirm` | 当前参与方确认；双方都确认才成交，重复确认保留原时间 |

所有交易 POST 继续要求可信 Origin 和有效 Cookie；匿名 401、不可信来源 403、非参与者 404、角色不符 403、状态冲突 409。交易状态为 `pending → reserved → completed`，待处理也可变为 `rejected/canceled`，未确认的预留可变为 `canceled`。已有一方确认后，不能单方面取消。

商品的 `status` 仍只有 published/withdrawn；新增响应字段 `availability`（available/reserved/sold/unavailable）由交易记录和下架状态计算。已预留、已售出物品仍可公开浏览并标明状态，不能再次申请购买。同一买家同商品只允许一个待处理或预留申请，同一商品只允许一个预留或完成交易。SQLite 的 BEGIN IMMEDIATE 在读取状态之前获取写锁，交易变化与危险商品编辑共享该锁；两个部分唯一索引提供数据库兜底。

有待处理、预留或完成交易时，禁止改价、切换模式和下架；允许描述等非价格资料编辑及价格不变的保存。卖家处理完所有有效申请后可修改；已成交商品保持不可交易。取消或拒绝后的历史价格快照也不会被后续编辑改变。

手动验收：卖家发布 sale 物品；另一账号进入详情点击“我想购买”；卖家在 `/my-trades` 的“我卖出的”接受；线下完成沟通、付款和交付后，双方各自在交易页确认。第一方确认后仍显示预留，第二方确认后显示成交时间，详情显示“已售出”。免费借还不支持购买申请。

## Phase 4 免费借还

新增独立 `BorrowRequest`，与 TradeIntent 分别管理状态。只允许 borrow 模式物品，无任何收费字段，也拒绝额外收费或伪造身份输入。保存计划开始/归还时间、备注、双方交接/归还确认时间、实际借出确认时间和完成时间。请求时间必须带时区，后端转换为 UTC；归还时间必须晚于开始时间；前端按用户本地时间填写和展示。

| 方法与路径 | 行为 |
| --- | --- |
| POST `/api/items/{id}/borrow-requests` | 登录用户申请借用他人的可借物品；必填 requested_start_at、expected_return_at，note 可选 |
| GET `/api/borrows/mine` | 参与者私有借还记录；支持 role=borrower/owner 和分页（page_size 最多 50） |
| POST `/api/borrows/{id}/approve` | 物主同意并在同一事务拒绝同物品其他待处理申请 |
| POST `/api/borrows/{id}/reject` | 物主拒绝待处理申请 |
| POST `/api/borrows/{id}/cancel` | 借用人取消待处理申请，或任一参与方取消双方均未确认交接的申请 |
| POST `/api/borrows/{id}/confirm-handover` | 当前参与方确认已交出/收到物品，双方确认后 borrowed |
| POST `/api/borrows/{id}/confirm-return` | 当前参与方确认归还，单方为 return_pending，双方后 completed |

状态为 `pending → approved → borrowed → return_pending → completed`，另有 rejected/canceled。第一方交接确认后仍 approved，已有交接确认时不允许单方取消；borrowed/return_pending 不允许直接取消。重复确认保留原时间。完成后物品恢复可借，历史记录保留，同一物品和同一用户均可以再次借用。

所有写接口继续要求可信 Origin、Cookie 和参与者身份；不返回学号或认证数据。复用 BEGIN IMMEDIATE，并用部分唯一索引限制同物品最多一笔 approved/borrowed/return_pending，以及同用户同物品最多一笔未结束有效申请；completed 不在唯一限制中。存在 pending 或有效借用时禁止切换方式和下架，非关键描述/标签可编辑。

borrow 物品的 availability 为 available（可借）、reserved（待交接）、borrowed（借用中）、return_pending（待双方确认归还）、unavailable（下架）。sale 原有状态规则保持一致。`/my-borrows` 提供“我借入的”“我借出的”，显示计划时间、角色操作、双方进度和历史完成时间；借用中及归还确认中的超期记录显示“已逾期”，提示不改变业务状态。不实现日历匹配、自动处罚、强制归还、定时通知或信用评分。Phase 4 无新增依赖或升级。

手动验收：物主发布 borrow 物品，另一账号在详情打开申请表单；物主在“我借出的”同意，然后双方可在借还记录点击“联系对方”协商。线下交接后双方分别确认收到/交出，变为借用中；线下归还后双方分别确认归还/收到归还，物品恢复可借。在详情再次申请可开启下一次借用。

## Phase 5 站内文字聊天

`Conversation` 保存上下文、物品、可选借还记录、物主/卖家和借用人/买家的 ID、创建/更新时间；`Message` 保存会话、服务端确定的发送者、文字和 UTC 时间。sale_item 会话按商品及双方复用，borrow_request 会话按具体申请复用；同一物品不同买家的消息隔离，同一双方再次借用会创建新申请对应的会话。数据库部分唯一索引和 SQLite BEGIN IMMEDIATE 共同防止重复创建。Phase 5 无新增依赖或升级。

| 方法与路径 | 行为 |
| --- | --- |
| POST `/api/items/{id}/conversations` | 非物主咨询正常可交易的 sale 商品，无需购买意向；已有双方会话直接复用 |
| POST `/api/trades/{id}/conversation` | 依据参与者交易记录联系正确的买家/卖家，复用商品咨询；待处理或有效预留可创建 |
| POST `/api/borrows/{id}/conversation` | 借还参与者在 approved/borrowed/return_pending/completed 阶段创建或复用会话 |
| GET `/api/conversations` | 当前用户的会话、物品摘要、对方昵称、最近消息摘要/时间；page/page_size，最多 50 项 |
| GET `/api/conversations/{id}` | 参与者读取会话详情，支持直接链接 |
| GET `/api/conversations/{id}/messages` | 参与者读取稳定 ID 顺序的消息；limit 最多 50，before_id 加载更早历史，after_id 获取新消息 |
| POST `/api/conversations/{id}/messages` | 仅传 `{ "content": "文字" }`；保存并返回 201，新消息发送者来自登录用户 |

所有接口验证登录和参与者权限，所有 POST 保留可信 Origin；客户端不能指定参与者或发送者。消息去首尾空白后为 1～1000 字，额外字段拒绝；只按普通文字保存/展示，不渲染 HTML。响应不返回学号、密码哈希或认证会话信息。未登录 401、不可信来源 403、非参与者/不存在 404、业务冲突 409、非法输入 422。

售出、下架、预留商品不接受新的陌生买家咨询；已有会话继续保留并可读写。交易记录可为有效预留的实际双方建立会话，已完成且没有历史会话时返回明确 409。借还 pending/rejected 不开放聊天；已批准后取消的会话历史仍能从“我的消息”访问，但取消记录不再新建会话。聊天不会自动改变任何交易或借还状态。

`/messages` 桌面左右布局，手机先列表再详情。商品详情、交易/借还记录、首页、导航和个人中心均已接入。当前会话约每 8 秒增量读取，消息按 ID 去重；发送成功立即显示，旧历史分页加载。切换/离开会话取消旧请求，隐藏页面暂停轮询，网络失败暂停自动更新并提供手动重载，不无限重试。其他会话摘要通过“刷新列表”更新；暂不提供未读数、已读回执、撤回、附件、群聊或推送。

手动验收：卖家发布 sale 商品；买家无需申请购买即可点击“联系卖家”，双方各发一条消息；刷新或重新打开“我的消息”可读历史。用第三账号访问该会话应被拒绝。borrow 场景先提交申请并由物主同意，再从“我的借还”进入聊天。

## Phase 6 举报申诉、免费转赠与挂牌参考

举报支持 item、trade、borrow、message，交易/借还/消息必须是参与者，公开物品或物主自己的物品可以举报。Report 保存原因、描述、对象 ID、提交时的有限证据快照和处理结果；ReportAppeal 每份举报只能一条，处理后由举报人申请复核。管理员记录 handled（已处理）或 dismissed（不予处理），复核结果另存并保留初次结论，不自动修改交易/借还状态或处罚用户。

| 方法与路径 | 行为 |
| --- | --- |
| POST `/api/reports` | 提交 target_type、target_id、reason（1～100 字）、description（1～2000 字），服务端验证对象查看权限 |
| GET `/api/reports/mine` | 当前举报人的分页列表 |
| GET `/api/reports/{id}` | 举报人查看详情及结果 |
| POST `/api/reports/{id}/appeal` | 处理后提交一次 reason（1～1000 字） |
| GET `/api/admin/reports` | 管理员分页列表，status 筛选、appeal_pending=true 待复核筛选 |
| GET `/api/admin/reports/{id}` | 管理员查看该举报的有限证据 |
| POST `/api/admin/reports/{id}/resolve` | 管理员提交 status=handled/dismissed、note（1～1000 字） |
| POST `/api/admin/reports/{id}/appeal-review` | 管理员记录单次复核结果，原处理结论保留 |
| POST `/api/items/{id}/gift-requests` | 对他人的可领取 gift 物品提交申请，note 可选，最多 300 字 |
| GET `/api/gifts/mine` | 参与者转赠记录，role=owner/recipient 和分页 |
| POST `/api/gifts/{id}/{approve,reject,cancel,confirm}` | 物主审核、参与者按状态取消/分别确认交付与领取 |
| GET `/api/items/{id}/price-reference` | 公开的 sale 商品当前挂牌参考，same_campus=true 可仅同校区 |

所有写接口继续要求可信 Origin 和 Cookie。管理员权限由后端逐次验证；注册不能设置 is_admin，没有 HTTP 授权角色接口。管理员也不能访问不参与的聊天或提交别人的私信举报；只可通过具体举报查看举报人有权访问、选中的**一条消息**快照。列表不返回消息证据，详情不查询整段聊天。

本地授权必须由开发者执行，先完成迁移并确认内部用户 ID；不根据自填学号自动授权。以下命令不会在日常启动时自动运行：

```powershell
Set-Location E:\homework\scut-share\backend
$ProjectPython = Join-Path $env:USERPROFILE 'anaconda3\envs\scut_share_env\python.exe'
$AdminUserId = [int](Read-Host '输入已确认的内部用户 ID')
& $ProjectPython -m app.admin_cli --user-id $AdminUserId
# 撤销同一用户：
& $ProjectPython -m app.admin_cli --user-id $AdminUserId --revoke
```

CLI 默认使用项目配置的已有数据库，可用 --database 显式指定已有隔离库。授权后刷新页面恢复账号信息，即可看到个人中心的“举报管理”。撤销权限在下一次后端请求立即生效，不依赖前端是否仍显示页面。本次只为隔离验收用户授权/撤销，开发库管理员角色未改动。

免费转赠为独立 gift 模式，不是 0 元 sale；价格和借用说明均为空，额外费用字段拒绝。GiftRequest 状态 `pending → approved → completed`，另有 rejected/canceled。物主同意后自动拒绝其余待处理申请；双方分别确认交付/领取后完成并记录时间，availability 为 gifted（已赠送）。单方确认仍 approved，不能直接取消；双方均未确认时任一方可取消，恢复可领取。重复确认不改变完成时间；同商品 approved/completed 唯一索引防止重复赠送，pending/approved 限制同领取人有效重复申请。有效或完成转赠禁止切换方式和下架，描述仍可编辑。

发布表单、广场筛选、卡片和详情支持免费转赠，`/my-gifts` 显示“我申请领取的”和“我赠出的”及状态操作。转赠暂通过申请备注和双方已有联系方式/线下协商，未扩展 Phase 5 聊天模型。

挂牌参考仅查询其他 published、sale、未预留/售出的同类别商品，标题使用英文词或连续两个汉字匹配，可限定同校区，最多列出最新 8 个样本。至少 3 个所列样本才显示其挂牌价范围，否则“参考数据不足”。无品牌、型号、成色结构化数据，不声称完全可比；不查询或推断成交价、不爬取外部平台、不进行 AI 估价。界面固定说明：“仅供参考，展示的是当前挂牌价，不代表实际成交价或公允价格。”

本阶段没有新增依赖或升级。一次集中检查：前端 58/58、typecheck/build 通过；后端首次全量 118/119，通过更新旧 gift 非法模式断言并定向复验后全部 119 项已验证通过，未再运行全量。隔离库 Alembic check 及真实 HTTP 举报/复核、CLI 授权撤销、有限私信证据、双人转赠、挂牌样本验证通过。详情见 [Phase 6 验收记录](docs/phase6-verification.md)。开发数据库及上传文件 SHA-256 前后不变，未自动执行开发库迁移。

## 环境变量

默认配置可直接运行。后端从 backend/.env 读取，进程环境变量优先；前端由 Vite 读取 frontend/.env。修改后重启对应服务。

| 位置 | 变量 | 默认值 | 说明 |
| --- | --- | --- | --- |
| backend | DATABASE_PATH | data/scut_share.db | 相对路径以 backend/ 为基准，也支持绝对路径 |
| backend | CORS_ORIGINS | ["http://127.0.0.1:5173","http://localhost:5173"] | 精确本地源的 JSON 数组，无通配符或路径 |
| backend | APP_ENV | development | development / production |
| backend | SESSION_COOKIE_SECURE | false | 仅本地 HTTP 使用 false；production 必须 true |
| backend | SESSION_COOKIE_NAME | scut_share_session | Cookie 名，修改后旧 Cookie 不再识别 |
| backend | SESSION_TTL_SECONDS | 604800 | 新会话有效期，60～2592000 秒，修改不改变现有会话 |
| frontend | VITE_API_BASE_URL | http://127.0.0.1:8000/api | 包含 /api，主机名与前端一致 |

VITE_* 会写入浏览器构建产物，不能放密码、令牌或服务端秘密。.env、SQLite、上传文件和构建产物均不提交。

## 测试与构建

后端：

```powershell
Set-Location E:\homework\scut-share\backend
$ProjectPython = Join-Path $env:USERPROFILE 'anaconda3\envs\scut_share_env\python.exe'
& $ProjectPython -m pytest -q --tb=short
& $ProjectPython -m pip check
```

前端：

```powershell
Set-Location E:\homework\scut-share\frontend
npm.cmd run test
npm.cmd run typecheck
npm.cmd run build
```

后端测试使用独立临时 SQLite 和注入的迁移连接，不读取本地 .env 或导入 app.main。backend/.pytest-tmp/ 是 pytest 专用目录，会被清理，勿保存用户文件。前端测试 mock API；实际浏览器验收使用真实 HTTP 后端和独立验收库。

交互式测试：npm.cmd run test:watch。构建预览：npm.cmd run preview，地址 http://127.0.0.1:4173/；需显式将该源加入后端 CORS_ORIGINS 后重启，API 服务也须运行。

Phase 6 验收：后端首次全量 118/119，修正旧 gift 非法参数断言后定向 2/2，通过用例总计 119；前端 58/58、typecheck、build、隔离库 Alembic check 通过，真实 HTTP 举报复核、CLI 角色授权撤销、免费转赠与挂牌参考通过。Phase 7 完成首页发布入口、窄屏导航收束、下架借还状态提示和隔离演示数据脚本；本阶段前端 58/58、typecheck、build 通过，后端 pytest 受当前 Windows 沙箱临时目录阻塞未记为通过，开发库仍在 `20261012_02`，未自动迁移。记录：[Phase 0](docs/phase0-verification.md)、[Phase 1](docs/phase1-verification.md)、[Phase 2](docs/phase2-verification.md)、[Phase 3](docs/phase3-verification.md)、[Phase 4](docs/phase4-verification.md)、[Phase 5](docs/phase5-verification.md)、[Phase 6](docs/phase6-verification.md)、[Phase 7](docs/phase7-verification.md)、[演示指南](docs/demo-guide.md)。

## 已知限制与下一阶段

当前没有登录/注册限流、账号找回、撤销所有设备会话或账户删除功能；适用于本地课程试点验收，尚未进行生产部署验证。保留 Starlette TestClient 的一条 AnyIO 弃用警告，详情见报告。

Phase 6 已完成课程 MVP 三项辅助业务。Phase 7 建议使用隔离服务做关键流程集成验收，重点核对管理员权限、不同用户数据隔离、旧数据迁移和手机交互；再统一文案和状态反馈。转赠聊天可作为后续优化，保留现有 Phase 5 会话规则。本阶段完成后停止，未自动启动 Phase 7。
