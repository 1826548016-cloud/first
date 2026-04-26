# 日有所做 · 任务与学习看板（Django + ECharts）

一个轻量但功能完整的个人任务 / 学习记录系统：任务列表 + 专题学习记录 + 可视化看板（趋势图、专题占比）。界面偏简洁，适合日常 PC 端使用。
项目已上线http://first.qzx1028.space/，请访问网址，另外如果无法访问可能与备案进度有关，于2026年5月14日后重试
## 功能

- 任务管理：新增/编辑/完成/删除（含软删除）、备注、截止时间、状态筛选
- 学习记录：按专题记录每日学习分钟数（可备注）
- 学习看板：堆叠趋势图（支持缩放/图例滚动）+ 专题占比（饼图 + Top 列表）
- 专题管理：内置专题 + 自定义专题，支持“合并到任务”统计口径
- 主题：浅色 / 深色切换

## 技术栈

- 后端：Python 3.x + Django 4.2
- 数据库：MySQL（PyMySQL）
- 前端：Django Templates + 原生 CSS/JS
- 图表：ECharts（本地静态文件）

## 本地运行（Windows / PowerShell）

在 `task_manager/` 目录下执行。

### 1) 安装依赖

```bash
pip install -r requirements.txt
```

### 2) 准备 MySQL 数据库

示例建库：

```sql
CREATE DATABASE renwu CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

可用环境变量覆盖默认连接信息（不设置也能跑，默认 `root/root@localhost:3306 + renwu`）：

```powershell
$env:DJANGO_DB_NAME="renwu"
$env:DJANGO_DB_USER="root"
$env:DJANGO_DB_PASSWORD="root"
$env:DJANGO_DB_HOST="localhost"
$env:DJANGO_DB_PORT="3306"
```

### 3) 执行迁移

```bash
python manage.py migrate
```

### 4) 启动服务

```bash
python manage.py runserver
```

## 页面入口

- 首页：`http://127.0.0.1:8000/`
- 任务列表：`http://127.0.0.1:8000/tasks/`
- 学习看板：`http://127.0.0.1:8000/dashboard/`
- 专题：`http://127.0.0.1:8000/topics/`
- 登录：`http://127.0.0.1:8000/login/`
- 管理后台：`http://127.0.0.1:8000/admin/`

## 常见问题

### 访问 `/tasks/` 报：Unknown column 'tasks_task.user_id'

说明数据库迁移没跑全。执行：

```bash
python manage.py showmigrations tasks
python manage.py migrate tasks 0020
```