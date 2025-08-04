#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信账单导入脚本

使用方法:
    python import_wechat_bills.py <excel_file_path>
    
示例:
    python import_wechat_bills.py ./csv/tencent/20250721-20250803_parse.xlsx
"""

import sys
import os
import pandas as pd
from datetime import datetime
from loguru import logger
from database import BillDatabase
from wechat_bill_processor import WechatBillProcessor

class WechatBillImporter:
    """微信账单导入器"""
    
    def __init__(self):
        """初始化导入器"""
        self.db = BillDatabase()
        self.processor = WechatBillProcessor(self.db)
        
        # 配置日志
        log_dir = os.path.join(os.path.dirname(__file__), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        logger.add(
            os.path.join(log_dir, 'wechat_import_{time:YYYY-MM-DD}.log'),
            rotation='1 day',
            retention='30 days',
            level='INFO',
            format="{time} | {level} | {message}"
        )
    
    def read_wechat_excel(self, file_path):
        """读取微信账单Excel文件"""
        try:
            logger.info(f"开始读取微信账单文件: {file_path}")
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            # 读取Excel文件
            df = pd.read_excel(file_path)
            
            # 验证必要的列
            required_columns = ['交易时间', '交易对方', '商品', '收/支', '金额(元)']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise ValueError(f"Excel文件缺少必要的列: {missing_columns}")
            
            logger.info(f"成功读取Excel文件，共 {len(df)} 行数据")
            logger.info(f"文件列名: {df.columns.tolist()}")
            
            return df
            
        except Exception as e:
            logger.error(f"读取Excel文件失败: {e}")
            raise
    
    def process_wechat_bills(self, df, auto_classify=True):
        """处理微信账单"""
        return self.processor.process_wechat_bills(df, auto_classify)
    
    def import_bills_to_database(self, bills):
        """导入账单到数据库"""
        return self.processor.import_bills_to_database(bills)
    
    def import_from_file(self, file_path, auto_classify=True, preview_only=False):
        """从文件导入微信账单"""
        try:
            # 读取文件
            df = self.read_wechat_excel(file_path)
            
            # 处理账单数据
            bills, unclassified_count = self.process_wechat_bills(df, auto_classify)
            
            if preview_only:
                logger.info("预览模式，不导入数据库")
                return bills, unclassified_count, 0, 0
            
            # 导入到数据库
            success_count, error_count = self.import_bills_to_database(bills)
            
            # 输出统计信息
            logger.info(f"导入完成统计:")
            logger.info(f"  - 总处理: {len(bills)} 条")
            logger.info(f"  - 成功导入: {success_count} 条")
            logger.info(f"  - 导入失败: {error_count} 条")
            logger.info(f"  - 未分类: {unclassified_count} 条")
            
            return bills, unclassified_count, success_count, error_count
            
        except Exception as e:
            logger.error(f"导入微信账单失败: {e}")
            raise

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法: python import_wechat_bills.py <excel_file_path> [--preview]")
        print("示例: python import_wechat_bills.py ./csv/tencent/20250721-20250803_parse.xlsx")
        print("预览模式: python import_wechat_bills.py ./csv/tencent/20250721-20250803_parse.xlsx --preview")
        sys.exit(1)
    
    file_path = sys.argv[1]
    preview_only = '--preview' in sys.argv
    
    try:
        importer = WechatBillImporter()
        bills, unclassified_count, success_count, error_count = importer.import_from_file(
            file_path, 
            auto_classify=True, 
            preview_only=preview_only
        )
        
        if preview_only:
            print(f"\n=== 预览结果 ===")
            print(f"共处理 {len(bills)} 条账单")
            print(f"未分类 {unclassified_count} 条")
            
            # 显示前5条数据
            print(f"\n前5条数据预览:")
            for i, bill in enumerate(bills[:5]):
                print(f"{i+1}. {bill}")
        else:
            print(f"\n=== 导入完成 ===")
            print(f"总处理: {len(bills)} 条")
            print(f"成功导入: {success_count} 条")
            print(f"导入失败: {error_count} 条")
            print(f"未分类: {unclassified_count} 条")
        
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()