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
        '零食有鸣': '日用品',
        
        # 停车费相关
        '深圳市微泊云科技有限公司': '停车费',
        '华敏物业': '停车费',
        '守权': '停车费',
        
        # 运动健身相关
        '羽毛球': '羽毛球',
        '闪动体育科技': '羽毛球',
        'Coriander. 京新海球馆 店长': '羽毛球教学场地',
        '华川馆长': '羽毛球教学场地',
        '华川': '羽毛球教学场地',
        
        # 其他
        '快剪': '美妆',
        '壳牌': '小车加油',
        '人居智慧': '物业',
        '妇幼保健院': '医疗保健',
    }
    
    # 通用商品名称关键词映射表
    PRODUCT_KEYWORD_MAPPING = {
        '旅行':['火车票' , '景区门票', '度假酒店', '富士'],
        '交通': [
            '地铁', '公交', '打车', '出租车', '网约车', '共享单车',
            '哈啰单车', '哈啰', '天府通', '快车', '特惠快车'
        ],
        '餐饮': [
            '外卖', '外卖订单', '咖啡', '奶茶', '零食', '小吃',  '食在宣', '老面馒头',
            '餐厅', '饭店', '食堂', '浏阳', '快餐', '餐饮店', '雪糕', '小笼包', '面面俱到', 
            '成都膳百味餐饮有限公司', '龙户人家', '浏阳蒸菜', '麻辣烫', '蜜雪冰城', '山城面馆',
            '真霸牛肉', '轩味轩', '乐意豌杂面', '三餐馆子', '调夫五味', '喜利来', '莱吃面',
            '烤肉', '绵阳米线', '七号卤肉', '五馅包', '水果', '手抓饼', '手工糖', '坚果', '零食',
            '川菜馆', '阿坝州特产', '牦牛肉', '羊肉米线', '冒菜', '串串', '蓝莓', '煎饼道', '海底捞', 
            '小面', '米饭', '火锅底料',
        ],
        '日用品': [
            '超市', '便利店', '购物', '日用', '生活用品', '小红书', '蓝月亮衣物', '蓝月亮洗衣液',
            '店内购物', '满彭菜场', '集刻便利店', '盒马鲜生', '抖音月付', '商品支付', '美团收银',
            '天猫超市', '永辉', '龙湖','抖音电商', '美宜佳', '沃尔玛', '抽纸', '舒肤佳', '洗头膏',
            '洗发露', '天猫优选', '多多买菜','小林百货','中意百货','开心邻里', '百货', '露营推车', '多多买菜',
            '朕给栗','鸡蛋', '保鲜膜','保鲜袋', '洗洁精', '卫生纸', '牙膏', '牙刷', '洗手液', '沐浴露', '洗发水', '护发素',
            '防撞贴', '洗衣液', '洗衣粉', '柔顺剂', '洗衣皂', '洗衣球', '洗衣片', '洗衣凝珠', '洗衣胶囊','收纳摆件',
            '收纳盒', '收纳袋', '收纳箱', '收纳柜', '收纳架', '收纳篮', '收纳筐', '收纳箱子', '收纳包', 
            '晾衣杆', '晾衣架', '晾衣绳', '晾衣夹',
        ],
        '美妆': [
            '快剪', '理发', '美发', '雅诗兰黛', '丝塔芙', '珀莱雅', '黛珂心悦', '福瑞达颐莲'
        ],
        '服饰': [
            '衣服', '鞋子', '包包', '配饰', '拖鞋', '内裤', '平角裤', '工作服',
        ],
        '运动健身': [
            '健身', '游泳', '运动', '球类', '泳镜'
        ],
        '羽毛球': [
            '羽毛球', '羽毛球馆', '四川启成体育','超越极限体育',
        ],
        '生活缴费': [
            '手机充值', '燃气费', '电费', '电信', '联通',
        ],
        '停车费': [
            '停车缴费', '川GE', '川-GE', '四川宏盛国际物流', '停车场', '停车费', 
        ],
        '小车加油': [
            '加油', '油费', '油卡',
        ],
        '医疗保健': [
            '医保支付', '医保', '医保费用', '医保服务', '药房',
        ],
        '小车保险': [
            '机动车综合商业保险', '机动车商业保险', '机动车商业保险',
        ],
        '小车维护': [
            '建国汽车', 
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