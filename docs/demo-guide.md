# 华园易享课程演示指南

演示数据只写入 `backend/.local/demo/demo.db`，不会写入开发数据库 `backend/data/scut_share.db`。演示账户使用虚构学号，不代表华南理工大学官方身份认证。

## 启动

先准备数据库和依赖：

```powershell
Set-Location E:\homework\scut-share\backend
$ProjectPython = Join-Path $env:USERPROFILE 'anaconda3\envs\scut_share_env\python.exe'
& $ProjectPython -m pip install -r requirements.txt
& $ProjectPython -m app.demo_seed --reset
& $ProjectPython -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

另开终端启动前端：

```powershell
Set-Location E:\homework\scut-share\frontend
npm.cmd run dev
```

打开 `http://127.0.0.1:5173/`。前后端使用同一主机名，确保 Cookie 会话正常工作。

## 演示账户

三个账户的密码均为 `Demo-only-password-123`：

| 账户 | 学号 | 用途 |
| --- | --- | --- |
| 演示物主 | `DEMO_OWNER` | 发布物品、交易卖家、借出物主 |
| 演示买家 | `DEMO_BUYER` | 交易买家、转赠物主 |
| 演示同学 | `DEMO_HELPER` | 借用人、转赠领取人 |

## 建议演示顺序

1. 以“演示物主”进入物品广场，展示课程相机、便携投影仪和兴趣标签；使用搜索、分类、校区和流通方式筛选。
2. 以“演示买家”查看课程相机，进入“我的交易”展示已完成交易记录和线下付款/交付提示；进入“我的消息”展示两条历史聊天。
3. 以“演示同学”进入“我的借还”，展示已完成的免费借还记录、预计归还时间和双方确认时间。免费借还流程不包含租金、押金或手续费。
4. 以“演示买家”浏览闲置教材礼包，进入“我的转赠”展示已完成的免费转赠记录。
5. 使用页面的“举报”入口提交测试举报；管理员页面需要先通过 CLI 显式授权一个隔离账户，普通用户不能访问管理员接口。

## 重置

停止后端后执行：

```powershell
Set-Location E:\homework\scut-share\backend
$ProjectPython = Join-Path $env:USERPROFILE 'anaconda3\envs\scut_share_env\python.exe'
& $ProjectPython -m app.demo_seed --reset
```

不要对开发数据库使用 `--reset`，也不要在未知状态的开发数据库上反复执行降级迁移。课程展示结束后可以直接删除 `backend/.local/demo/`，不会影响开发用户、开发图片或迁移历史。
