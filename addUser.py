from user_manager import UserManager
import getpass
import sys

def add_new_user():
    # 创建用户管理器实例
    user_manager = UserManager()
    
    try:
        # 获取用户输入
        username = input("请输入用户名: ").strip()
        if not username:
            print("错误：用户名不能为空")
            return
        
        # 使用 getpass 安全地获取密码（输入时不显示）
        password = getpass.getpass("请输入密码: ").strip()
        confirm_password = getpass.getpass("请再次输入密码: ").strip()
        
        # 验证密码
        if not password:
            print("错误：密码不能为空")
            return
        
        if password != confirm_password:
            print("错误：两次输入的密码不一致")
            return
        
        # 添加用户
        if user_manager.add_user(username, password):
            print(f"✅ 用户 {username} 创建成功！")
        else:
            print(f"❌ 用户 {username} 已存在，创建失败")
            
    except KeyboardInterrupt:
        print("\n取消操作")
        sys.exit(0)
    except Exception as e:
        print(f"❌ 创建用户失败: {str(e)}")

if __name__ == "__main__":
    print("=== 创建新用户 ===")
    add_new_user() 