#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
支付宝账单处理器

提供支付宝账单的通用处理功能，包括数据处理、分类和数据库导入
"""

import pandas as pd
from datetime import datetime
from database import BillDatabase
from loguru import logger
from bill_classifier import UniversalBillClassifier


class AlipayBillProcessor:
    """支付宝账单处理器"""
    
    def __init__(self, db=None):
        """初始化处理器
        
        Args:
            db: 数据库实例，如果不提供则创建新实例
        """
        self.db = db if db is not None else BillDatabase()
    
    def classify_alipay_bill(self, row):
        """根据规则自动分类支付宝账单"""
        return UniversalBillClassifier.classify_alipay_bill(row)
    
    def process_alipay_bills(self, df, include_raw_data=False):
        """处理支付宝账单数据，进行自动分类
        
        Args:
            df: 包含支付宝账单数据的DataFrame
            include_raw_data: 是否在结果中包含原始数据（用于Web界面显示）
            
        Returns:
            tuple: (processed_bills, unclassified_bills)
        """
        processed_bills = []
        unclassified_bills = []
        
        for _, row in df.iterrows():
            try:
                # 解析时间格式
                create_time = pd.to_datetime(row['创建时间'])
                bill_date = create_time.strftime('%Y%m%d')
                
                # 基本账单信息
                bill_data = {
                    'bill_date': bill_date,
                    'type': '支出',
                    'amount': -float(row['订单金额(元)']),  # 支出为负数
                    'remark': str(row['商品名称']),
                    'create_time': datetime.now()
                }
                
                # 如果需要包含原始数据（用于Web界面）
                if include_raw_data:
                    bill_data['raw_data'] = row.to_dict()
                
                # 自动分类逻辑
                category = self.classify_alipay_bill(row)
                
                if category:
                    bill_data['category'] = category
                    processed_bills.append(bill_data)
                else:
                    if include_raw_data:
                        # Web界面格式：直接添加到未分类列表
                        unclassified_bills.append(bill_data)
                    else:
                        # 命令行格式：包装在字典中
                        unclassified_bills.append({
                            'bill_data': bill_data,
                            'raw_data': row.to_dict()
                        })
                        
            except Exception as e:
                logger.error(f"处理账单行失败: {e}, 数据: {row.to_dict()}")
                continue
        
        return processed_bills, unclassified_bills
    
    def import_bills_to_database(self, bills, return_failed_count=False):
        """批量导入账单到数据库
        
        Args:
            bills: 要导入的账单列表
            return_failed_count: 是否返回失败计数（用于命令行界面）
            
        Returns:
            int or tuple: 成功导入的数量，或 (成功数量, 失败数量)
        """
        success_count = 0
        failed_count = 0
        
        for bill in bills:
            try:
                # 移除raw_data字段，避免存储到数据库
                bill_to_insert = {k: v for k, v in bill.items() if k != 'raw_data'}
                self.db.insert_bill(bill_to_insert)
                success_count += 1
            except Exception as e:
                logger.error(f"导入单条账单失败: {e}, 账单数据: {bill}")
                failed_count += 1
                continue
        
        if return_failed_count:
            return success_count, failed_count
        else:
            return success_count