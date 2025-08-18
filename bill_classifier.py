#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用账单分类器

提供微信和支付宝账单的统一分类功能
"""

import pandas as pd
from loguru import logger


class UniversalBillClassifier:
    """通用账单分类器"""
    
    # 通用交易对方名称映射表
    COUNTERPART_MAPPING = {
        # 交通相关
        '成都地铁运营有限公司': '交通',
        '滴滴出行科技有限公司': '交通',
        '滴滴出行': '交通',
        '哈啰出行': '交通',
        '成都天府通数字科技有限公司': '交通',
        
        # 餐饮相关
        '公司餐厅消费': '餐饮',
        '四川乡村基餐饮有限公司': '餐饮',
        '美团': '餐饮',
        '饿了么': '餐饮',
        '星巴克': '餐饮',
        '肯德基': '餐饮',
        '麦当劳': '餐饮',
        
        # 日用品相关
        '成都红旗连锁股份有限公司': '日用品',
        '四川舞东风超市连锁股份有限公司': '日用品',
        '四川永辉超市有限公司': '日用品',
        '永辉超市': '日用品',
        '沃尔玛': '日用品',
        '家乐福': '日用品',
        '淘宝平台商户': '日用品',
        
        # 停车费相关
        '深圳市微泊云科技有限公司': '停车费',
        '华敏物业': '停车费',
        '守权': '停车费',
        
        # 运动健身相关
        '闪动体育科技': '羽毛球',
        'Coriander. 京新海球馆 店长': '羽毛球教学场地',
        
        # 其他
        '快剪': '美妆',
        '壳牌': '小车加油',
    }
    
    # 通用商品名称关键词映射表
    PRODUCT_KEYWORD_MAPPING = {
        '交通': [
            '地铁', '公交', '打车', '出租车', '网约车', '共享单车',
            '哈啰单车', '哈啰', '天府通', '快车', '特惠快车'
        ],
        '餐饮': [
            '外卖', '外卖订单', '咖啡', '奶茶', '零食', '小吃', 
            '餐厅', '饭店', '食堂', '快餐', '餐饮店', '雪糕',
            '成都膳百味餐饮有限公司', '龙户人家', '浏阳蒸菜', '麻辣烫',
            '真霸牛肉', '轩味轩', '乐意豌杂面', '三餐馆子', '调夫五味', 
        ],
        '日用品': [
            '超市', '便利店', '购物', '日用', '生活用品',
            '店内购物', '满彭菜场', '集刻便利店', '盒马鲜生', 
            '天猫超市', '永辉', '龙湖','抖音电商',
        ],
        '服饰': [
            '衣服', '鞋子', '包包', '配饰', '拖鞋'
        ],
        '运动健身': [
            '健身', '游泳', '运动', '球类', '泳镜'
        ],
        '羽毛球': [
            '羽毛球', '羽毛球馆', '四川启成体育',
        ],
        '停车费': [
            '停车缴费', '川GE'
        ],
        '小车加油': [
            '加油', '油费', '油卡'
        ],
    }
    
    @classmethod
    def classify_bill(cls, product_name, counterpart, existing_category=None):
        """
        通用账单分类方法
        
        Args:
            product_name (str): 商品名称或商品描述
            counterpart (str): 交易对方
            existing_category (str): 已有分类（如果存在）
            
        Returns:
            str or None: 分类结果，无法分类时返回None
        """
        # 如果已有分类，直接使用
        if existing_category and existing_category.strip():
            return existing_category.strip()
        
        # 转换为字符串并处理空值
        product_name = str(product_name) if product_name is not None else ''
        counterpart = str(counterpart) if counterpart is not None else ''
        
        # 按交易对方分类
        for company, category in cls.COUNTERPART_MAPPING.items():
            if company in counterpart:
                return category
        
        # 按商品名称关键词分类
        for category, keywords in cls.PRODUCT_KEYWORD_MAPPING.items():
            if any(keyword in product_name for keyword in keywords):
                return category
        
        # 无法分类
        return None
    
    @classmethod
    def classify_alipay_bill(cls, row):
        """
        支付宝账单分类
        
        Args:
            row: 包含支付宝账单数据的行
            
        Returns:
            str or None: 分类结果
        """
        product_name = row.get('商品名称', '')
        counterpart = row.get('对方名称', '')
        existing_category = row.get('分类', '')
        
        if pd.notna(existing_category) and existing_category.strip():
            existing_category = str(existing_category)
        else:
            existing_category = None
            
        return cls.classify_bill(product_name, counterpart, existing_category)
    
    @classmethod
    def classify_wechat_bill(cls, row):
        """
        微信账单分类
        
        Args:
            row: 包含微信账单数据的行
            
        Returns:
            str or None: 分类结果
        """
        product_name = row.get('商品', '')
        counterpart = row.get('交易对方', '')
        existing_category = row.get('分类', '')
        
        if pd.notna(existing_category) and existing_category.strip():
            existing_category = str(existing_category)
        else:
            existing_category = None
            
        return cls.classify_bill(product_name, counterpart, existing_category)