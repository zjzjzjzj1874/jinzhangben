'''
Author: zjzjzjzj1874 zjzjzjzj1874@gmail.com
Date: 2025-01-02 15:14:19
LastEditors: zjzjzjzj1874 zjzjzjzj1874@gmail.com
LastEditTime: 2025-01-19 21:20:40
FilePath: /bill-py-streamlit/bill_types.py
Description: 账单类型
'''
from enum import Enum, auto

class BillCategory:
    class Income(Enum):
        """收入类型"""
        PART_TIME = "兼职收入"
        SUBSIDY = "补贴"
        OTHER_INCOME = "其他收入"

    class Expense(Enum):
        """支出类型"""
        FOOD = "餐饮"
        BADMINTON = "羽毛球"
        TRANSPORTATION = "交通"
        ENTERTAINMENT = "娱乐"
        DAILY_NECESSITIES = "日用品"
        LIVING_EXPENSES = "生活缴费"
        CAR_MAINTENANCE = "小车维护"
        CAR_INSURANCE = "小车保险"
        CAR_GAS = "小车加油"
        PARKING = "停车费"
        CLOTHING = "服饰"
        TRAVEL = "旅行"
        BOOKS = "书籍"
        FITNESS = "运动健身"
        SOCIAL = "人情往来"
        DRESS = "美妆"
        DONATE = "奉献"
        HOME_FURNISHING = "家居"
        PROPERTY_MANAGEMENT = "物业"

    @classmethod
    def get_all_types(cls):
        """获取所有类型"""
        return list(cls.Income) + list(cls.Expense)

    @classmethod
    def get_type_by_name(cls, name):
        """根据名称获取类型"""
        for category in [cls.Income, cls.Expense]:
            for item in category:
                if item.value == name:
                    return item
        return None
