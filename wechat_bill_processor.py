import pandas as pd
from datetime import datetime
from loguru import logger

class WechatBillClassifier:
    """微信账单分类器"""
    
    @staticmethod
    def classify_wechat_bill(row):
        """根据规则自动分类微信账单"""
        product_name = str(row['商品'])
        counterpart = str(row['交易对方'])
        category_field = str(row['分类']) if pd.notna(row['分类']) and row['分类'].strip() else ''
        
        # 如果Excel中已有分类，直接使用
        if category_field:
            return category_field
        
        # 交易对方名称映射表
        counterpart_mapping = {
            '快剪': '美妆',
            '深圳市微泊云科技有限公司': '停车费',
            '华敏物业': '停车费',
            '闪动体育科技': '羽毛球',
            '壳牌': '小车加油',
            'Coriander. 京新海球馆 店长': '羽毛球教学场地',
            '滴滴出行': '交通',
            '哈啰出行': '交通',
            '美团': '餐饮',
            '饿了么': '餐饮',
            '星巴克': '餐饮',
            '肯德基': '餐饮',
            '麦当劳': '餐饮',
            '永辉超市': '日用品',
            '沃尔玛': '日用品',
            '家乐福': '日用品'
        }
        
        # 按交易对方分类
        for company, category in counterpart_mapping.items():
            if company in counterpart:
                return category
        
        # 商品名称关键词映射表
        product_keyword_mapping = {
            '交通': ['地铁', '公交', '打车', '出租车', '网约车', '共享单车'],
            '餐饮': ['外卖', '咖啡', '奶茶', '零食', '小吃', '餐厅', '饭店', '食堂', '快餐', '餐饮店'],
            '日用品': ['超市', '便利店', '购物', '日用', '生活用品'],
            '服饰': ['衣服', '鞋子', '包包', '配饰'],
            '运动健身': ['健身', '游泳', '运动', '球类'],
            '羽毛球': ['羽毛球', '羽毛球馆'],
            '停车费': ['停车缴费'],
        }
        
        # 按商品名称分类
        for category, keywords in product_keyword_mapping.items():
            if any(keyword in product_name for keyword in keywords):
                return category
        
        # 无法分类
        return None

class WechatBillProcessor:
    """微信账单处理器"""
    
    def __init__(self, database=None):
        """初始化微信账单处理器"""
        self.db = database
    
    def classify_wechat_bill(self, row):
        """分类微信账单"""
        return WechatBillClassifier.classify_wechat_bill(row)
    
    def process_wechat_bills(self, df, auto_classify=True, include_raw_data=False):
        """处理微信账单数据"""
        try:
            processed_bills = []
            unclassified_bills = []
            unclassified_count = 0
            
            for _, row in df.iterrows():
                # 解析金额
                amount_str = str(row['金额(元)']).replace('¥', '').replace(',', '')
                try:
                    amount = float(amount_str)
                except ValueError:
                    logger.warning(f"无法解析金额: {amount_str}")
                    continue
                
                # 根据收/支类型确定金额正负
                transaction_type = str(row['收/支']).strip()
                if transaction_type in ['支出', '支 出']:
                    amount = -abs(amount)  # 支出为负数
                    bill_type = '支出'
                elif transaction_type in ['收入', '收 入']:
                    amount = abs(amount)   # 收入为正数
                    bill_type = '收入'
                else:
                    logger.warning(f"未知的收支类型: {transaction_type}")
                    continue
                
                # 解析交易时间
                try:
                    if isinstance(row['交易时间'], str):
                        transaction_time = datetime.strptime(row['交易时间'], '%Y-%m-%d %H:%M:%S')
                    else:
                        transaction_time = row['交易时间']
                    bill_date = transaction_time.strftime('%Y%m%d')
                except Exception as e:
                    logger.warning(f"无法解析交易时间: {row['交易时间']}, 错误: {e}")
                    continue
                
                # 自动分类
                category = None
                if auto_classify:
                    category = self.classify_wechat_bill(row)
                
                # 构建账单数据
                bill_data = {
                    'bill_date': bill_date,
                    'type': bill_type,
                    'category': category or '未分类',
                    'amount': amount,
                    'transaction_type': 'income' if bill_type == '收入' else 'expense',
                    'remark': f"微信-{row['交易对方']}-{row['商品']}",
                    # 'create_time': transaction_time
                    'create_time': datetime.now()
                }
                
                # 如果需要原始数据，添加原始数据字段
                if include_raw_data:
                    bill_data['raw_data'] = {
                        '交易时间': str(row['交易时间']),
                        '交易对方': str(row['交易对方']),
                        '商品': str(row['商品']),
                        '收/支': str(row['收/支']),
                        '金额(元)': str(row['金额(元)']),
                        '分类': str(row.get('分类', ''))
                    }
                
                # 根据是否有分类决定放入哪个列表
                if category:
                    processed_bills.append(bill_data)
                else:
                    unclassified_bills.append(bill_data)
                    unclassified_count += 1
            
            logger.info(f"处理完成，共处理 {len(processed_bills)} 条账单，未分类 {unclassified_count} 条")
            return processed_bills, unclassified_bills
            
        except Exception as e:
            logger.error(f"处理微信账单失败: {e}")
            raise
    
    def import_bills_to_database(self, bills, return_failed_count=False):
        """批量导入账单到数据库
        
        Args:
            bills: 要导入的账单列表
            return_failed_count: 是否返回失败计数（用于命令行界面）
            
        Returns:
            int or tuple: 成功导入的数量，或 (成功数量, 失败数量)
        """
        if not self.db:
            raise ValueError("数据库连接未初始化")
        
        success_count = 0
        error_count = 0
        
        for bill in bills:
            try:
                # 移除raw_data字段，避免存储到数据库
                bill_to_insert = {k: v for k, v in bill.items() if k != 'raw_data'}
                self.db.insert_bill(bill_to_insert)
                success_count += 1
            except Exception as e:
                logger.error(f"导入账单失败: {bill}, 错误: {e}")
                error_count += 1
        
        logger.info(f"导入完成，成功 {success_count} 条，失败 {error_count} 条")
        
        if return_failed_count:
            return success_count, error_count
        else:
            return success_count