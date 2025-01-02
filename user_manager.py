import bcrypt
from loguru import logger
import os
import json

class UserManager:
    def __init__(self, users_file='users.json'):
        """
        初始化用户管理器
        
        :param users_file: 存储用户信息的文件
        """
        self.users_file = users_file
        self.users = self.load_users()
    
    def load_users(self):
        """
        加载用户信息
        
        :return: 用户字典
        """
        try:
            if not os.path.exists(self.users_file):
                # 如果文件不存在，创建默认管理员账号
                default_users = {
                    'admin': self.hash_password('admin123')
                }
                with open(self.users_file, 'w') as f:
                    json.dump(default_users, f)
                return default_users
            
            with open(self.users_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载用户信息失败: {e}")
            return {}
    
    def hash_password(self, password):
        """
        密码哈希
        
        :param password: 明文密码
        :return: 哈希后的密码
        """
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, stored_password, provided_password):
        """
        验证密码
        
        :param stored_password: 存储的哈希密码
        :param provided_password: 提供的明文密码
        :return: 是否匹配
        """
        return bcrypt.checkpw(
            provided_password.encode('utf-8'), 
            stored_password.encode('utf-8')
        )
    
    def authenticate(self, username, password):
        """
        用户认证
        
        :param username: 用户名
        :param password: 密码
        :return: 是否认证成功
        """
        try:
            if username not in self.users:
                return False
            
            return self.verify_password(self.users[username], password)
        except Exception as e:
            logger.error(f"认证失败: {e}")
            return False
    
    def add_user(self, username, password):
        """
        添加新用户
        
        :param username: 用户名
        :param password: 密码
        :return: 是否添加成功
        """
        try:
            if username in self.users:
                return False
            
            self.users[username] = self.hash_password(password)
            
            with open(self.users_file, 'w') as f:
                json.dump(self.users, f)
            
            return True
        except Exception as e:
            logger.error(f"添加用户失败: {e}")
            return False
