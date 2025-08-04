# Changelog

所有重要的项目变更都会记录在这个文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 新增
- 微信账单导入功能
  - 新增 `WechatBillProcessor` 类支持微信账单Excel文件导入
  - 新增 `import_wechat_bills.py` 命令行导入工具
  - 在Streamlit应用中集成微信账单导入界面
  - 支持微信账单自动分类，包含交通、餐饮、购物等多个类别
  - 支持预览模式，可在导入前查看账单数据
- 统一账单分类器
  - 新增 `UniversalBillClassifier` 类统一处理支付宝和微信账单分类
  - 合并了支付宝和微信的分类规则，减少代码重复
  - 提供 `classify_alipay_bill` 和 `classify_wechat_bill` 专用方法

### 修复
- 修复了数据库查询中的日期比较问题，将字符串比较改为数值比较
  - 更新了 `query_bills` 方法使用 `$expr` 和 `$toInt` 进行数值比较
  - 更新了 `get_period_summary` 方法的日期查询逻辑
  - 更新了 `get_category_summary` 方法的日期查询逻辑
  - 更新了 `get_monthly_summary` 方法的日期查询逻辑
  - 更新了 `get_annual_summary` 方法的日期查询逻辑
  - 更新了 `get_bills_by_year` 方法的日期查询逻辑
- 修复了支付宝账单导入中的分类逻辑缺陷
  - 将羽毛球和哈啰单车的分类判断优先级提高
  - 扩展了羽毛球相关关键词匹配：支持"羽毛球"和"羽毛球馆"
  - 扩展了哈啰单车相关关键词匹配：支持"哈啰单车"和"哈啰"
- 修复了微信账单处理器的导入和分类问题
  - 统一了 `import_bills_to_database` 方法的返回值格式，支持可选的错误计数返回
  - 确保 `raw_data` 字段不被插入到数据库中
  - 修复了分类器重构后的导入错误，移除了已删除类的引用

### 改进
- 重构了账单分类架构
  - 将支付宝和微信的分类逻辑合并到统一的 `UniversalBillClassifier` 中
  - 消除了 `AlipayBillClassifier` 和 `WechatBillClassifier` 类的代码重复
  - 提高了代码的可维护性和扩展性
  - 统一了分类规则的管理和更新
- 清理了 `database.py` 中的非必要调试日志
  - 移除了数据库连接初始化时的详细打印信息
  - 移除了 `insert_bill` 方法中的数据打印
  - 移除了 `paginate_query` 方法中的查询调试信息
  - 移除了 `query_bills` 方法中的所有调试和测试查询代码
  - 保留了关键的错误日志和连接状态日志

### 技术债务
- 提供了代码质量和可维护性改进建议
  - 架构优化：分离业务逻辑和UI逻辑，配置管理
  - 数据处理：智能分类，增强验证
  - 错误处理和日志：统一异常处理，日志优化
  - 代码重构：消除重复，类型注解
  - 性能优化：数据库查询和前端优化
  - 测试和文档：单元测试，API文档
  - 安全性：输入验证，敏感信息保护
  - 部署和运维：容器化，监控

## [1.0.0] - 初始版本

### 新增
- 基于 Streamlit 的个人财务管理系统
- 支付宝账单导入功能
- 账单记录和查询功能
- 财务统计和可视化
- 用户管理系统
- MongoDB 数据库集成
- Docker 容器化支持