#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
支付宝账单导入脚本

使用方法：
1. 将支付宝账单CSV文件放在 csv/ali/ 目录下
2. 运行脚本：python import_alipay_bills.py [文件名]
3. 如果不指定文件名，将导入 csv/ali/zfb-bill.csv

示例：
    python import_alipay_bills.py
    python import_alipay_bills.py my-alipay-bill.csv
"""

import sys
import os
import pandas as pd
from datetime import datetime
from database import BillDatabase
from loguru import logger
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class AlipayBillImporter:
    def __init__(self):
        """初始化导入器"""
        self.db = BillDatabase()
        
        # 配置日志
        log_dir = os.path.join(os.path.dirname(__file__), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        logger.add(
            os.path.join(log_dir, 'alipay_import_{time:YYYY-MM-DD}.log'),
            rotation='1 day',
            retention='30 days',
            level='INFO',
            format="{time} | {level} | {message}"
        )
    
    def classify_alipay_bill(self, row):
        """根据规则自动分类支付宝账单"""
        product_name = str(row['商品名称'])
        counterpart = str(row['对方名称'])
        category_field = str(row['分类']) if pd.notna(row['分类']) and row['分类'].strip() else ''
        
        # 如果CSV中已有分类，直接使用
        if category_field:
            return category_field
        
        # 按对方名称分类
        if '成都地铁运营有限公司' in counterpart:
            return '交通'
        elif '四川乡村基餐饮有限公司' in counterpart:
            return '餐饮'
        
        # 按商品名称分类
        if any(keyword in product_name for keyword in ['羽毛球', '羽毛球馆']):
            return '羽毛球'
        elif any(keyword in product_name for keyword in ['哈啰单车', '哈啰']):
            return '交通'
        elif any(keyword in product_name for keyword in ['外卖订单', '咖啡', '奶茶', '零食', '小吃']):
            return '餐饮'
        elif any(keyword in product_name for keyword in ['店内购物', '满彭菜场', '集刻便利店']):
            return '日用品'
        
        # 无法分类
        return None
    
    def process_alipay_bills(self, df):
        """处理支付宝账单数据，进行自动分类"""
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
                
                # 自动分类逻辑
                category = self.classify_alipay_bill(row)
                
                if category:
                    bill_data['category'] = category
                    processed_bills.append(bill_data)
                else:
                    unclassified_bills.append({
                        'bill_data': bill_data,
                        'raw_data': row.to_dict()
                    })
                    
            except Exception as e:
                logger.error(f"处理账单行失败: {e}, 数据: {row.to_dict()}")
                continue
        
        return processed_bills, unclassified_bills
    
    def import_bills_to_database(self, bills):
        """批量导入账单到数据库"""
        success_count = 0
        failed_count = 0
        
        for bill in bills:
            try:
                self.db.insert_bill(bill)
                success_count += 1
            except Exception as e:
                logger.error(f"导入单条账单失败: {e}, 账单数据: {bill}")
                failed_count += 1
                continue
        
        return success_count, failed_count
    
    def import_from_file(self, file_path):
        """从文件导入支付宝账单"""
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                print(f"❌ 错误：文件 {file_path} 不存在")
                return False
            
            print(f"📂 正在读取文件：{file_path}")
            
            # 读取CSV文件
            df = pd.read_csv(file_path)
            
            # 验证文件格式
            required_columns = ['创建时间', '商品名称', '订单金额(元)', '对方名称', '分类']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                print(f"❌ 错误：文件格式不正确！缺少以下列：{', '.join(missing_columns)}")
                return False
            
            print(f"📊 文件验证通过，共发现 {len(df)} 条账单记录")
            
            # 处理和分类账单
            processed_bills, unclassified_bills = self.process_alipay_bills(df)
            
            # 显示分类结果
            print(f"\n📈 分类结果：")
            print(f"✅ 可自动分类：{len(processed_bills)} 条")
            print(f"⚠️  需要手动分类：{len(unclassified_bills)} 条")
            
            if processed_bills:
                # 显示分类统计
                category_stats = {}
                for bill in processed_bills:
                    category = bill['category']
                    category_stats[category] = category_stats.get(category, 0) + 1
                
                print("\n📊 分类统计：")
                for category, count in category_stats.items():
                    print(f"  - {category}: {count} 条")
                
                total_amount = sum(bill['amount'] for bill in processed_bills)
                print(f"  - 总金额: ¥{abs(total_amount):.2f}")
            
            # 显示无法分类的账单
            if unclassified_bills:
                print("\n⚠️  以下账单无法自动分类，需要手动确认：")
                for i, item in enumerate(unclassified_bills[:5], 1):  # 只显示前5条
                    raw_data = item['raw_data']
                    print(f"  {i}. {raw_data['创建时间']} | {raw_data['商品名称']} | ¥{raw_data['订单金额(元)']} | {raw_data['对方名称']}")
                
                if len(unclassified_bills) > 5:
                    print(f"  ... 还有 {len(unclassified_bills) - 5} 条未显示")
                
                print("\n💡 建议：请在Web界面中处理这些未分类的账单")
            
            # 询问是否导入
            if processed_bills:
                while True:
                    choice = input(f"\n🤔 是否导入 {len(processed_bills)} 条可分类账单到数据库？(y/n): ").lower().strip()
                    if choice in ['y', 'yes', '是']:
                        print("\n🚀 开始导入账单...")
                        success_count, failed_count = self.import_bills_to_database(processed_bills)
                        
                        print(f"\n📊 导入结果：")
                        print(f"✅ 成功导入：{success_count} 条")
                        if failed_count > 0:
                            print(f"❌ 导入失败：{failed_count} 条")
                        
                        logger.info(f"支付宝账单导入完成：成功 {success_count} 条，失败 {failed_count} 条")
                        return True
                    elif choice in ['n', 'no', '否']:
                        print("❌ 取消导入")
                        return False
                    else:
                        print("请输入 y 或 n")
            else:
                print("\n❌ 没有可导入的账单")
                return False
                
        except Exception as e:
            print(f"❌ 导入失败：{str(e)}")
            logger.error(f"支付宝账单导入失败: {e}")
            return False

def main():
    """主函数"""
    print("🏦 支付宝账单导入工具")
    print("=" * 50)
    
    # 获取文件路径
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        if not filename.endswith('.csv'):
            filename += '.csv'
        file_path = os.path.join('csv', 'ali', filename)
    else:
        file_path = os.path.join('csv', 'ali', 'zfb-bill.csv')
    
    # 创建导入器并执行导入
    importer = AlipayBillImporter()
    
    try:
        success = importer.import_from_file(file_path)
        if success:
            print("\n🎉 导入完成！")
        else:
            print("\n❌ 导入失败或被取消")
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断操作")
    except Exception as e:
        print(f"\n❌ 程序执行出错：{str(e)}")
        logger.error(f"程序执行出错: {e}")

if __name__ == '__main__':
    main()