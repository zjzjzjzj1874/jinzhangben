# 每日账单管理系统 (Daily Expense Tracker)

## 项目简介 (Project Overview)

这是一个基于 Streamlit 和 MongoDB 的个人财务管理应用，帮助用户轻松记录、分析和追踪日常收支。

This is a personal finance management application built with Streamlit and MongoDB, helping users easily record, analyze, and track daily income and expenses.

## 主要功能 (Key Features)

### 1. 用户认证 (User Authentication)
- 安全的用户登录和注册系统
- 使用 bcrypt 加密存储用户密码
- 保护个人财务数据隐私

### 2. 账单记录 (Bill Recording)
- 支持多种收入类型：
  - 兼职收入
  - 补贴
  - 其他收入

- 支持多种支出类型：
  - 餐饮
  - 羽毛球
  - 交通
  - 娱乐
  - 日用品
  - 生活缴费
  - 小车维护
  - 小车保险
  - 停车费
  - 服饰
  - 旅行
  - 书籍
  - 运动健身
  - 人情往来
  - 家居
  - 物业

### 3. 数据查询 (Data Query)
- 灵活的多条件账单查询
- 支持按日期范围、账单类型、金额范围等筛选
- 支持备注关键词模糊搜索

### 4. 财务分析 (Financial Analysis)
- 周、月、季度、年度财务总结
- 收支图表可视化
- 详细的财务指标展示

## 技术栈 (Tech Stack)

- **前端框架**: Streamlit
- **数据库**: MongoDB
- **数据处理**: Pandas
- **数据可视化**: Plotly
- **日志**: Loguru
- **密码加密**: Bcrypt

## 安装与运行 (Installation and Running)

1. 克隆仓库
```bash
git clone https://github.com/zjzjzjzj1874/python_bill.git
cd python_bill
```

2. 创建虚拟环境
```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate  # Windows
```

3. 安装依赖
```bash
pip3 install -r requirements.txt
```

4. 启动 MongoDB
```bash
# 确保 MongoDB 运行在 localhost:27017
mongod
```

5. 运行应用
```bash
streamlit run app.py
```

## 配置 (Configuration)

- 默认 MongoDB 地址: `localhost:27017`
- 日志文件位置: `logs/` 目录
- 用户信息存储: `users.json`

## 安全性 (Security)

- 用户密码使用 bcrypt 加密存储
- 日志记录包含 IP 地址信息
- 日志按天切割，保留最近 30 天记录

## 贡献 (Contributing)

欢迎提交 Issues 和 Pull Requests！

## 许可证 (License)

[待添加许可证信息]

## 联系 (Contact)

GitHub: [zjzjzjzj1874](https://github.com/zjzjzjzj1874)
