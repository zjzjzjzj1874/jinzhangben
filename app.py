import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from database import BillDatabase
from datetime import datetime
from bill_types import BillCategory
from loguru import logger
import os
import socket
from user_manager import UserManager

# 获取本机IP地址的函数
def get_client_ip():
    try:
        # 尝试获取Streamlit提供的远程IP
        remote_ip = st.runtime.scriptrunner.add_script_run_ctx().get_remote_ip()
        if remote_ip:
            return remote_ip
        
        # 备选方案：获取本机IP
        return socket.gethostbyname(socket.gethostname())
    except Exception as e:
        logger.warning(f"获取IP地址失败: {e}")
        return "Unknown"

# 配置日志
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)
logger.add(os.path.join(log_dir, 'bill_app_{time:YYYY-MM-DD}.log'), 
           rotation='1 day',  # 按天切割
           retention='7 days',  # 保留最近7天的日志
           level='INFO',  # 日志级别
           format="{time} | {level} | IP: {extra[ip]} | {message}"  # 自定义日志格式
)

class BillTrackerApp:
    def __init__(self):
        """初始化应用"""
        try:
            self.db = BillDatabase(port=27017)
            self.user_manager = UserManager()
            st.set_page_config(page_title='每日账单管理', page_icon='💰')
            
            # 初始化会话状态
            if 'logged_in' not in st.session_state:
                st.session_state.logged_in = False
                st.session_state.username = None
            
            logger.info("应用初始化成功", extra={"ip": get_client_ip()})
        except Exception as e:
            logger.error(f"应用初始化失败: {e}", extra={"ip": get_client_ip()})
            st.error(f"应用初始化失败: {e}")
    
    def login_page(self):
        """登录页面"""
        st.title('💰 每日账单管理系统 - 登录')
        
        username = st.text_input('用户名')
        password = st.text_input('密码', type='password')
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button('登录'):
                if self.user_manager.authenticate(username, password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.success('登录成功！')
                    logger.info(f"用户 {username} 登录成功", extra={"ip": get_client_ip()})
                    st.experimental_rerun()
                else:
                    st.error('用户名或密码错误')
                    logger.warning(f"登录失败：{username}", extra={"ip": get_client_ip()})
        
        with col2:
            if st.button('注册'):
                new_username = st.text_input('新用户名')
                new_password = st.text_input('新密码', type='password')
                confirm_password = st.text_input('确认密码', type='password')
                
                if new_password == confirm_password:
                    if self.user_manager.add_user(new_username, new_password):
                        st.success('注册成功！')
                        logger.info(f"用户 {new_username} 注册成功", extra={"ip": get_client_ip()})
                    else:
                        st.error('用户名已存在')
                else:
                    st.error('两次密码不一致')
    
    def run(self):
        """运行Streamlit应用"""
        # 检查登录状态
        if not st.session_state.logged_in:
            self.login_page()
            return
        
        st.sidebar.text(f'欢迎，{st.session_state.username}')
        if st.sidebar.button('退出登录'):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.experimental_rerun()
        
        st.title('💰 每日账单管理系统')
        
        # 侧边栏菜单
        menu = st.sidebar.radio('功能菜单', 
            ['记录账单', '账单统计', '账单查询', '财务看板', '年度总览'])
        
        if menu == '记录账单':
            self.record_bill_page()
        elif menu == '账单统计':
            self.bill_statistics_page()
        elif menu == '账单查询':
            self.query_bills_page()
        elif menu == '财务看板':
            self.dashboard_page()
        elif menu == '年度总览':
            self.annual_overview_page()
    
    def record_bill_page(self):
        """记录账单页面"""
        st.header('记录新账单')
        
        col1, col2 = st.columns(2)
        
        with col1:
            bill_type = st.selectbox('账单类型', ['支出', '收入'])
        
        with col2:
            bill_date = st.date_input('账单日期', datetime.now())
        
        # 根据账单类型动态显示类型选择
        if bill_type == '收入':
            bill_category = st.selectbox('收入类型', 
                [category.value for category in BillCategory.Income])
        else:
            bill_category = st.selectbox('支出类型', 
                [category.value for category in BillCategory.Expense])
        
        amount = st.number_input('金额', min_value=0.0, step=0.1)
        remark = st.text_input('备注')
        
        if st.button('保存账单'):
            try:
                # 将日期转换为20250102格式
                formatted_date = int(bill_date.strftime('%Y%m%d'))
                
                # 获取具体的枚举类型
                category_enum = BillCategory.get_type_by_name(bill_category)
                
                self.db.insert_bill(
                    bill_date=formatted_date, 
                    bill_type=bill_type, 
                    bill_category=category_enum,
                    amount=amount, 
                    remark=remark
                )
                st.success('账单保存成功！')
                logger.info(f"成功保存账单: {bill_type}, {bill_category}, {amount}", extra={"ip": get_client_ip()})
            except Exception as e:
                st.error(f'保存失败: {e}')
                logger.error(f"保存账单失败: {e}", extra={"ip": get_client_ip()})
    
    def bill_statistics_page(self):
        """账单统计页面"""
        st.header('账单统计')
        
        year = st.selectbox('选择年份', 
            [2024, 2025, 2026], index=1)
        
        try:
            bills = self.db.get_bills_by_year(year)
            
            if not bills.empty:
                # 按类型分组统计
                type_summary = bills.groupby('category')['amount'].sum()
                
                # 绘制饼图
                fig = px.pie(
                    values=type_summary.values, 
                    names=type_summary.index, 
                    title=f'{year}年账单分类'
                )
                st.plotly_chart(fig)
                
                # 按月份统计
                bills['month'] = bills['bill_date'] % 10000 // 100
                monthly_summary = bills.groupby('month')['amount'].sum()
                
                # 绘制柱状图
                fig_bar = px.bar(
                    x=monthly_summary.index, 
                    y=monthly_summary.values, 
                    labels={'x': '月份', 'y': '金额'},
                    title=f'{year}年月度账单总览'
                )
                st.plotly_chart(fig_bar)
                
                logger.info(f"成功生成{year}年账单统计", extra={"ip": get_client_ip()})
            else:
                st.warning('该年份暂无账单数据')
                logger.warning(f"{year}年无账单数据", extra={"ip": get_client_ip()})
        except Exception as e:
            st.error(f'统计失败: {e}')
            logger.error(f"账单统计失败: {e}", extra={"ip": get_client_ip()})
    
    def query_bills_page(self):
        """账单查询页面"""
        st.header('账单查询')
        
        # 查询条件
        col1, col2, col3 = st.columns(3)
        
        with col1:
            start_date = st.date_input('开始日期', 
                datetime(2024, 1, 1), key='query_start')
            bill_type = st.selectbox('账单类型', 
                ['全部', '支出', '收入'], key='query_type')
        
        with col2:
            end_date = st.date_input('结束日期', 
                datetime.now(), key='query_end')
            bill_category = st.selectbox('账单分类', 
                ['全部'] + [category.value for category in BillCategory.Expense] + 
                [category.value for category in BillCategory.Income], 
                key='query_category')
        
        with col3:
            min_amount = st.number_input('最小金额', min_value=0.0, step=0.1, key='query_min')
            max_amount = st.number_input('最大金额', min_value=0.0, step=0.1, key='query_max')
        
        remark = st.text_input('备注关键词')
        
        if st.button('查询'):
            try:
                # 准备查询参数
                query_params = {
                    'start_date': int(start_date.strftime('%Y%m%d')),
                    'end_date': int(end_date.strftime('%Y%m%d'))
                }
                
                if bill_type != '全部':
                    query_params['bill_type'] = bill_type
                
                if bill_category != '全部':
                    query_params['bill_category'] = bill_category
                
                if min_amount > 0:
                    query_params['min_amount'] = min_amount
                
                if max_amount > 0:
                    query_params['max_amount'] = max_amount
                
                if remark:
                    query_params['remark'] = remark
                
                # 执行查询
                bills = self.db.query_bills(**query_params)
                
                if not bills.empty:
                    st.dataframe(bills)
                    
                    # 查询结果统计
                    st.subheader('查询结果统计')
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric('总记录数', len(bills))
                    
                    with col2:
                        st.metric('总金额', f'¥ {bills["amount"].sum():.2f}')
                    
                    with col3:
                        st.metric('平均金额', f'¥ {bills["amount"].mean():.2f}')
                else:
                    st.warning('未找到匹配的账单')
            except Exception as e:
                st.error(f'查询失败: {e}')
    
    def dashboard_page(self):
        """财务看板页面"""
        st.header('财务看板')
        
        # 选择周期
        period_type = st.selectbox('选择周期', 
            ['周', '月', '季度', '年'], key='dashboard_period')
        
        # 映射中文到英文
        period_map = {
            '周': 'week',
            '月': 'month', 
            '季度': 'quarter', 
            '年': 'year'
        }
        
        try:
            # 获取周期财务总结
            summary = self.db.get_period_summary(
                period_type=period_map[period_type]
            )
            
            # 显示总结
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric('总收入', f'¥ {summary["income"]:.2f}')
            
            with col2:
                st.metric('总支出', f'¥ {summary["expense"]:.2f}')
            
            with col3:
                st.metric('净收益', f'¥ {summary["net"]:.2f}')
            
            # 绘制饼图
            bills = self.db.query_bills(
                start_date=summary['start_date'], 
                end_date=summary['end_date']
            )
            
            if not bills.empty:
                # 按分类统计
                category_summary = bills.groupby('category')['amount'].sum()
                
                fig = px.pie(
                    values=category_summary.values, 
                    names=category_summary.index, 
                    title=f'{period_type}账单分类'
                )
                st.plotly_chart(fig)
        except Exception as e:
            st.error(f'{period_type}财务看板获取失败: {e}')
    
    def annual_overview_page(self):
        """年度总览页面"""
        st.header('年度财务总览')
        
        year = st.selectbox('选择年份', 
            [2024, 2025, 2026], index=1)
        
        try:
            summary = self.db.get_annual_summary(year)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric('总收入', f'¥ {summary["income"]:.2f}')
            
            with col2:
                st.metric('总支出', f'¥ {summary["expense"]:.2f}')
            
            with col3:
                st.metric('净收益', f'¥ {summary["net"]:.2f}')
            
            logger.info(f"成功生成{year}年度财务总览", extra={"ip": get_client_ip()})
        except Exception as e:
            st.error(f'总览获取失败: {e}')
            logger.error(f"年度总览获取失败: {e}", extra={"ip": get_client_ip()})

def main():
    try:
        app = BillTrackerApp()
        app.run()
    except Exception as e:
        logger.critical(f"应用运行失败: {e}", extra={"ip": get_client_ip()})

if __name__ == '__main__':
    main()
