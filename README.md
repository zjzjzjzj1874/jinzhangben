<!--
 * @Author: zhoujian zhoujian@industai.com
 * @Date: 2025-01-02 15:07:15
 * @LastEditors: zhoujian zhoujian@industai.com
 * @LastEditTime: 2025-01-02 15:32:17
 * @FilePath: /bill-py-streamlit/README.md
 * @Description: readme
-->
# 每日账单管理系统

## 项目简介
这是一个使用Streamlit开发的个人财务管理应用，可以记录和统计每日收支情况。

## 功能特点
- 记录每日账单
- 按类型分类账单
- 统计年度收支情况
- 数据可视化展示

## 技术栈
- Streamlit
- MongoDB
- Pandas
- Plotly

## 安装依赖
```bash
pip install -r requirements.txt
```

## 运行应用
```bash
# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动应用（23333端口）
streamlit run app.py --server.port 23333
```
