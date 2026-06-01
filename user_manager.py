import bcrypt
from loguru import logger
import os
import json

# 认证结果状态
AUTH_SUCCESS = 'success'          # 数据库已有密码且校验通过
AUTH_NEED_CHANGE = 'need_change'  # 数据库无密码，文件初始密码校验通过，需修改密码
AUTH_FAIL = 'fail'                # 认证失败

class UserManager:
    def __init__(self, db=None, users_file='users.json'):
        """
        初始化用户管理器

        :param db: 数据库实例（BillDatabase），用于优先存储/读取登录密码；为 None 时退回文件
        :param users_file: 存储系统初始化用户信息的文件
        """
        self.db = db
        self.users_file = users_file
        self.users = self.load_users()
    
    def load_users(self):
        """
        加载文件中的初始用户信息

        :return: 用户字典
        """
        try:
            if not os.path.exists(self.users_file):
                # 如果文件不存在，创建默认管理员账号（系统初始化密码）
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
        try:
            return bcrypt.checkpw(
                provided_password.encode('utf-8'),
                stored_password.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"密码校验异常: {e}")
            return False

    def _get_db_password(self, username):
        """从数据库读取用户密码哈希，无数据库或不存在时返回 None"""
        if self.db is None:
            return None
        try:
            return self.db.get_user_password(username)
        except Exception as e:
            logger.error(f"读取数据库用户密码失败: {e}")
            return None
    
    def authenticate(self, username, password):
        """
        用户认证（数据库优先）

        流程：
        1. 优先从数据库读取该用户的密码，存在则与输入比对，匹配返回 success，否则 fail
        2. 数据库没有该用户密码时，读取文件中的初始密码进行校验，
           校验通过返回 need_change（要求用户修改密码并持久化到数据库）

        :param username: 用户名
        :param password: 密码
        :return: AUTH_SUCCESS / AUTH_NEED_CHANGE / AUTH_FAIL
        """
        try:
            if not username:
                return AUTH_FAIL

            # 1. 数据库优先
            db_hash = self._get_db_password(username)
            if db_hash:
                return AUTH_SUCCESS if self.verify_password(db_hash, password) else AUTH_FAIL

            # 2. 数据库无密码，回退到文件中的初始密码
            file_hash = self.users.get(username)
            if file_hash and self.verify_password(file_hash, password):
                return AUTH_NEED_CHANGE

            return AUTH_FAIL
        except Exception as e:
            logger.error(f"认证失败: {e}")
            return AUTH_FAIL

    def set_password(self, username, new_password):
        """
        设置/持久化新密码（优先写入数据库，无数据库时退回文件）

        :param username: 用户名
        :param new_password: 新的明文密码
        :return: 是否成功
        """
        try:
            if not username or not new_password:
                return False

            password_hash = self.hash_password(new_password)

            if self.db is not None:
                return self.db.set_user_password(username, password_hash)

            # 无数据库时退回文件存储
            self.users[username] = password_hash
            with open(self.users_file, 'w') as f:
                json.dump(self.users, f)
            return True
        except Exception as e:
            logger.error(f"设置密码失败: {e}")
            return False
    
    def add_user(self, username, password):
        """
        添加新用户（写入文件，作为初始化用途）
        
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
