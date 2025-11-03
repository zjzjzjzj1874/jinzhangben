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
    def __init__(self, host=None, port=27017, db_name=None):
        """
        初始化数据库连接
        
        :param host: MongoDB主机地址，默认为None，使用环境变量或容器内默认地址
        :param port: MongoDB端口
        :param db_name: 数据库名称，默认为None，优先使用环境变量MONGO_DB_NAME
        """
        try:
            # 优先使用环境变量中的数据库名称
            if db_name is None:
                db_name = os.getenv('MONGO_DB_NAME', 'bill_tracker')
                # db_name = os.getenv('MONGO_DB_NAME', 'bill_tracker_test')
            # 优先使用环境变量中的 MONGO_URI
            mongo_uri = os.getenv('MONGO_URI')
            
            if mongo_uri:
                # 使用环境变量中的连接字符串
                self.client = pymongo.MongoClient(mongo_uri)
            else:
                # 检查是否在容器内运行
                is_docker = os.path.exists('/.dockerenv')
                
                if is_docker:
                    # 容器内使用服务名
                    host = host or 'mongo'
                    self.client = pymongo.MongoClient(host, port)
                else:
                    # 本地开发使用 localhost
                    host = host or 'localhost'
                    port = 37017
                    self.client = pymongo.MongoClient(host, port)
            
            self.db = self.client[db_name]
            self.collection = self.db['bills']
            
            # 创建索引以提高查询性能
            self.collection.create_index([('bill_date', pymongo.ASCENDING)])
            self.collection.create_index([('type', pymongo.ASCENDING)])
            
            # 检查数据库连接状态
            try:
                self.client.admin.command('ping')
                logger.info(f"数据库连接成功: {db_name}")
            except Exception as e:
                logger.error(f"数据库连接测试失败: {e}")
            
            # 只在初始化时记录IP
            logger.info(f"成功连接到MongoDB数据库: {host}:{port}/{db_name}", extra={"ip": get_client_ip()})
        except Exception as e:
            logger.error(f"连接MongoDB失败: {e}")
            raise
    
    def insert_bill(self, bill_data):
        """
        插入新的账单记录
        
        :param bill_data: 账单数据字典
        :return: 插入结果
        """
        try:
            
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
            

            
            # 插入数据
            result = self.collection.insert_one(bill_data)
            
            # 记录日志
            logger.info(f"账单插入成功: {result.inserted_id}")
            
            return result.inserted_id
        
        except Exception as e:
            logger.error(f"账单插入失败: {e}")
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
            year_start = int(f"{year}0101")
            year_end = int(f"{year}1231")
            query = {
                '$expr': {
                    '$and': [
                        {'$gte': [{'$toInt': '$bill_date'}, year_start]},
                        {'$lte': [{'$toInt': '$bill_date'}, year_end]}
                    ]
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
            start_date_int = int(f"{year}0101")
            end_date_int = int(f"{year}1231")
            
            # 聚合管道
            pipeline = [
                {
                    '$match': {
                        '$expr': {
                            '$and': [
                                {'$gte': [{'$toInt': '$bill_date'}, start_date_int]},
                                {'$lte': [{'$toInt': '$bill_date'}, end_date_int]}
                            ]
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
                # 确保日期参数为整数格式进行数值比较
                start_date_int = int(start_date) if isinstance(start_date, str) else start_date
                end_date_int = int(end_date) if isinstance(end_date, str) else end_date
                
                # 使用$expr进行数值比较，将字符串转换为整数
                query['$expr'] = {
                    '$and': [
                        {'$gte': [{'$toInt': '$bill_date'}, start_date_int]},
                        {'$lte': [{'$toInt': '$bill_date'}, end_date_int]}
                    ]
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
            start_date_int = int(start_datetime.strftime('%Y%m%d'))
            end_date_int = int(end_datetime.strftime('%Y%m%d'))
            pipeline = [
                {
                    '$match': {
                        '$expr': {
                            '$and': [
                                {'$gte': [{'$toInt': '$bill_date'}, start_date_int]},
                                {'$lte': [{'$toInt': '$bill_date'}, end_date_int]}
                            ]
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
            year_start = int(f"{year}0101")
            year_end = int(f"{year}1231")
            pipeline = [
                # 匹配指定年份的账单
                {'$match': {
                    '$expr': {
                        '$and': [
                            {'$gte': [{'$toInt': '$bill_date'}, year_start]},
                            {'$lte': [{'$toInt': '$bill_date'}, year_end]}
                        ]
                    }
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
            year_start = int(f"{year}0101")
            year_end = int(f"{year}1231")
            pipeline = [
                # 匹配指定年份的账单
                {'$match': {
                    '$expr': {
                        '$and': [
                            {'$gte': [{'$toInt': '$bill_date'}, year_start]},
                            {'$lte': [{'$toInt': '$bill_date'}, year_end]}
                        ]
                    }
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

    def get_data_hash(self):
        """
        获取数据的哈希值，用于检测数据变化
        
        :return: 数据哈希值
        """
        try:
            import hashlib
            
            # 获取bill_tracker数据库的基本统计信息
            target_db_name = 'bill_tracker'
            db = self.client[target_db_name]
            collections = db.list_collection_names()
            
            hash_data = []
            for collection_name in collections:
                collection = db[collection_name]
                count = collection.count_documents({})
                
                # 获取最新和最旧记录的时间戳
                latest = list(collection.find().sort('_id', -1).limit(1))
                oldest = list(collection.find().sort('_id', 1).limit(1))
                
                latest_id = str(latest[0]['_id']) if latest else ''
                oldest_id = str(oldest[0]['_id']) if oldest else ''
                
                hash_data.append(f"{collection_name}:{count}:{latest_id}:{oldest_id}")
            
            # 生成哈希值
            hash_string = '|'.join(sorted(hash_data))
            return hashlib.md5(hash_string.encode()).hexdigest()
            
        except Exception as e:
            logger.error(f"获取数据哈希失败: {e}")
            return None
    
    def cleanup_old_backups(self, backup_dir, max_backups=5):
        """
        清理旧的备份文件，只保留最新的几份
        
        :param backup_dir: 备份目录
        :param max_backups: 最大保留备份数量
        """
        try:
            import glob
            import os
            
            # 获取所有备份文件
            backup_pattern = os.path.join(backup_dir, 'bills_backup_*.json')
            backup_files = glob.glob(backup_pattern)
            
            if len(backup_files) <= max_backups:
                return
            
            # 按修改时间排序，最新的在前
            backup_files.sort(key=os.path.getmtime, reverse=True)
            
            # 删除多余的备份文件
            files_to_delete = backup_files[max_backups:]
            for file_path in files_to_delete:
                try:
                    os.remove(file_path)
                    logger.info(f"删除旧备份文件: {os.path.basename(file_path)}")
                except Exception as e:
                    logger.error(f"删除备份文件失败 {file_path}: {e}")
                    
        except Exception as e:
            logger.error(f"清理备份文件失败: {e}")
    
    def check_backup_needed(self, backup_dir):
        """
        检查是否需要备份（基于数据变化）
        
        :param backup_dir: 备份目录
        :return: (是否需要备份, 当前哈希值, 上次哈希值)
        """
        try:
            import os
            import json
            import glob
            
            # 获取当前数据哈希
            current_hash = self.get_data_hash()
            if not current_hash:
                return True, None, None  # 无法获取哈希时，默认需要备份
            
            # 查找最新的备份文件
            backup_pattern = os.path.join(backup_dir, 'bills_backup_*.json')
            backup_files = glob.glob(backup_pattern)
            
            if not backup_files:
                return True, current_hash, None  # 没有备份文件，需要备份
            
            # 获取最新备份文件
            latest_backup = max(backup_files, key=os.path.getmtime)
            
            try:
                with open(latest_backup, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
                    last_hash = backup_data.get('backup_info', {}).get('data_hash')
                    
                    if last_hash == current_hash:
                        logger.info(f"数据未发生变化，跳过备份 (哈希: {current_hash})")
                        return False, current_hash, last_hash
                    else:
                        logger.info(f"检测到数据变化，需要备份 (旧哈希: {last_hash}, 新哈希: {current_hash})")
                        return True, current_hash, last_hash
                        
            except Exception as e:
                logger.warning(f"读取上次备份信息失败: {e}，将进行备份")
                return True, current_hash, None
                
        except Exception as e:
            logger.error(f"检查备份需求失败: {e}")
            return True, None, None  # 出错时默认需要备份

    def backup_all_data(self, backup_path=None, force=False):
        """
        备份所有数据到JSON文件
        
        :param backup_path: 备份文件路径，如果为None则自动生成
        :param force: 是否强制备份，忽略增量检测
        :return: 备份结果字典
        """
        try:
            import os
            import json
            from datetime import datetime
            
            # 确定备份目录
            if backup_path:
                backup_dir = os.path.dirname(backup_path)
            else:
                backup_dir = '/app/data'
            
            # 确保备份目录存在
            os.makedirs(backup_dir, exist_ok=True)
            
            # 检查是否需要备份（除非强制备份）
            if not force:
                need_backup, current_hash, last_hash = self.check_backup_needed(backup_dir)
                if not need_backup:
                    return {
                        'success': True,
                        'message': '数据未发生变化，跳过备份',
                        'skipped': True,
                        'current_hash': current_hash,
                        'last_hash': last_hash
                    }
            else:
                current_hash = self.get_data_hash()
            
            # 生成备份文件名
            if not backup_path:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = os.path.join(backup_dir, f'bills_backup_{timestamp}.json')
            
            # 只备份bill_tracker数据库
            target_db_name = 'bill_tracker'
            db = self.client[target_db_name]
            collections = db.list_collection_names()
            
            backup_data = {
                'backup_info': {
                    'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
                    'backup_time': datetime.now().isoformat(),
                    'database_name': target_db_name,
                    'version': '2.0',
                    'data_hash': current_hash  # 添加数据哈希
                },
                'databases': {}
            }
            
            total_records = 0
            
            # 备份指定数据库
            db_data = {'collections': {}}
            for collection_name in collections:
                collection = db[collection_name]
                documents = []
                
                for doc in collection.find():
                    # 转换ObjectId为字符串
                    if '_id' in doc:
                        doc['_id'] = str(doc['_id'])
                    documents.append(doc)
                
                db_data['collections'][collection_name] = {
                    'count': len(documents),
                    'documents': documents
                }
                total_records += len(documents)
                logger.info(f"备份集合 {target_db_name}.{collection_name}: {len(documents)} 条记录")
            
            backup_data['databases'][target_db_name] = db_data
            
            # 写入备份文件
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2, default=str)
            
            # 获取文件大小
            file_size = os.path.getsize(backup_path)
            file_size_mb = file_size / (1024 * 1024)
            
            # 清理旧备份文件
            self.cleanup_old_backups(backup_dir, max_backups=5)
            
            logger.info(f"数据备份完成: {backup_path}, 共{total_records}条记录, 文件大小: {file_size_mb:.2f}MB")
            
            return {
                'success': True,
                'message': f'备份完成: {os.path.basename(backup_path)}',
                'backup_path': backup_path,
                'total_databases': 1,
                'total_documents': total_records,
                'file_size': file_size,
                'file_size_mb': round(file_size_mb, 2),
                'data_hash': current_hash,
                'skipped': False
            }
            
        except Exception as e:
            logger.error(f"数据备份失败: {e}")
            return {
                'success': False,
                'message': f'备份失败: {str(e)}',
                'error': str(e)
            }

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
