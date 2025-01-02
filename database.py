import pymongo
from datetime import datetime
import pandas as pd
from loguru import logger
import os
from bill_types import BillCategory
from datetime import timedelta

# 配置日志
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)

# 获取本机IP地址的函数
def get_client_ip():
    try:
        import socket
        return socket.gethostbyname(socket.gethostname())
    except Exception as e:
        logger.warning(f"获取IP地址失败: {e}")
        return "Unknown"

logger.add(os.path.join(log_dir, 'bill_database_{time:YYYY-MM-DD}.log'), 
           rotation='1 day',  # 按天切割
           retention='30 days',  # 保留最近7天的日志
           level='INFO',  # 日志级别
           format="{time} | {level} | IP: {extra[ip]} | {message}"  # 自定义日志格式
)

class BillDatabase:
    def __init__(self, host='localhost', port=27017, db_name='bill_tracker'):
        """
        初始化MongoDB数据库连接
        
        :param host: MongoDB主机地址
        :param port: MongoDB端口
        :param db_name: 数据库名称
        """
        try:
            self.client = pymongo.MongoClient(host, port)
            self.db = self.client[db_name]
            self.collection = self.db['bills']
            
            # 创建索引以提高查询性能
            self.collection.create_index([('bill_date', pymongo.ASCENDING)])
            self.collection.create_index([('type', pymongo.ASCENDING)])
            
            logger.info(f"成功连接到MongoDB数据库: {host}:{port}/{db_name}", extra={"ip": get_client_ip()})
        except Exception as e:
            logger.error(f"数据库连接失败: {e}", extra={"ip": get_client_ip()})
            raise
    
    def insert_bill(self, bill_date, bill_type, bill_category, amount, remark):
        """
        插入新的账单记录
        
        :param bill_date: 账单发生日期 (格式: 20250102)
        :param bill_type: 账单类型 (收入/支出)
        :param bill_category: 账单具体分类
        :param amount: 金额
        :param remark: 备注
        :return: 插入的记录ID
        """
        try:
            # 验证账单类型和分类
            if bill_type == '收入':
                if not isinstance(bill_category, BillCategory.Income):
                    raise ValueError("无效的收入类型")
            elif bill_type == '支出':
                if not isinstance(bill_category, BillCategory.Expense):
                    raise ValueError("无效的支出类型")
            
            bill_data = {
                'bill_date': int(bill_date),  # 使用整数存储日期
                'type': bill_type,
                'category': bill_category.value,
                'amount': float(amount),
                'remark': remark,
                'create_time': datetime.now()  # 创建时间使用datetime
            }
            
            result = self.collection.insert_one(bill_data)
            logger.info(f"成功插入账单: {bill_data}", extra={"ip": get_client_ip()})
            return result.inserted_id
        except Exception as e:
            logger.error(f"插入账单失败: {e}", extra={"ip": get_client_ip()})
            raise
    
    def get_bills_by_year(self, year):
        """
        获取特定年份的所有账单
        
        :param year: 年份 (如 2025)
        :return: DataFrame格式的账单数据
        """
        try:
            start_date = int(f"{year}0101")
            end_date = int(f"{year}1231")
            
            bills = list(self.collection.find({
                'bill_date': {
                    '$gte': start_date,
                    '$lte': end_date
                }
            }))
            
            return pd.DataFrame(bills)
        except Exception as e:
            logger.error(f"获取{year}年账单失败: {e}", extra={"ip": get_client_ip()})
            raise
    
    def get_annual_summary(self, year):
        """
        获取年度收支汇总
        
        :param year: 年份
        :return: 收入、支出总计的字典
        """
        try:
            bills = self.get_bills_by_year(year)
            
            income_total = bills[bills['type'] == '收入']['amount'].sum()
            expense_total = bills[bills['type'] == '支出']['amount'].sum()
            
            summary = {
                'income': income_total,
                'expense': expense_total,
                'net': income_total - expense_total
            }
            
            logger.info(f"{year}年度财务总结: {summary}", extra={"ip": get_client_ip()})
            return summary
        except Exception as e:
            logger.error(f"获取{year}年度总结失败: {e}", extra={"ip": get_client_ip()})
            raise

    def query_bills(self, 
                  start_date=None, 
                  end_date=None, 
                  bill_type=None, 
                  bill_category=None, 
                  min_amount=None, 
                  max_amount=None, 
                  remark=None):
        """
        多条件灵活查询账单
        
        :param start_date: 开始日期 (格式: 20250102)
        :param end_date: 结束日期 (格式: 20250102)
        :param bill_type: 账单类型 (收入/支出)
        :param bill_category: 账单分类
        :param min_amount: 最小金额
        :param max_amount: 最大金额
        :param remark: 备注关键词
        :return: DataFrame格式的账单数据
        """
        try:
            # 构建查询条件
            query = {}
            
            # 日期范围查询
            if start_date and end_date:
                query['bill_date'] = {
                    '$gte': int(start_date),
                    '$lte': int(end_date)
                }
            
            # 账单类型
            if bill_type:
                query['type'] = bill_type
            
            # 账单分类
            if bill_category:
                query['category'] = bill_category
            
            # 金额范围
            amount_query = {}
            if min_amount is not None:
                amount_query['$gte'] = float(min_amount)
            if max_amount is not None:
                amount_query['$lte'] = float(max_amount)
            
            if amount_query:
                query['amount'] = amount_query
            
            # 备注模糊查询
            if remark:
                query['remark'] = {'$regex': remark, '$options': 'i'}
            
            # 执行查询
            bills = list(self.collection.find(query))
            
            df = pd.DataFrame(bills)
            logger.info(f"查询账单成功，共{len(bills)}条记录", extra={"ip": get_client_ip()})
            return df
        except Exception as e:
            logger.error(f"账单查询失败: {e}", extra={"ip": get_client_ip()})
            raise

    def get_period_summary(self, period_type='week', start_date=None):
        """
        获取不同周期的财务总结
        
        :param period_type: 周期类型 ('week', 'month', 'quarter', 'year')
        :param start_date: 开始日期 (格式: 20250102)
        :return: 财务总结字典
        """
        try:
            # 如果没有提供开始日期，使用当前日期
            if not start_date:
                start_date = int(datetime.now().strftime('%Y%m%d'))
            
            # 根据周期类型计算开始和结束日期
            if period_type == 'week':
                # 获取本周开始和结束日期
                start = datetime.strptime(str(start_date), '%Y%m%d')
                week_start = start - timedelta(days=start.weekday())
                week_end = week_start + timedelta(days=6)
                
                start_date = int(week_start.strftime('%Y%m%d'))
                end_date = int(week_end.strftime('%Y%m%d'))
            
            elif period_type == 'month':
                # 获取本月开始和结束日期
                start_date = int(str(start_date)[:6] + '01')
                end_date = int(str(start_date)[:6] + '31')
            
            elif period_type == 'quarter':
                # 获取本季度开始和结束日期
                year = int(str(start_date)[:4])
                quarter = (int(str(start_date)[4:6]) - 1) // 3 + 1
                
                quarter_map = {
                    1: (f'{year}0101', f'{year}0331'),
                    2: (f'{year}0401', f'{year}0630'),
                    3: (f'{year}0701', f'{year}0930'),
                    4: (f'{year}1001', f'{year}1231')
                }
                
                start_date, end_date = map(int, quarter_map[quarter])
            
            elif period_type == 'year':
                # 获取本年开始和结束日期
                year = int(str(start_date)[:4])
                start_date = int(f'{year}0101')
                end_date = int(f'{year}1231')
            
            # 查询该周期的账单
            bills = self.query_bills(start_date=start_date, end_date=end_date)
            
            # 计算总结
            income_total = bills[bills['type'] == '收入']['amount'].sum()
            expense_total = bills[bills['type'] == '支出']['amount'].sum()
            
            summary = {
                'start_date': start_date,
                'end_date': end_date,
                'income': income_total,
                'expense': expense_total,
                'net': income_total - expense_total
            }
            
            logger.info(f"{period_type}财务总结: {summary}", extra={"ip": get_client_ip()})
            return summary
        except Exception as e:
            logger.error(f"{period_type}财务总结获取失败: {e}", extra={"ip": get_client_ip()})
            raise

    def close(self):
        """关闭数据库连接"""
        try:
            self.client.close()
            logger.info("数据库连接已关闭", extra={"ip": get_client_ip()})
        except Exception as e:
            logger.error(f"关闭数据库连接时发生错误: {e}", extra={"ip": get_client_ip()})
            raise
