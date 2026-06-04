#!/usr/bin/env python3
"""交互式创建用户（写入 users.json）。"""
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bill_tracker.auth import UserManager


def add_new_user():
    user_manager = UserManager()

    try:
        username = input('请输入用户名: ').strip()
        if not username:
            print('错误：用户名不能为空')
            return

        password = getpass.getpass('请输入密码: ').strip()
        confirm_password = getpass.getpass('请再次输入密码: ').strip()

        if not password:
            print('错误：密码不能为空')
            return

        if password != confirm_password:
            print('错误：两次输入的密码不一致')
            return

        if user_manager.add_user(username, password):
            print(f'✅ 用户 {username} 创建成功！')
        else:
            print(f'❌ 用户 {username} 已存在，创建失败')

    except KeyboardInterrupt:
        print('\n取消操作')
        sys.exit(0)
    except Exception as e:
        print(f'❌ 创建用户失败: {e}')


if __name__ == '__main__':
    print('=== 创建新用户 ===')
    add_new_user()
