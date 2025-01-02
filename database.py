import pymongo
from datetime import datetime
import pandas as pd
from loguru import logger
import os
from bill_types import BillCategory
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import math

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
        初始化数据库连接
        
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
            
            # 只在初始化时记录IP
            logger.info(f"成功连接到MongoDB数据库: {host}:{port}/{db_name}", extra={"ip": get_client_ip()})
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    def insert_bill(self, bill_data):
        """
        插入新的账单记录
        
        :param bill_data: 账单数据字典
        :return: 插入结果
        """
        try:
            # 打印详细的账单数据信息
            print("插入账单数据详情:")
            print("数据类型:", type(bill_data))
            print("数据内容:", bill_data)
            
            # 验证必填字段
            required_fields = ['bill_date', 'type', 'category', 'amount']
            for field in required_fields:
                if field not in bill_data:
                    raise ValueError(f"缺少必填字段: {field}")
            
            # 类型转换和验证
            try:
                # 确保日期是字符串且格式正确
                bill_data['bill_date'] = str(bill_data['bill_date'])
                
                # 确保金额是数字
                bill_data['amount'] = float(bill_data['amount'])
                
                # 可选字段处理
                if 'remark' not in bill_data:
                    bill_data['remark'] = ''
            except (ValueError, TypeError) as e:
                raise ValueError(f"数据类型转换错误: {e}")
            
            # 打印转换后的数据
            print("转换后的数据:", bill_data)
            
            # 插入数据
            result = self.collection.insert_one(bill_data)
            
            # 记录日志
            logger.info(f"账单插入成功: {result.inserted_id}")
            
            return result.inserted_id
        
        except Exception as e:
            # 详细的错误日志
            logger.error(f"账单插入失败: {e}")
            print(f"账单插入失败详细信息: {e}")
            print("完整账单数据:", bill_data)
            raise
    
    def get_bills_by_year(self, year, page=1, page_size=10):
        """
        获取指定年份的账单（分页）
        
        :param year: 年份
        :param page: 页码
        :param page_size: 每页记录数
        :return: 分页后的账单数据
        """
        try:
            # 构建年份查询条件
            query = {
                'bill_date': {
                    '$gte': f"{year}0101",
                    '$lte': f"{year}1231"
                }
            }
            
            # 执行分页查询
            result = self.paginate_query(
                query=query, 
                page=page, 
                page_size=page_size,
                sort_field='bill_date',
                sort_order=-1  # 按日期降序
            )
            
            logger.info(f"成功获取{year}年度账单，第{page}页，共{result['total_count']}条记录")
            return result
        
        except Exception as e:
            logger.error(f"{year}年度账单获取失败: {e}")
            raise
    
    def paginate_query(self, 
                query={}, 
                page=1, 
                page_size=10, 
                sort_field='bill_date', 
                sort_order=-1):
        """
        通用的分页查询方法
        
        :param query: MongoDB查询条件
        :param page: 页码，从1开始
        :param page_size: 每页记录数
        :param sort_field: 排序字段
        :param sort_order: 排序顺序，1为升序，-1为降序
        :return: 查询结果和总记录数
        """
        try:
            # 计算跳过的记录数
            skip = (page - 1) * page_size
            
            # 执行查询
            total_count = self.collection.count_documents(query)
            
            # 构建聚合管道
            pipeline = [
                {'$match': query},
                {'$sort': {sort_field: sort_order}},
                {'$skip': skip},
                {'$limit': page_size}
            ]
            
            # 执行查询
            results = list(self.collection.aggregate(pipeline))
            
            # 转换为DataFrame
            df = pd.DataFrame(results)
            
            # 确保数据类型正确
            if not df.empty:
                df['amount'] = df['amount'].astype(float)
                df['bill_date'] = df['bill_date'].astype(str)
            
            # 计算总页数
            total_pages = math.ceil(total_count / page_size)
            
            # 返回查询结果和分页信息
            return {
                'data': df,
                'total_count': total_count,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages
            }
        
        except Exception as e:
            logger.error(f"分页查询失败: {e}")
            raise
    
    def get_annual_summary(self, year):
        """
        获取指定年份的财务年度总结
        
        :param year: 年份
        :return: 包含年度收入、支出和净收益的字典
        """
        try:
            # 构建年份查询条件
            start_date = f"{year}0101"
            end_date = f"{year}1231"
            
            # 聚合管道
            pipeline = [
                {
                    '$match': {
                        'bill_date': {
                            '$gte': start_date,
                            '$lte': end_date
                        }
                    }
                },
                {
                    '$group': {
                        '_id': None,
                        'total_income': {
                            '$sum': {
                                '$cond': [
                                    {'$gt': ['$amount', 0]},  # 条件：金额大于0
                                    '$amount',               # 为真时求和
                                    0                        # 为假时为0
                                ]
                            }
                        },
                        'total_expense': {
                            '$sum': {
                                '$cond': [
                                    {'$lt': ['$amount', 0]},  # 条件：金额小于0
                                    {'$abs': '$amount'},      # 取绝对值
                                    0                         # 为假时为0
                                ]
                            }
                        }
                    }
                }
            ]
            
            # 执行聚合查询
            result = list(self.collection.aggregate(pipeline))
            
            # 处理查询结果
            if result and len(result) > 0:
                summary = result[0]
                return {
                    'income': summary['total_income'],
                    'expense': summary['total_expense'],
                    'net': summary['total_income'] - summary['total_expense']
                }
            else:
                # 如果没有数据，返回全0
                return {
                    'income': 0,
                    'expense': 0,
                    'net': 0
                }
        
        except Exception as e:
            logger.error(f"{year}年度财务总结获取失败: {e}")
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
        灵活的账单查询方法
        
        :param start_date: 开始日期 (格式: 20250102)
        :param end_date: 结束日期 (格式: 20250102)
        :param bill_type: 账单类型
        :param bill_category: 账单分类
        :param min_amount: 最小金额
        :param max_amount: 最大金额
        :param remark: 备注关键词
        :return: 查询结果DataFrame
        """
        try:
            # 构建查询条件
            query = {}
            
            # 日期范围查询
            if start_date and end_date:
                query['bill_date'] = {
                    '$gte': str(start_date),  # 大于等于开始日期
                    '$lte': str(end_date)     # 小于等于结束日期
                }
            
            # 类型查询
            if bill_type:
                query['type'] = bill_type
            
            # 分类查询
            if bill_category:
                query['category'] = bill_category
            
            # 金额范围查询
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
            
            # 转换为DataFrame
            df = pd.DataFrame(bills)
            
            # 确保数据类型正确
            if not df.empty:
                df['amount'] = df['amount'].astype(float)
                df['bill_date'] = df['bill_date'].astype(str)
            
            # 如果查询结果为空，返回空DataFrame
            if df.empty:
                return pd.DataFrame(columns=['bill_date', 'type', 'category', 'amount', 'remark'])
            
            # 对结果进行排序（按日期降序）
            df = df.sort_values('bill_date', ascending=False)
            
            logger.info(f"查询账单成功，共{len(bills)}条记录")
            return df
        except Exception as e:
            logger.error(f"账单查询失败: {e}")
            raise

    def get_period_summary(self, period_type='week', start_date=None):
        """
        获取指定周期的财务总结
        
        :param period_type: 周期类型，可选 'week', 'month', 'quarter', 'year'
        :param start_date: 开始日期，默认为当前日期
        :return: 周期财务总结字典
        """
        try:
            # 如果没有传入开始日期，使用当前日期
            if start_date is None:
                start_date = datetime.now().strftime('%Y%m%d')
            
            # 将开始日期转换为datetime对象
            start_datetime = datetime.strptime(start_date, '%Y%m%d')
            
            # 根据周期类型计算开始和结束日期
            if period_type == 'week':
                # 获取本周第一天（自然周）
                week_start = start_datetime - timedelta(days=start_datetime.weekday())
                end_datetime = week_start + timedelta(days=6)
                start_datetime = week_start
            elif period_type == 'month':
                # 获取本月第一天（自然月）
                month_start = start_datetime.replace(day=1)
                end_datetime = month_start + relativedelta(months=1) - timedelta(days=1)
                start_datetime = month_start
            elif period_type == 'quarter':
                # 获取本季度第一天（自然季）
                quarter_start = start_datetime.replace(
                    day=1, 
                    month=((start_datetime.month - 1) // 3) * 3 + 1
                )
                end_datetime = quarter_start + relativedelta(months=3) - timedelta(days=1)
                start_datetime = quarter_start
            elif period_type == 'year':
                # 获取本年第一天（自然年）
                year_start = start_datetime.replace(month=1, day=1)
                end_datetime = year_start.replace(month=12, day=31)
                start_datetime = year_start
            else:
                raise ValueError(f"不支持的周期类型: {period_type}")
            
            # 构建查询条件
            pipeline = [
                {
                    '$match': {
                        'bill_date': {
                            '$gte': start_datetime.strftime('%Y%m%d'),
                            '$lte': end_datetime.strftime('%Y%m%d')
                        }
                    }
                },
                {
                    '$group': {
                        '_id': '$type',  # 按账单类型分组
                        'total_amount': {'$sum': '$amount'}  # 计算每种类型的总金额
                    }
                }
            ]
            
            # 执行聚合查询
            result = list(self.collection.aggregate(pipeline))
            
            # 初始化收入和支出
            income_total = 0
            expense_total = 0
            
            # 分类汇总
            for item in result:
                if item['total_amount'] > 0:
                    income_total += item['total_amount']
                else:
                    expense_total += abs(item['total_amount'])
            
            # 构建总结
            summary = {
                'income': income_total,
                'expense': expense_total,
                'net': income_total - expense_total,
                'start_date': start_datetime.strftime('%Y%m%d'),
                'end_date': end_datetime.strftime('%Y%m%d')
            }
            
            logger.info(f"{period_type}财务总结: {summary}")
            return summary
        except Exception as e:
            logger.error(f"{period_type}财务总结获取失败: {e}")
            raise

    def get_category_summary(self, year, bill_type='all'):
        """
        获取指定年份的类别统计
        
        :param year: 统计年份
        :param bill_type: 统计类型 'income', 'expense', 或 'all'
        :return: DataFrame 包含类别和金额
        """
        try:
            # 构建聚合管道
            pipeline = [
                # 匹配指定年份的账单
                {'$match': {
                    'bill_date': {'$regex': f'^{year}'},
                }},
                # 根据账单类型过滤
                *([{'$match': {'amount': {'$gt': 0}}}] if bill_type == 'income' 
                  else [{'$match': {'amount': {'$lt': 0}}}] if bill_type == 'expense' 
                  else []),
                # 按类别分组并计算总金额
                {'$group': {
                    '_id': '$category',
                    'amount': {'$sum': {'$abs': '$amount'}}
                }},
                # 转换结果格式
                {'$project': {
                    'category': '$_id',
                    'amount': 1,
                    '_id': 0
                }},
                # 按金额降序排序
                {'$sort': {'amount': -1}}
            ]
            
            # 执行聚合查询
            result = list(self.collection.aggregate(pipeline))
            
            # 转换为DataFrame
            df = pd.DataFrame(result) if result else pd.DataFrame(columns=['category', 'amount'])
            
            return df
        
        except Exception as e:
            logger.error(f"类别统计查询失败: {e}")
            return pd.DataFrame(columns=['category', 'amount'])

    def get_monthly_summary(self, year):
        """
        获取指定年份的月度收支统计
        
        :param year: 统计年份
        :return: DataFrame 包含月份、收入和支出
        """
        try:
            # 构建聚合管道
            pipeline = [
                # 匹配指定年份的账单
                {'$match': {
                    'bill_date': {'$regex': f'^{year}'}
                }},
                # 按月份分组并计算收入和支出
                {'$group': {
                    '_id': {'$substr': ['$bill_date', 4, 2]},
                    'income': {
                        '$sum': {'$cond': [{'$gt': ['$amount', 0]}, '$amount', 0]}
                    },
                    'expense': {
                        '$sum': {'$cond': [{'$lt': ['$amount', 0]}, {'$abs': '$amount'}, 0]}
                    }
                }},
                # 转换结果格式
                {'$project': {
                    'month': {'$toInt': '$_id'},
                    'income': 1,
                    'expense': 1,
                    '_id': 0
                }},
                # 按月份排序
                {'$sort': {'month': 1}}
            ]
            
            # 执行聚合查询
            result = list(self.collection.aggregate(pipeline))
            
            # 转换为DataFrame
            df = pd.DataFrame(result) if result else pd.DataFrame(columns=['month', 'income', 'expense'])
            
            # 补全缺失月份
            all_months = pd.DataFrame({
                'month': range(1, 13)
            })
            df = all_months.merge(df, on='month', how='left').fillna(0)
            
            return df
        
        except Exception as e:
            logger.error(f"月度统计查询失败: {e}")
            return pd.DataFrame(columns=['month', 'income', 'expense'])

    def close(self):
        """
        关闭数据库连接
        """
        try:
            self.client.close()
            logger.info("数据库连接已关闭")
        except Exception as e:
            logger.error(f"关闭数据库连接时发生错误: {e}")
            raise
