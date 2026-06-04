#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用账单分类器

提供微信和支付宝账单的统一分类功能
"""

import os
import json
import pandas as pd
from loguru import logger

# 本地私有关键词文件（含个人敏感词，已在 .gitignore 中忽略，不会开源泄露）
from bill_tracker.paths import PROJECT_ROOT

LOCAL_KEYWORDS_FILE = os.path.join(
    PROJECT_ROOT, 'classifier_keywords.local.json'
)

# 默认通用映射表：仅保留全国连锁/通用词，不含城市、车牌、个人姓名、常去店铺等隐私信息
DEFAULT_COUNTERPART_MAPPING = {
    # 交通相关
    '滴滴出行': '交通',
    '哈啰出行': '交通',

    # 餐饮相关
    '美团': '餐饮',
    '饿了么': '餐饮',
    '星巴克': '餐饮',
    '肯德基': '餐饮',
    '麦当劳': '餐饮',

    # 日用品相关
    '永辉超市': '日用品',
    '沃尔玛': '日用品',
    '家乐福': '日用品',
    '淘宝平台商户': '日用品',

    # 加油相关
    '壳牌': '小车加油',
}

# 默认通用商品名称关键词映射表
DEFAULT_PRODUCT_KEYWORD_MAPPING = {
    '旅行': ['火车票', '景区门票', '度假酒店'],
    '交通': ['地铁', '公交', '打车', '出租车', '网约车', '共享单车', '快车'],
    '餐饮': [
        '外卖', '外卖订单', '咖啡', '奶茶', '零食', '小吃', '餐厅', '饭店', '食堂',
        '快餐', '餐饮店', '雪糕', '小笼包', '麻辣烫', '蜜雪冰城', '烤肉', '冒菜',
        '串串', '水果', '坚果', '海底捞', '小面', '米饭', '火锅', '火锅底料',
    ],
    '日用品': [
        '超市', '便利店', '购物', '日用', '生活用品', '盒马鲜生', '天猫超市', '美宜佳',
        '抽纸', '舒肤佳', '洗发露', '多多买菜', '百货', '鸡蛋', '保鲜膜', '保鲜袋',
        '洗洁精', '卫生纸', '牙膏', '牙刷', '洗手液', '沐浴露', '洗发水', '护发素',
        '洗衣液', '洗衣粉', '柔顺剂', '洗衣皂', '洗衣球', '洗衣凝珠',
        '收纳盒', '收纳袋', '收纳箱', '收纳架', '收纳篮',
        '晾衣杆', '晾衣架', '晾衣绳', '晾衣夹',
    ],
    '美妆': ['理发', '美发', '雅诗兰黛', '丝塔芙', '珀莱雅'],
    '服饰': ['衣服', '鞋子', '包包', '配饰', '拖鞋', '内裤', '工作服'],
    '运动健身': ['健身', '游泳', '运动', '球类', '泳镜'],
    '羽毛球': ['羽毛球', '羽毛球馆'],
    '生活缴费': ['手机充值', '燃气费', '电费', '电信', '联通'],
    '停车费': ['停车缴费', '停车场', '停车费'],
    '小车加油': ['加油', '油费', '油卡'],
    '医疗保健': ['医保支付', '医保', '医保费用', '医保服务', '药房'],
    '小车保险': ['机动车综合商业保险', '机动车商业保险'],
    '小车维护': [],
}


def _load_local_keywords():
    """读取本地私有关键词文件，返回 (counterpart_mapping, product_keyword_mapping)"""
    if not os.path.exists(LOCAL_KEYWORDS_FILE):
        return {}, {}
    try:
        with open(LOCAL_KEYWORDS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        counterpart = data.get('counterpart_mapping') or {}
        products = data.get('product_keyword_mapping') or {}
        return counterpart, products
    except Exception as e:
        logger.warning(f"加载本地关键词文件失败，仅使用默认关键词: {e}")
        return {}, {}


def _merge_counterpart(default_map, local_map):
    """合并交易对方映射：本地配置可新增或覆盖默认项"""
    merged = dict(default_map)
    merged.update(local_map)
    return merged


def _merge_products(default_map, local_map):
    """合并商品关键词映射：按分类合并并去重"""
    merged = {category: list(keywords) for category, keywords in default_map.items()}
    for category, keywords in local_map.items():
        merged.setdefault(category, [])
        for keyword in keywords:
            if keyword not in merged[category]:
                merged[category].append(keyword)
    return merged


class UniversalBillClassifier:
    """通用账单分类器（默认通用关键词 + 本地私有关键词合并）"""

    _local_counterpart, _local_products = _load_local_keywords()

    # 最终生效的映射表 = 默认通用 + 本地私有（合并去重）
    COUNTERPART_MAPPING = _merge_counterpart(
        DEFAULT_COUNTERPART_MAPPING, _local_counterpart
    )
    PRODUCT_KEYWORD_MAPPING = _merge_products(
        DEFAULT_PRODUCT_KEYWORD_MAPPING, _local_products
    )
    
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