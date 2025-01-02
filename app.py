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
            
            logger.info("应用初始化成功")
        except Exception as e:
            logger.error(f"应用初始化失败: {e}")
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
                    st.rerun()
                else:
                    st.error('用户名或密码错误')
                    logger.warning(f"登录失败：{username}")
        
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
            st.rerun()
        
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
        st.header('录入账单')
        
        # 检查是否有上一次操作的消息
        if 'bill_message' in st.session_state:
            st.info(st.session_state.bill_message)
            del st.session_state.bill_message
        
        # 账单类型选择
        bill_type = st.radio('账单类型', ['支出', '收入'])
        
        # 根据账单类型动态显示分类
        if bill_type == '收入':
            bill_category = st.selectbox('收入分类', 
                [cat.value for cat in BillCategory.Income])
            # 收入为正数
            amount_sign = 1
        else:
            bill_category = st.selectbox('支出分类', 
                [cat.value for cat in BillCategory.Expense])
            # 支出为负数
            amount_sign = -1
        
        # 其他输入项
        bill_date = st.date_input('账单日期', datetime.now())
        amount = st.number_input('金额', min_value=0.0, step=0.01)
        remark = st.text_input('备注（可选）')
        
        # 提交按钮
        if st.button('保存账单'):
            try:
                # 准备账单数据字典
                bill_data = {
                    'bill_date': bill_date.strftime('%Y%m%d'),  # 转换为字符串格式
                    'type': bill_type,
                    'category': bill_category,
                    'amount': float(amount) * amount_sign,  # 支出为负数，收入为正数
                    'remark': remark or '',  # 如果备注为空，使用空字符串
                    'create_time': datetime.now()  # 添加创建时间
                }
                
                # 插入账单
                result = self.db.insert_bill(bill_data)
                print("保存账单-成功提示！")
                # 准备成功消息
                st.session_state.bill_message = f"""
                🎉 账单保存成功！
                📅 日期: {bill_date.strftime("%Y-%m-%d")}
                💰 金额: ¥{amount:.2f} ({bill_type})
                📊 类型: {bill_category}
                {"📝 备注: " + remark if remark else ""}
                """
                
                # 成功提示
                st.balloons()  # 添加气球动画
                
                # 清空输入
                st.rerun()
                print("保存账单-清空输入！")
                
            except Exception as e:
                # 错误处理
                st.error(f'保存账单失败: {e}')
    
    def bill_statistics_page(self):
        """账单统计页面"""
        st.header('账单统计')
        
        # 获取当前年份
        current_year = datetime.now().year
        
        # 选择统计维度
        statistic_type = st.selectbox('统计维度', ['年度统计', '月度统计', '类别统计'])
        
        try:
            # 年度统计
            if statistic_type == '年度统计':
                # 选择年份
                selected_year = st.selectbox('选择年份', 
                    list(range(current_year, current_year - 5, -1)), 
                    index=0
                )
                
                # 获取年度财务总结
                summary = self.db.get_annual_summary(selected_year)
                
                # 收入支出饼图
                col1, col2 = st.columns(2)
                
                with col1:
                    # 收入类别统计
                    income_summary = self.db.get_category_summary(selected_year, 'income')
                    
                    if not income_summary.empty:
                        fig_income = px.pie(
                            values=income_summary['amount'], 
                            names=income_summary['category'], 
                            title='收入分类',
                            hole=0.3,  # 添加中心空洞
                            labels={'category': '类别', 'amount': '金额'},
                            color_discrete_sequence=px.colors.qualitative.Pastel  # 使用柔和的颜色
                        )
                        fig_income.update_traces(textposition='inside', textinfo='percent+label')
                        fig_income.update_layout(
                            margin=dict(t=50, b=0, l=0, r=0),  # 调整边距
                            legend=dict(
                                orientation="h",  # 水平图例
                                yanchor="bottom",
                                y=1.02,
                                xanchor="center",
                                x=0.5
                            )
                        )
                        st.plotly_chart(fig_income, use_container_width=True)
                
                with col2:
                    # 支出类别统计
                    expense_summary = self.db.get_category_summary(selected_year, 'expense')
                    
                    if not expense_summary.empty:
                        fig_expense = px.pie(
                            values=expense_summary['amount'], 
                            names=expense_summary['category'], 
                            title='支出分类',
                            hole=0.3,  # 添加中心空洞
                            labels={'category': '类别', 'amount': '金额'},
                            color_discrete_sequence=px.colors.qualitative.Pastel1  # 使用另一组柔和的颜色
                        )
                        fig_expense.update_traces(textposition='inside', textinfo='percent+label')
                        fig_expense.update_layout(
                            margin=dict(t=50, b=0, l=0, r=0),  # 调整边距
                            legend=dict(
                                orientation="h",  # 水平图例
                                yanchor="bottom",
                                y=1.02,
                                xanchor="center",
                                x=0.5
                            )
                        )
                        st.plotly_chart(fig_expense, use_container_width=True)
            
            # 月度统计
            elif statistic_type == '月度统计':
                # 选择年份
                selected_year = st.selectbox('选择年份', 
                    list(range(current_year, current_year - 5, -1)), 
                    index=0
                )
                
                # 获取月度收支统计
                monthly_summary = self.db.get_monthly_summary(selected_year)
                
                # 绘制月度收支柱状图
                fig_monthly = go.Figure()
                fig_monthly.add_trace(go.Bar(
                    x=monthly_summary['month'], 
                    y=monthly_summary['income'], 
                    name='月度收入'
                ))
                fig_monthly.add_trace(go.Bar(
                    x=monthly_summary['month'], 
                    y=monthly_summary['expense'], 
                    name='月度支出'
                ))
                fig_monthly.update_layout(
                    title=f'{selected_year}年月度收支',
                    xaxis_title='月份',
                    yaxis_title='金额',
                    barmode='group'
                )
                st.plotly_chart(fig_monthly)
            
            # 类别统计
            elif statistic_type == '类别统计':
                # 选择年份和类型
                selected_year = st.selectbox('选择年份', 
                    list(range(current_year, current_year - 5, -1)), 
                    index=0
                )
                bill_type = st.radio('选择类型', ['收入', '支出'])
                
                # 获取类别统计
                if bill_type == '收入':
                    category_summary = self.db.get_category_summary(selected_year, 'income')
                else:
                    category_summary = self.db.get_category_summary(selected_year, 'expense')
                
                # 绘制类别饼图
                if not category_summary.empty:
                    fig_category = px.pie(
                        values=category_summary['amount'], 
                        names=category_summary['category'], 
                        title=f'{selected_year}年{bill_type}类别统计',
                        hole=0.3,  # 添加中心空洞
                        labels={'category': '类别', 'amount': '金额'},
                        color_discrete_sequence=px.colors.qualitative.Pastel  # 使用柔和的颜色
                    )
                    fig_category.update_traces(textposition='inside', textinfo='percent+label')
                    fig_category.update_layout(
                        margin=dict(t=50, b=0, l=0, r=0),  # 调整边距
                        legend=dict(
                            orientation="h",  # 水平图例
                            yanchor="bottom",
                            y=1.02,
                            xanchor="center",
                            x=0.5
                        )
                    )
                    st.plotly_chart(fig_category, use_container_width=True)
                    
                    # 显示详细类别统计表格
                    st.subheader('详细类别统计')
                    st.dataframe(category_summary)
                else:
                    st.warning(f'{selected_year}年没有{bill_type}记录')
        
        except Exception as e:
            st.error(f'统计失败: {e}')
    
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
        period_type = st.selectbox('选择统计周期', ['周', '月', '季', '年'])
        
        # 映射选择到数据库查询类型
        period_map = {
            '周': 'week',
            '月': 'month', 
            '季': 'quarter', 
            '年': 'year'
        }
        
        try:
            # 获取当前日期
            current_date = datetime.now().strftime('%Y%m%d')
            
            # 获取财务总结
            summary = self.db.get_period_summary(
                period_type=period_map[period_type], 
                start_date=current_date
            )
            
            # 获取详细的类别数据
            bills = self.db.query_bills(
                start_date=summary['start_date'], 
                end_date=summary['end_date']
            )
            
            # 计算收入和支出总额
            # 正数为收入，负数为支出
            income_bills = bills[bills['amount'] > 0]
            expense_bills = bills[bills['amount'] < 0]
            
            # 计算总收入和总支出
            total_income = income_bills['amount'].sum()
            total_expense = abs(expense_bills['amount'].sum())  # 取绝对值
            net_total = total_income + bills[bills['amount'] < 0]['amount'].sum()
            
            # 显示总览数据
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric('总收入', f'¥ {total_income:.2f}')
            with col2:
                st.metric('总支出', f'¥ {total_expense:.2f}')
            with col3:
                st.metric('净收益', f'¥ {net_total:.2f}')
            
            # 按类别汇总
            category_summary = bills.groupby('category')['amount'].sum().reset_index()
            
            # 收入类别饼图
            income_categories = ['兼职收入', '补贴', '其他收入']
            income_data = category_summary[
                (category_summary['category'].isin(income_categories)) & 
                (category_summary['amount'] > 0)
            ]
            if not income_data.empty:
                fig_income = px.pie(
                    income_data, 
                    values='amount', 
                    names='category', 
                    title='收入分类',
                    hole=0.3,  # 添加中心空洞
                    labels={'category': '类别', 'amount': '金额'},
                    color_discrete_sequence=px.colors.qualitative.Pastel  # 使用柔和的颜色
                )
                fig_income.update_traces(textposition='inside', textinfo='percent+label')
                fig_income.update_layout(
                    margin=dict(t=50, b=0, l=0, r=0),  # 调整边距
                    legend=dict(
                        orientation="h",  # 水平图例
                        yanchor="bottom",
                        y=1.02,
                        xanchor="center",
                        x=0.5
                    )
                )
                st.plotly_chart(fig_income, use_container_width=True)
            
            # 支出类别饼图
            expense_categories = [cat for cat in category_summary['category'] 
                                  if cat not in income_categories]
            expense_data = category_summary[
                (category_summary['category'].isin(expense_categories)) & 
                (category_summary['amount'] < 0)
            ].copy()
            # 转换为正数用于显示
            expense_data['amount'] = abs(expense_data['amount'])
            if not expense_data.empty:
                fig_expense = px.pie(
                    expense_data, 
                    values='amount', 
                    names='category', 
                    title='支出分类',
                    hole=0.3,  # 添加中心空洞
                    labels={'category': '类别', 'amount': '金额'},
                    color_discrete_sequence=px.colors.qualitative.Pastel1  # 使用另一组柔和的颜色
                )
                fig_expense.update_traces(textposition='inside', textinfo='percent+label')
                fig_expense.update_layout(
                    margin=dict(t=50, b=0, l=0, r=0),  # 调整边距
                    legend=dict(
                        orientation="h",  # 水平图例
                        yanchor="bottom",
                        y=1.02,
                        xanchor="center",
                        x=0.5
                    )
                )
                st.plotly_chart(fig_expense, use_container_width=True)
            
            # 显示统计周期
            st.write(f"统计周期：{summary['start_date']} 至 {summary['end_date']}")
            
        except Exception as e:
            st.error(f'财务看板获取失败: {e}')
    
    def annual_overview_page(self):
        """年度总览页面"""
        st.header('年度财务总览')
        
        # 获取当前年份
        current_year = datetime.now().year
        
        # 选择年份
        selected_year = st.selectbox('选择年份', 
            list(range(current_year, current_year - 5, -1)), 
            index=0
        )
        
        # 默认每页记录数和页码
        page_size = st.sidebar.selectbox('每页记录数', [10, 20, 50, 100], index=0)
        page = st.sidebar.number_input('页码', min_value=1, value=1)
        
        # 查询按钮
        if st.sidebar.button('查询'):
            try:
                # 获取年度财务总结
                summary = self.db.get_annual_summary(selected_year)
                
                # 显示年度总览
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric('总收入', f'¥ {summary["income"]:.2f}')
                with col2:
                    st.metric('总支出', f'¥ {summary["expense"]:.2f}')
                with col3:
                    st.metric('净收益', f'¥ {summary["net"]:.2f}')
                
                # 获取指定年份的分页账单
                bills_result = self.db.get_bills_by_year(selected_year, page, page_size)
                bills = bills_result['data']
                
                # 如果没有账单数据
                if bills.empty:
                    st.warning(f'{selected_year}年没有账单记录')
                    return
                
                # 详细账单表格
                st.subheader('账单明细')
                st.dataframe(bills[['bill_date', 'type', 'category', 'amount', 'remark']])
                
                # 分页控件（放在底部）
                st.markdown('---')  # 添加分隔线
                
                # 分页控件 - 横向布局
                col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 2])
                
                with col2:
                    st.write(f'每页 {page_size} 条')
                
                with col3:
                    st.write(f'第 {page} 页')
                
                with col4:
                    st.write(f"共 {bills_result['total_count']} 条")
            
            except Exception as e:
                st.error(f'年度总览获取失败: {e}')
        else:
            st.info('请在侧边栏选择查询条件并点击查询按钮')

def main():
    try:
        app = BillTrackerApp()
        app.run()
    except Exception as e:
        logger.critical(f"应用运行失败: {e}")

if __name__ == '__main__':
    main()
