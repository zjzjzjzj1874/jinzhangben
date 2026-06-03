import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from database import (
    BillDatabase,
    get_data_root,
    RESTORE_MODE_BILLS_ONLY,
    RESTORE_MODE_FULL_REPLACE,
    RESTORE_MODE_MERGE,
)
from datetime import datetime
from bill_types import BillCategory
from loguru import logger
import os
import socket
from user_manager import UserManager, AUTH_SUCCESS, AUTH_NEED_CHANGE
import csv
import io
from dotenv import load_dotenv
from alipay_bill_processor import AlipayBillProcessor
from wechat_bill_processor import WechatBillProcessor

# 加载环境变量
load_dotenv()

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
           format="{time} | {level} | {message}"  # 自定义日志格式
)

class BillTrackerApp:
    def __init__(self):
        """初始化应用"""
        try:
            self.db = BillDatabase()
            self.user_manager = UserManager(self.db)
            self.alipay_processor = AlipayBillProcessor(self.db)
            self.wechat_processor = WechatBillProcessor(self.db)
            st.set_page_config(page_title='金账本', page_icon='💰')
            
            # 自定义侧边栏样式
            st.markdown("""
            <style>
            .sidebar .sidebar-content {
                background-color: #f4f6f9;  /* 更柔和的背景色 */
                border-radius: 15px;  /* 更圆的圆角 */
                padding: 20px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.08);  /* 更轻的阴影 */
            }
            .sidebar .stRadio > label {
                font-weight: 700;  /* 更粗的字体 */
                color: #2c3e50;  /* 更深的文字颜色 */
                font-size: 16px;  /* 稍大的字体 */
            }
            .sidebar .stRadio > div > div > label {
                color: #34495e;  /* 选项文字颜色 */
                font-weight: 500;
            }
            .sidebar .stRadio > div > div {
                background-color: #ffffff;  /* 纯白背景 */
                border-radius: 8px;  /* 圆角 */
                padding: 10px;
                border: 1px solid #ecf0f1;  /* 轻微边框 */
            }
            /* 主区域 Tab：胶囊样式，隐藏默认红色下划线 */
            .stTabs [data-baseweb="tab-list"] {
                gap: 6px;
                background: #eef1f6;
                border-radius: 12px;
                padding: 6px 8px;
                border-bottom: none !important;
            }
            .stTabs [data-baseweb="tab-highlight"] {
                display: none !important;
            }
            .stTabs [data-baseweb="tab"] {
                height: 2.5rem;
                border-radius: 8px;
                padding: 0 1.1rem;
                font-weight: 600;
                color: #5c6b7a;
                background: transparent;
                border: none !important;
            }
            .stTabs [aria-selected="true"] {
                background: #ffffff !important;
                color: #c0392b !important;
                box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
                border: none !important;
            }
            .stTabs [data-baseweb="tab-panel"] {
                padding-top: 1.25rem;
            }
            div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
                border-radius: 12px;
            }
            h2.module-title {
                font-size: 1.35rem;
                font-weight: 700;
                color: #2c3e50;
                margin: 0 0 0.75rem 0;
                padding-bottom: 0.5rem;
                border-bottom: 2px solid #eef1f6;
            }
            .kpi-income [data-testid="stMetricValue"] { color: #16a34a !important; }
            .kpi-expense [data-testid="stMetricValue"] { color: #dc2626 !important; }
            .kpi-net [data-testid="stMetricValue"] { color: #2563eb !important; }
            .section-title {
                font-size: 1.05rem;
                font-weight: 600;
                color: #334155;
                margin: 1rem 0 0.5rem;
            }
            .empty-hint {
                text-align: center;
                padding: 2.5rem 1rem;
                color: #94a3b8;
                background: #f8fafc;
                border-radius: 12px;
                border: 1px dashed #cbd5e1;
            }
            </style>
            """, unsafe_allow_html=True)
            
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
        st.title('💰 金账本 - 登录')

        # 首次登录（数据库无密码、文件初始密码校验通过）需先修改密码
        if st.session_state.get('pending_pwd_change'):
            self._change_password_page()
            return

        username = st.text_input('用户名')
        password = st.text_input('密码', type='password')

        if st.button('登录'):
            result = self.user_manager.authenticate(username, password)
            if result == AUTH_SUCCESS:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success('登录成功！')
                logger.info(f"用户 {username} 登录成功", extra={"ip": get_client_ip()})
                st.rerun()
            elif result == AUTH_NEED_CHANGE:
                # 初始密码正确，要求修改并持久化到数据库
                st.session_state.pending_pwd_change = username
                logger.info(f"用户 {username} 首次登录，需修改初始密码", extra={"ip": get_client_ip()})
                st.rerun()
            else:
                st.error('用户名或密码错误')
                logger.warning(f"登录失败：{username}")

    def _change_password_page(self):
        """首次登录修改初始密码页面"""
        username = st.session_state.get('pending_pwd_change')
        st.info(f'用户 {username} 首次登录，请设置新密码')

        new_password = st.text_input('新密码', type='password', key='new_pwd')
        confirm_password = st.text_input('确认新密码', type='password', key='confirm_pwd')

        col1, col2 = st.columns(2)
        with col1:
            if st.button('确认修改'):
                if not new_password:
                    st.error('新密码不能为空')
                elif new_password != confirm_password:
                    st.error('两次输入的密码不一致')
                elif self.user_manager.set_password(username, new_password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    del st.session_state.pending_pwd_change
                    st.success('密码修改成功，已登录！')
                    logger.info(f"用户 {username} 修改初始密码并登录成功", extra={"ip": get_client_ip()})
                    st.rerun()
                else:
                    st.error('密码保存失败，请重试')
        with col2:
            if st.button('取消'):
                del st.session_state.pending_pwd_change
                st.rerun()
    
    def _input_module_page(self):
        """录入模块：主区域 Tab"""
        tab_record, tab_alipay, tab_wechat = st.tabs(['单条录入', '支付宝导入', '微信导入'])
        with tab_record:
            self.record_bill_page()
        with tab_alipay:
            self.alipay_import_page()
        with tab_wechat:
            self.wechat_import_page()

    def _report_module_page(self):
        """报表分析模块：主区域 Tab"""
        tab_dash, tab_stats, tab_query, tab_annual = st.tabs(
            ['财务看板', '账单统计', '账单查询', '年度总览']
        )
        with tab_dash:
            self.dashboard_page()
        with tab_stats:
            self.bill_statistics_page()
        with tab_query:
            self.query_bills_page()
        with tab_annual:
            self.annual_overview_page()

    def run(self):
        """运行Streamlit应用"""
        if not st.session_state.logged_in:
            self.login_page()
            return

        st.sidebar.header('💰 金账本')
        menu = st.sidebar.radio(
            '功能',
            ['录入', '报表分析', '数据备份与恢复'],
            key='main_menu',
        )

        st.sidebar.divider()
        st.sidebar.caption(f'欢迎，{st.session_state.username}')
        if st.sidebar.button('退出登录', use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.rerun()

        if menu == '录入':
            st.markdown('<h2 class="module-title">📝 录入</h2>', unsafe_allow_html=True)
            self._input_module_page()
        elif menu == '报表分析':
            st.markdown('<h2 class="module-title">📊 报表分析</h2>', unsafe_allow_html=True)
            self._report_module_page()
        else:
            self.data_backup_page()
    
    def record_bill_page(self):
        """记录账单页面"""
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
        current_year = datetime.now().year
        with st.container(border=True):
            st.markdown('##### 统计维度')
            statistic_type = st.selectbox(
                '选择维度',
                ['年度统计', '月度统计', '类别统计'],
                key='stats_dimension',
                label_visibility='collapsed',
            )
        
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
        with st.container(border=True):
            st.markdown('##### 筛选条件')
            col1, col2, col3 = st.columns(3)
            with col1:
                start_date = st.date_input('开始日期', datetime(2024, 1, 1), key='query_start')
                bill_type = st.selectbox('账单类型', ['全部', '支出', '收入'], key='query_type')
            with col2:
                end_date = st.date_input('结束日期', datetime.now(), key='query_end')
                bill_categories = st.multiselect(
                    '账单分类（可多选）',
                    [c.value for c in BillCategory.Expense] + [c.value for c in BillCategory.Income],
                    key='query_category',
                )
            with col3:
                min_amount = st.number_input('最小金额', min_value=0.0, step=0.1, key='query_min')
                max_amount = st.number_input('最大金额', min_value=0.0, step=0.1, key='query_max')
            remark = st.text_input('备注关键词', key='query_remark')
            submitted = st.button('查询', type='primary', key='query_bills_btn')

        if submitted:
            try:
                # 准备查询参数
                query_params = {
                    'start_date': int(start_date.strftime('%Y%m%d')),
                    'end_date': int(end_date.strftime('%Y%m%d'))
                }
                
                if bill_type != '全部':
                    query_params['bill_type'] = bill_type
                
                # 多分类：若选择了分类列表，则传递给后端
                if bill_categories:
                    query_params['bill_categories'] = bill_categories
                
                # 处理金额范围查询 - 根据账单类型调整
                if min_amount > 0 or max_amount > 0:
                    if bill_type == '支出':
                        # 对于支出，用户输入的正数需要转换为负数范围
                        # 例如：用户输入最小金额100（表示支出≥100），实际查询amount ≤ -100
                        # 用户输入最大金额200（表示支出≤200），实际查询amount ≥ -200
                        if min_amount > 0:
                            query_params['max_amount'] = -min_amount  # 支出≥100 → amount ≤ -100
                        if max_amount > 0:
                            query_params['min_amount'] = -max_amount  # 支出≤200 → amount ≥ -200
                    else:
                        # 对于收入或全部，保持原有逻辑
                        if min_amount > 0:
                            query_params['min_amount'] = min_amount
                        if max_amount > 0:
                            query_params['max_amount'] = max_amount
                
                if remark:
                    query_params['remark'] = remark
                
                # 执行查询
                bills = self.db.query_bills(**query_params)
                
                if not bills.empty:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        with st.container(border=True):
                            st.metric('总记录数', f'{len(bills):,}')
                    with col2:
                        with st.container(border=True):
                            st.metric('总金额', f'¥ {bills["amount"].sum():,.2f}')
                    with col3:
                        with st.container(border=True):
                            st.metric('平均金额', f'¥ {bills["amount"].mean():,.2f}')
                    st.markdown('<p class="section-title">查询结果</p>', unsafe_allow_html=True)
                    st.dataframe(bills, use_container_width=True, hide_index=True)
                else:
                    st.markdown(
                        '<div class="empty-hint">未找到匹配的账单，请调整筛选条件后重试</div>',
                        unsafe_allow_html=True,
                    )
            except Exception as e:
                st.error(f'查询失败: {e}')
    
    def dashboard_page(self):
        """财务看板页面"""
        with st.container(border=True):
            st.markdown('##### 统计周期')
            period_type = st.selectbox(
                '选择周期',
                ['周', '月', '季', '年'],
                key='dash_period',
                label_visibility='collapsed',
            )
        
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
    
    def _fetch_annual_overview(self, selected_year, page, page_size):
        summary = self.db.get_annual_summary(selected_year)
        bills_result = self.db.get_bills_by_year(selected_year, int(page), int(page_size))
        return {
            'year': selected_year,
            'page': int(page),
            'page_size': int(page_size),
            'summary': summary,
            'bills_result': bills_result,
        }

    def _render_kpi_metrics(self, summary):
        """三列 KPI 指标卡"""
        m1, m2, m3 = st.columns(3)
        with m1:
            with st.container(border=True):
                st.markdown('<div class="kpi-income">', unsafe_allow_html=True)
                st.metric('总收入', f'¥ {summary["income"]:,.2f}')
        with m2:
            with st.container(border=True):
                st.markdown('<div class="kpi-expense">', unsafe_allow_html=True)
                st.metric('总支出', f'¥ {abs(summary["expense"]):,.2f}')
        with m3:
            with st.container(border=True):
                st.markdown('<div class="kpi-net">', unsafe_allow_html=True)
                st.metric('净收益', f'¥ {summary["net"]:,.2f}')

    def annual_overview_page(self):
        """年度总览页面"""
        current_year = datetime.now().year
        year_options = list(range(current_year, current_year - 5, -1))

        if 'annual_last_result' not in st.session_state:
            st.session_state.annual_last_result = None

        with st.container(border=True):
            st.markdown('##### 查询条件')
            c1, c2, c3, c4 = st.columns([1.2, 1, 1, 0.8])
            with c1:
                selected_year = st.selectbox('年份', year_options, index=0, key='annual_year')
            with c2:
                page_size = st.selectbox('每页', [10, 20, 50, 100], index=0, key='annual_page_size')
            with c3:
                page = st.number_input('页码', min_value=1, value=1, step=1, key='annual_page')
            with c4:
                st.markdown('<div style="height:1.6rem"></div>', unsafe_allow_html=True)
                submitted = st.button('查询', type='primary', use_container_width=True, key='annual_query_btn')

        if submitted:
            try:
                with st.spinner('加载中...'):
                    st.session_state.annual_last_result = self._fetch_annual_overview(
                        selected_year, page, page_size
                    )
            except Exception as e:
                st.error(f'年度总览获取失败: {e}')
                return

        result = st.session_state.annual_last_result
        if not result:
            st.markdown(
                '<div class="empty-hint">📅 选择年份与分页后，点击「查询」查看年度汇总与明细</div>',
                unsafe_allow_html=True,
            )
            return

        summary = result['summary']
        bills_result = result['bills_result']
        bills = bills_result['data']
        selected_year = result['year']
        page_size = result['page_size']
        page = result['page']

        self._render_kpi_metrics(summary)

        st.subheader(f'{selected_year} 年账单明细')
        if bills.empty:
            st.markdown(
                f'<div class="empty-hint">暂无 {selected_year} 年的账单数据<br><span style="font-size:0.85rem">'
                f'可尝试其他年份，或先在「录入」中添加账单</span></div>',
                unsafe_allow_html=True,
            )
            return

        st.dataframe(
            bills[['bill_date', 'type', 'category', 'amount', 'remark']],
            use_container_width=True,
            hide_index=True,
        )
        total = bills_result['total_count']
        total_pages = max(1, (total + page_size - 1) // page_size)
        st.caption(f'第 {page} / {total_pages} 页 · 每页 {page_size} 条 · 共 {total:,} 条')
    
    def alipay_import_page(self):
        """支付宝账单导入页面"""
        # 使用说明
        with st.expander('📋 使用说明'):
            st.markdown("""
            **支付宝账单导入功能说明：**
            
            1. **文件格式要求：**
               - 支持CSV格式的支付宝账单文件
               - 必须包含：创建时间、商品名称、订单金额(元)、对方名称、分类字段
            
            2. **自动分类规则：**
               - 内置通用关键词自动归类（如"地铁/公交"→交通，"外卖/咖啡/奶茶"→餐饮，"超市/便利店"→日用品）
               - 可在 classifier_keywords.local.json 中补充个人专属关键词，启动时自动与默认规则合并
            
            3. **注意事项：**
               - 所有账单将作为支出类型导入
               - 无法自动分类的订单会单独列出供确认
               - 导入前请确保数据格式正确
            """)
        
        # 文件上传
        uploaded_file = st.file_uploader(
            "选择支付宝账单CSV文件", 
            type=['csv'],
            help="请上传支付宝导出的CSV格式账单文件"
        )
        
        if uploaded_file is not None:
            try:
                # 读取CSV文件
                content = uploaded_file.read().decode('utf-8')
                df = pd.read_csv(io.StringIO(content))
                
                # 验证文件格式
                required_columns = ['创建时间', '商品名称', '订单金额(元)', '对方名称', '分类']
                if not all(col in df.columns for col in required_columns):
                    st.error(f"文件格式不正确！需要包含以下列：{', '.join(required_columns)}")
                    return
                
                # 显示预览
                st.subheader('📊 文件预览')
                st.dataframe(df.head(10))
                st.info(f"共发现 {len(df)} 条账单记录")
                
                # 处理和分类账单
                processed_bills, unclassified_bills = self.alipay_processor.process_alipay_bills(df, include_raw_data=True)
                
                # 显示分类结果
                if processed_bills:
                    st.subheader('✅ 可自动分类的账单')
                    st.info(f"共 {len(processed_bills)} 条可自动导入")
                    
                    # 显示分类统计
                    category_stats = {}
                    for bill in processed_bills:
                        category = bill['category']
                        category_stats[category] = category_stats.get(category, 0) + 1
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**分类统计：**")
                        for category, count in category_stats.items():
                            st.write(f"- {category}: {count} 条")
                    
                    with col2:
                        total_amount = sum(bill['amount'] for bill in processed_bills)
                        st.metric("总金额", f"¥{abs(total_amount):.2f}")
                
                # 显示无法分类的账单 - 直接集成分类功能
                if unclassified_bills:
                    st.subheader('⚠️ 需要手动分类的账单')
                    st.warning(f"共 {len(unclassified_bills)} 条需要手动确认分类")
                    st.info("💡 提示：可以从下拉框选择分类，也可以直接输入自定义分类")
                    
                    # 获取所有可用的支出分类
                    expense_categories = [cat.value for cat in BillCategory.Expense]
                    
                    # 初始化 session state
                    if 'alipay_classifications' not in st.session_state:
                        st.session_state.alipay_classifications = {}
                    
                    # 使用紧凑的表格布局
                    # 创建表头
                    header_cols = st.columns([0.4, 1.2, 1.8, 0.8, 1.8, 1.2, 1.2, 0.6])
                    header_cols[0].markdown("**序号**")
                    header_cols[1].markdown("**创建时间**")
                    header_cols[2].markdown("**商品名称**")
                    header_cols[3].markdown("**金额**")
                    header_cols[4].markdown("**对方名称**")
                    header_cols[5].markdown("**选择分类**")
                    header_cols[6].markdown("**或输入分类**")
                    header_cols[7].markdown("**状态**")
                    
                    # 添加表格样式
                    st.markdown("""
                    <style>
                    .stSelectbox > div > div {
                        padding: 0.25rem 0.5rem;
                    }
                    .stTextInput > div > div > input {
                        padding: 0.25rem 0.5rem;
                    }
                    </style>
                    """, unsafe_allow_html=True)
                    
                    # 为每条未分类账单创建一行（紧凑布局）
                    for idx, bill in enumerate(unclassified_bills):
                        cols = st.columns([0.4, 1.2, 1.8, 0.8, 1.8, 1.2, 1.2, 0.6])
                        
                        with cols[0]:
                            st.markdown(f"<div style='padding: 0.5rem 0;'>{idx + 1}</div>", unsafe_allow_html=True)
                        
                        with cols[1]:
                            st.markdown(f"<div style='padding: 0.5rem 0; font-size: 0.9rem;'>{bill['raw_data']['创建时间']}</div>", unsafe_allow_html=True)
                        
                        with cols[2]:
                            st.markdown(f"<div style='padding: 0.5rem 0; font-size: 0.9rem;'>{bill['raw_data']['商品名称']}</div>", unsafe_allow_html=True)
                        
                        with cols[3]:
                            # 去掉金额中的¥符号后再显示
                            amount_display = str(bill['raw_data']['订单金额(元)']).replace('¥', '').replace('￥', '').strip()
                            st.markdown(f"<div style='padding: 0.5rem 0; font-size: 0.9rem;'>¥{amount_display}</div>", unsafe_allow_html=True)
                        
                        with cols[4]:
                            st.markdown(f"<div style='padding: 0.5rem 0; font-size: 0.9rem;'>{bill['raw_data']['对方名称']}</div>", unsafe_allow_html=True)
                        
                        with cols[5]:
                            selected_category = st.selectbox(
                                '选择',
                                [''] + expense_categories,
                                key=f"alipay_category_{idx}",
                                label_visibility="collapsed"
                            )
                        
                        with cols[6]:
                            custom_category = st.text_input(
                                '输入',
                                value='',
                                key=f"alipay_custom_{idx}",
                                label_visibility="collapsed",
                                placeholder="自定义"
                            )
                        
                        with cols[7]:
                            # 确定最终使用的分类（优先使用自定义）
                            final_category = custom_category if custom_category else selected_category
                            st.session_state.alipay_classifications[idx] = {
                                'bill': bill,
                                'category': final_category
                            }
                            
                            # 状态指示
                            if final_category:
                                st.markdown("<div style='padding: 0.5rem 0; color: green;'>✓</div>", unsafe_allow_html=True)
                            else:
                                st.markdown("<div style='padding: 0.5rem 0; color: #888;'>○</div>", unsafe_allow_html=True)
                    
                    st.markdown("---")
                    
                    # 显示分类汇总
                    classified_count = sum(1 for v in st.session_state.alipay_classifications.values() 
                                          if v.get('category'))
                    unclassified_count = len(unclassified_bills) - classified_count
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("✅ 已分类", classified_count)
                    with col2:
                        st.metric("⏳ 未分类", unclassified_count)
                    with col3:
                        st.metric("📊 总计", len(unclassified_bills))
                
                # 导入按钮
                col1, col2 = st.columns(2)
                
                with col1:
                    if processed_bills:
                        if st.button('🚀 导入可分类账单', type='primary', key='import_classified'):
                            success_count = self.alipay_processor.import_bills_to_database(processed_bills)
                            if success_count > 0:
                                st.success(f"✅ 成功导入 {success_count} 条账单！")
                                st.balloons()
                            else:
                                st.error("导入失败，请检查数据格式")
                    else:
                        st.info("暂无可自动分类的账单")
                
                with col2:
                    if unclassified_bills:
                        # 检查分类状态
                        classified_count = sum(1 for v in st.session_state.get('alipay_classifications', {}).values() 
                                              if v.get('category'))
                        
                        if classified_count > 0:
                            if st.button('✅ 导入手动分类账单', type='primary', key='import_manual'):
                                try:
                                    success_count = 0
                                    for idx, classification in st.session_state.alipay_classifications.items():
                                        if classification.get('category'):
                                            bill = classification['bill']
                                            
                                            # 处理金额：去掉¥等特殊字符，只保留数字和小数点
                                            amount_str = str(bill['raw_data']['订单金额(元)']).replace('¥', '').replace('￥', '').strip()
                                            try:
                                                amount_value = float(amount_str)
                                            except ValueError:
                                                st.error(f"金额格式错误: {bill['raw_data']['订单金额(元)']}")
                                                logger.error(f"无法解析金额: {bill['raw_data']['订单金额(元)']}")
                                                continue
                                            
                                            # 处理日期格式：将 "2026/1/1 12:20" 或 "2026-01-01" 转换为 "20260101"
                                            date_str = bill['raw_data']['创建时间']
                                            if ' ' in date_str:
                                                date_str = date_str.split()[0]  # 去掉时间部分
                                            # 替换所有可能的分隔符
                                            bill_date = date_str.replace('-', '').replace('/', '')
                                            # 确保格式为 YYYYMMDD (补零)
                                            if len(bill_date) < 8:
                                                try:
                                                    from datetime import datetime as dt
                                                    parsed_date = dt.strptime(date_str, '%Y/%m/%d')
                                                    bill_date = parsed_date.strftime('%Y%m%d')
                                                except:
                                                    try:
                                                        parsed_date = dt.strptime(date_str, '%Y-%m-%d')
                                                        bill_date = parsed_date.strftime('%Y%m%d')
                                                    except:
                                                        bill_date = date_str.replace('-', '').replace('/', '')
                                            
                                            classified_bill = {
                                                'bill_date': bill_date,
                                                'type': '支出',
                                                'category': classification['category'],
                                                'amount': -amount_value,
                                                'remark': f"{bill['raw_data']['商品名称']} - {bill['raw_data']['对方名称']}",
                                                'create_time': datetime.now()
                                            }
                                            result = self.db.insert_bill(classified_bill)
                                            if result:
                                                success_count += 1
                                    
                                    if success_count > 0:
                                        # 清空 session state
                                        del st.session_state.alipay_classifications
                                        st.success(f"✅ 成功导入 {success_count} 条手动分类账单！")
                                        st.balloons()
                                        st.info("💡 页面将在 2 秒后刷新...")
                                        import time
                                        time.sleep(2)
                                        st.rerun()
                                    else:
                                        st.error("导入失败，请检查数据")
                                except Exception as e:
                                    st.error(f"导入失败: {e}")
                                    logger.error(f"手动分类账单导入失败: {e}")
                        else:
                            st.warning("⚠️ 请先为账单选择或输入分类")
                    else:
                        st.success("✓ 所有账单已分类")
                
            except Exception as e:
                st.error(f"文件处理失败：{str(e)}")
                logger.error(f"支付宝账单导入失败: {e}")
    
    def wechat_import_page(self):
        """微信账单导入页面"""
        # 使用说明
        with st.expander('📋 使用说明'):
            st.markdown("""
            **微信账单导入功能说明：**
            
            1. **文件格式要求：**
               - 支持Excel格式的微信账单文件(.xlsx)
               - 必须包含：交易时间、交易对方、商品、收/支、金额(元)、分类字段
            
            2. **自动分类规则：**
               - 滴滴出行、地铁、公交 → 交通
               - 美团外卖、饿了么、餐厅 → 餐饮
               - 超市、便利店、商场 → 日用品
               - 电影院、KTV、游戏 → 娱乐
            
            3. **注意事项：**
               - 支持收入和支出两种类型
               - 无法自动分类的订单会单独列出供确认
               - 导入前请确保数据格式正确
            """)
        
        # 文件上传
        uploaded_file = st.file_uploader(
            "选择微信账单Excel文件", 
            type=['xlsx'],
            help="请上传微信导出的Excel格式账单文件"
        )
        
        if uploaded_file is not None:
            try:
                # 读取Excel文件
                df = pd.read_excel(uploaded_file)
                
                # 验证文件格式
                required_columns = ['交易时间', '交易对方', '商品', '收/支', '金额(元)', '分类']
                if not all(col in df.columns for col in required_columns):
                    st.error(f"文件格式不正确！需要包含以下列：{', '.join(required_columns)}")
                    return
                
                # 显示预览
                st.subheader('📊 文件预览')
                st.dataframe(df.head(10))
                st.info(f"共发现 {len(df)} 条账单记录")
                
                # 处理和分类账单
                processed_bills, unclassified_bills = self.wechat_processor.process_wechat_bills(df, include_raw_data=True)
                
                # 显示分类结果
                if processed_bills:
                    st.subheader('✅ 可自动分类的账单')
                    st.info(f"共 {len(processed_bills)} 条可自动导入")
                    
                    # 显示分类统计
                    category_stats = {}
                    income_count = 0
                    expense_count = 0
                    for bill in processed_bills:
                        category = bill['category']
                        category_stats[category] = category_stats.get(category, 0) + 1
                        if bill['transaction_type'] == 'income':
                            income_count += 1
                        else:
                            expense_count += 1
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write("**分类统计：**")
                        for category, count in category_stats.items():
                            st.write(f"- {category}: {count} 条")
                    
                    with col2:
                        total_amount = sum(bill['amount'] for bill in processed_bills)
                        st.metric("总金额", f"¥{total_amount:.2f}")
                    
                    with col3:
                        st.write("**交易类型：**")
                        st.write(f"- 收入: {income_count} 条")
                        st.write(f"- 支出: {expense_count} 条")
                
                # 显示无法分类的账单 - 直接集成分类功能
                if unclassified_bills:
                    st.subheader('⚠️ 需要手动分类的账单')
                    st.warning(f"共 {len(unclassified_bills)} 条需要手动确认分类")
                    st.info("💡 提示：可以从下拉框选择分类，也可以直接输入自定义分类")
                    
                    # 获取所有可用的分类
                    income_categories = [cat.value for cat in BillCategory.Income]
                    expense_categories = [cat.value for cat in BillCategory.Expense]
                    all_categories = income_categories + expense_categories
                    
                    # 初始化 session state
                    if 'wechat_classifications' not in st.session_state:
                        st.session_state.wechat_classifications = {}
                    
                    # 使用紧凑的表格布局
                    # 创建表头
                    header_cols = st.columns([0.4, 1.2, 1.6, 0.7, 1.6, 0.6, 1.2, 1.2, 0.5])
                    header_cols[0].markdown("**序号**")
                    header_cols[1].markdown("**交易时间**")
                    header_cols[2].markdown("**商品**")
                    header_cols[3].markdown("**金额**")
                    header_cols[4].markdown("**交易对方**")
                    header_cols[5].markdown("**类型**")
                    header_cols[6].markdown("**选择分类**")
                    header_cols[7].markdown("**或输入分类**")
                    header_cols[8].markdown("**状态**")
                    
                    # 添加表格样式
                    st.markdown("""
                    <style>
                    .stSelectbox > div > div {
                        padding: 0.25rem 0.5rem;
                    }
                    .stTextInput > div > div > input {
                        padding: 0.25rem 0.5rem;
                    }
                    </style>
                    """, unsafe_allow_html=True)
                    
                    # 为每条未分类账单创建一行（紧凑布局）
                    for idx, bill in enumerate(unclassified_bills):
                        cols = st.columns([0.4, 1.2, 1.6, 0.7, 1.6, 0.6, 1.2, 1.2, 0.5])
                        
                        transaction_type = bill['raw_data']['收/支']
                        type_emoji = "📤" if transaction_type == '支' else "📥"
                        
                        with cols[0]:
                            st.markdown(f"<div style='padding: 0.5rem 0;'>{idx + 1}</div>", unsafe_allow_html=True)
                        
                        with cols[1]:
                            st.markdown(f"<div style='padding: 0.5rem 0; font-size: 0.9rem;'>{bill['raw_data']['交易时间']}</div>", unsafe_allow_html=True)
                        
                        with cols[2]:
                            st.markdown(f"<div style='padding: 0.5rem 0; font-size: 0.9rem;'>{bill['raw_data']['商品']}</div>", unsafe_allow_html=True)
                        
                        with cols[3]:
                            # 去掉金额中的¥符号后再显示
                            amount_display = str(bill['raw_data']['金额(元)']).replace('¥', '').replace('￥', '').strip()
                            st.markdown(f"<div style='padding: 0.5rem 0; font-size: 0.9rem;'>¥{amount_display}</div>", unsafe_allow_html=True)
                        
                        with cols[4]:
                            st.markdown(f"<div style='padding: 0.5rem 0; font-size: 0.9rem;'>{bill['raw_data']['交易对方']}</div>", unsafe_allow_html=True)
                        
                        with cols[5]:
                            st.markdown(f"<div style='padding: 0.5rem 0; font-size: 0.85rem;'>{type_emoji}{transaction_type}</div>", unsafe_allow_html=True)
                        
                        with cols[6]:
                            selected_category = st.selectbox(
                                '选择',
                                [''] + all_categories,
                                key=f"wechat_category_{idx}",
                                label_visibility="collapsed"
                            )
                        
                        with cols[7]:
                            custom_category = st.text_input(
                                '输入',
                                value='',
                                key=f"wechat_custom_{idx}",
                                label_visibility="collapsed",
                                placeholder="自定义"
                            )
                        
                        with cols[8]:
                            # 确定最终使用的分类（优先使用自定义）
                            final_category = custom_category if custom_category else selected_category
                            st.session_state.wechat_classifications[idx] = {
                                'bill': bill,
                                'category': final_category
                            }
                            
                            # 状态指示
                            if final_category:
                                st.markdown("<div style='padding: 0.5rem 0; color: green;'>✓</div>", unsafe_allow_html=True)
                            else:
                                st.markdown("<div style='padding: 0.5rem 0; color: #888;'>○</div>", unsafe_allow_html=True)
                    
                    st.markdown("---")
                    
                    # 显示分类汇总
                    classified_count = sum(1 for v in st.session_state.wechat_classifications.values() 
                                          if v.get('category'))
                    unclassified_count = len(unclassified_bills) - classified_count
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("✅ 已分类", classified_count)
                    with col2:
                        st.metric("⏳ 未分类", unclassified_count)
                    with col3:
                        st.metric("📊 总计", len(unclassified_bills))
                
                # 导入按钮
                col1, col2 = st.columns(2)
                
                with col1:
                    if processed_bills:
                        if st.button('🚀 导入可分类账单', type='primary', key='wechat_import_classified'):
                            success_count = self.wechat_processor.import_bills_to_database(processed_bills)
                            if success_count > 0:
                                st.success(f"✅ 成功导入 {success_count} 条账单！")
                                st.balloons()
                            else:
                                st.error("导入失败，请检查数据格式")
                    else:
                        st.info("暂无可自动分类的账单")
                
                with col2:
                    if unclassified_bills:
                        # 检查分类状态
                        classified_count = sum(1 for v in st.session_state.get('wechat_classifications', {}).values() 
                                              if v.get('category'))
                        
                        if classified_count > 0:
                            if st.button('✅ 导入手动分类账单', type='primary', key='wechat_import_manual'):
                                try:
                                    success_count = 0
                                    for idx, classification in st.session_state.wechat_classifications.items():
                                        if classification.get('category'):
                                            bill = classification['bill']
                                            transaction_type = bill['raw_data']['收/支']
                                            
                                            # 处理金额：去掉¥等特殊字符，只保留数字和小数点
                                            amount_str = str(bill['raw_data']['金额(元)']).replace('¥', '').replace('￥', '').strip()
                                            try:
                                                amount_value = float(amount_str)
                                            except ValueError:
                                                st.error(f"金额格式错误: {bill['raw_data']['金额(元)']}")
                                                logger.error(f"无法解析金额: {bill['raw_data']['金额(元)']}")
                                                continue
                                            
                                            if transaction_type == '收':
                                                bill_type = '收入'
                                                amount = amount_value
                                            else:
                                                bill_type = '支出'
                                                amount = -amount_value
                                            
                                            # 处理日期格式：将 "2026/1/1 12:20" 或 "2026-01-01" 转换为 "20260101"
                                            date_str = bill['raw_data']['交易时间']
                                            if ' ' in date_str:
                                                date_str = date_str.split()[0]  # 去掉时间部分
                                            # 替换所有可能的分隔符
                                            bill_date = date_str.replace('-', '').replace('/', '')
                                            # 确保格式为 YYYYMMDD (补零)
                                            if len(bill_date) < 8:
                                                try:
                                                    from datetime import datetime as dt
                                                    parsed_date = dt.strptime(date_str, '%Y/%m/%d')
                                                    bill_date = parsed_date.strftime('%Y%m%d')
                                                except:
                                                    try:
                                                        parsed_date = dt.strptime(date_str, '%Y-%m-%d')
                                                        bill_date = parsed_date.strftime('%Y%m%d')
                                                    except:
                                                        bill_date = date_str.replace('-', '').replace('/', '')
                                            
                                            classified_bill = {
                                                'bill_date': bill_date,
                                                'type': bill_type,
                                                'category': classification['category'],
                                                'amount': amount,
                                                'remark': f"{bill['raw_data']['商品']} - {bill['raw_data']['交易对方']}",
                                                'create_time': datetime.now()
                                            }
                                            result = self.db.insert_bill(classified_bill)
                                            if result:
                                                success_count += 1
                                    
                                    if success_count > 0:
                                        # 清空 session state
                                        del st.session_state.wechat_classifications
                                        st.success(f"✅ 成功导入 {success_count} 条手动分类账单！")
                                        st.balloons()
                                        st.info("💡 页面将在 2 秒后刷新...")
                                        import time
                                        time.sleep(2)
                                        st.rerun()
                                    else:
                                        st.error("导入失败，请检查数据")
                                except Exception as e:
                                    st.error(f"导入失败: {e}")
                                    logger.error(f"手动分类账单导入失败: {e}")
                        else:
                            st.warning("⚠️ 请先为账单选择或输入分类")
                    else:
                        st.success("✓ 所有账单已分类")
                
            except Exception as e:
                st.error(f"文件处理失败：{str(e)}")
                logger.error(f"微信账单导入失败: {e}")
    
    def _render_backup_db_status(self):
        """备份页：当前库状态"""
        target_db_name = 'bill_tracker'
        total_documents = 0
        db = self.db.client[target_db_name]
        collections = db.list_collection_names()

        cols = st.columns(min(len(collections) + 1, 4))
        for i, collection_name in enumerate(collections):
            count = db[collection_name].count_documents({})
            total_documents += count
            with cols[i % len(cols)]:
                st.metric(collection_name, f"{count:,} 条")
        with cols[-1]:
            st.metric('合计', f"{total_documents:,} 条")

    def _render_backup_result(self, backup_result, *, skipped_ok=False):
        """备份页：展示单次备份结果"""
        if backup_result.get('skipped', False):
            if skipped_ok:
                st.info('数据未发生变化，已跳过备份')
                st.caption(f"哈希: `{backup_result.get('current_hash', 'N/A')}`")
            return

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric('记录数', f"{backup_result.get('total_documents', 0):,}")
        with c2:
            st.metric('大小', f"{backup_result.get('file_size_mb', 0)} MB")
        with c3:
            st.metric('数据库', backup_result.get('total_databases', 1))

        path = backup_result.get('backup_path')
        if path:
            st.caption(f"文件: `{os.path.basename(path)}` · 哈希: `{backup_result.get('data_hash', 'N/A')}`")
            if os.path.exists(path):
                with open(path, 'rb') as f:
                    st.download_button(
                        '📥 下载此备份',
                        data=f.read(),
                        file_name=os.path.basename(path),
                        mime='application/json',
                        key=f"dl_{os.path.basename(path)}_{backup_result.get('data_hash', '')[:8]}",
                    )

    def _backup_tab_content(self):
        st.caption('仅在数据有变化时创建新快照；文件保存在 `data/snapshots/`，最多保留 5 份。')
        left, right = st.columns([1, 1])
        with left:
            st.markdown('##### 智能备份')
            st.write('检测哈希变化，无变化则跳过。')
            if st.button('🚀 开始智能备份', type='primary', use_container_width=True, key='btn_smart_backup'):
                try:
                    with st.spinner('检查并备份...'):
                        result = self.db.backup_all_data(force=False)
                    if result.get('success'):
                        st.success('完成' if not result.get('skipped') else '无需新备份')
                        self._render_backup_result(result, skipped_ok=True)
                    else:
                        st.error(result.get('message', '备份失败'))
                except Exception as e:
                    st.error(f'备份失败: {e}')
        with right:
            st.markdown('##### 强制备份')
            st.write('忽略变化检测，立即生成快照。')
            if st.button('🔄 强制备份', use_container_width=True, key='btn_force_backup'):
                try:
                    with st.spinner('备份中...'):
                        result = self.db.backup_all_data(force=True)
                    if result.get('success'):
                        st.success('强制备份完成')
                        self._render_backup_result(result)
                    else:
                        st.error(result.get('message', '备份失败'))
                except Exception as e:
                    st.error(f'强制备份失败: {e}')

    def _restore_tab_content(self):
        self.db._ensure_data_layout()
        snapshot_files = self.db.list_backup_files(include_pre_restore=False)
        all_files = self.db.list_backup_files(include_pre_restore=True)
        pre_restore_only = [f for f in all_files if f.get('category') == 'pre_restore']

        if not snapshot_files:
            st.info('暂无快照，请先在「执行备份」中创建备份。')
            return

        left, right = st.columns([1, 1])
        with left:
            source_options = {
                f"{f['file_name']}（{f['total_documents']:,} 条）": f['backup_path']
                for f in snapshot_files
            }
            selected_label = st.selectbox('选择快照', options=list(source_options.keys()), key='restore_file_select')
            backup_path = source_options[selected_label]

            restore_mode = st.radio(
                '恢复模式',
                [RESTORE_MODE_BILLS_ONLY, RESTORE_MODE_MERGE, RESTORE_MODE_FULL_REPLACE],
                format_func=lambda m: {
                    RESTORE_MODE_BILLS_ONLY: '仅账单（推荐）',
                    RESTORE_MODE_MERGE: '合并（按 _id）',
                    RESTORE_MODE_FULL_REPLACE: '整库覆盖',
                }[m],
                key='restore_mode_radio',
            )
            include_users = False
            if restore_mode == RESTORE_MODE_FULL_REPLACE:
                include_users = st.checkbox('同时恢复 users', value=False, key='restore_include_users')

            confirm_text = st.text_input('输入 RESTORE 确认', placeholder='RESTORE', key='restore_confirm_input')
            if st.button('执行恢复', type='primary', use_container_width=True, key='restore_execute_btn'):
                if confirm_text != 'RESTORE':
                    st.error('请输入 RESTORE')
                else:
                    try:
                        with st.spinner('恢复中（会先自动做 pre_restore）...'):
                            result = self.db.restore_from_backup(backup_path, mode=restore_mode, include_users=include_users)
                        if result.get('success'):
                            st.success('恢复完成')
                            st.json(result.get('stats', {}))
                            st.rerun()
                        else:
                            st.error(result.get('message', '恢复失败'))
                    except Exception as e:
                        st.error(str(e))

        with right:
            preview = self.db.parse_backup_file(backup_path)
            if preview.get('success'):
                st.markdown('##### 快照预览')
                st.write(f"时间: {preview.get('backup_time', '')[:19].replace('T', ' ')}")
                st.write(f"记录: {preview['total_documents']:,} · {preview['file_size_mb']} MB")
                for cname, cstat in (preview.get('collection_stats') or {}).items():
                    line = f"- **{cname}**: {cstat.get('count', 0):,}"
                    if cstat.get('bill_date_min'):
                        line += f" ({cstat['bill_date_min']} ~ {cstat['bill_date_max']})"
                    st.write(line)
            st.info('恢复前会自动写入 `data/pre_restore/` 安全快照。')

        if pre_restore_only:
            st.divider()
            st.markdown('##### 误操作回滚')
            rollback_options = {f['file_name']: f['backup_path'] for f in pre_restore_only[:5]}
            rb_name = st.selectbox('pre_restore 快照', options=list(rollback_options.keys()), key='rollback_select')
            if st.button('回滚到此快照', key='rollback_btn'):
                try:
                    with st.spinner('回滚中...'):
                        rb_result = self.db.restore_from_backup(
                            rollback_options[rb_name],
                            mode=RESTORE_MODE_FULL_REPLACE,
                            include_users=True,
                        )
                    if rb_result.get('success'):
                        st.success('回滚完成')
                        st.rerun()
                    else:
                        st.error(rb_result.get('message'))
                except Exception as e:
                    st.error(str(e))

    def _snapshots_tab_content(self):
        snapshot_files = self.db.list_backup_files(include_pre_restore=False)
        if not snapshot_files:
            st.info(f"暂无快照 · 目录 `{get_data_root()}/snapshots/`")
            return

        st.caption(f"共 {len(snapshot_files)} 个文件（显示最新 10 个）")
        for i, meta in enumerate(snapshot_files[:10]):
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([3, 1, 2, 1])
                with c1:
                    st.write(f"{'🆕 ' if i == 0 else ''}**{meta['file_name']}**")
                with c2:
                    st.write(f"{meta['file_size_mb']} MB")
                with c3:
                    st.write(meta.get('backup_time', '')[:19].replace('T', ' '))
                with c4:
                    try:
                        with open(meta['backup_path'], 'rb') as f:
                            st.download_button('📥', f.read(), meta['file_name'], 'application/json', key=f"snap_dl_{i}")
                    except Exception:
                        st.write('—')

    def data_backup_page(self):
        """数据备份与恢复（Tab 布局）"""
        st.header('📦 数据备份与恢复')

        tab_overview, tab_backup, tab_restore, tab_files = st.tabs(
            ['概览', '执行备份', '数据恢复', '快照文件']
        )

        with tab_overview:
            st.markdown(
                """
| 目录 | 用途 |
|------|------|
| `data/snapshots/` | 全量快照，定时/手动备份，保留 5 份 |
| `data/pre_restore/` | 恢复前自动安全快照 |
| `data/yearly/` | 按年归档（阶段二） |
                """
            )
            try:
                self.db._ensure_data_layout()
                st.markdown('##### 当前数据库')
                self._render_backup_db_status()
            except Exception as e:
                st.error(f'读取库状态失败: {e}')

        with tab_backup:
            try:
                self._backup_tab_content()
            except Exception as e:
                st.error(f'备份功能异常: {e}')

        with tab_restore:
            try:
                self._restore_tab_content()
            except Exception as e:
                st.error(f'恢复功能异常: {e}')

        with tab_files:
            try:
                self._snapshots_tab_content()
            except Exception as e:
                st.warning(f'读取快照列表失败: {e}')


def main():
    try:
        app = BillTrackerApp()
        app.run()
    except Exception as e:
        logger.critical(f"应用运行失败: {e}")

if __name__ == '__main__':
    main()
