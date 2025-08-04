import pandas as pd
from datetime import datetime
from loguru import logger
from bill_classifier import UniversalBillClassifier

class WechatBillProcessor:
    """微信账单处理器"""
    
    def __init__(self, database=None):
        """初始化微信账单处理器"""
        self.db = database
    
    def classify_wechat_bill(self, row):
        """分类微信账单"""
        return UniversalBillClassifier.classify_wechat_bill(row)
    
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