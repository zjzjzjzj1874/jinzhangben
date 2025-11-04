#!/usr/bin/env python3
"""
周期性数据备份脚本

这个脚本可以作为定时任务运行，自动执行智能备份：
- 只有数据发生变化时才会创建新备份
- 自动清理旧备份，保留最新5份
- 记录备份日志

使用方法：
1. 直接运行: python scheduled_backup.py
2. 作为cron任务: 0 2 * * * /usr/bin/python3 /path/to/scheduled_backup.py
3. Docker环境: docker exec bill-py-streamlit-web-1 python /app/scheduled_backup.py
"""

import os
import sys
import logging
from datetime import datetime
from database import BillDatabase

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/scheduled_backup.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def run_scheduled_backup():
    """
    执行周期性备份任务
    """
    logger.info("开始执行周期性备份任务")
    
    try:
        # 连接数据库
        db = BillDatabase()
        logger.info("数据库连接成功")
        
        # 执行智能备份
        backup_result = db.backup_all_data(force=False)
        
        if backup_result.get('success', False):
            if backup_result.get('skipped', False):
                logger.info("数据未发生变化，跳过备份")
                logger.info(f"当前数据哈希: {backup_result.get('current_hash', 'N/A')}")
            else:
                logger.info("备份完成")
                logger.info(f"备份文件: {backup_result.get('backup_path', 'N/A')}")
                logger.info(f"备份记录数: {backup_result.get('total_documents', 0):,}")
                logger.info(f"文件大小: {backup_result.get('file_size_mb', 0):.2f} MB")
                logger.info(f"数据哈希: {backup_result.get('data_hash', 'N/A')}")
        else:
            logger.error(f"备份失败: {backup_result.get('message', '未知错误')}")
            return False
            
        # 关闭数据库连接
        db.close()
        logger.info("周期性备份任务完成")
        return True
        
    except Exception as e:
        logger.error(f"周期性备份任务失败: {e}")
        return False

def check_environment():
    """
    检查运行环境
    """
    logger.info("检查运行环境...")
    
    # 检查数据目录
    data_dir = '/app/data'
    if not os.path.exists(data_dir):
        logger.warning(f"数据目录不存在，尝试创建: {data_dir}")
        try:
            os.makedirs(data_dir, exist_ok=True)
            logger.info(f"数据目录创建成功: {data_dir}")
        except Exception as e:
            logger.error(f"无法创建数据目录: {e}")
            return False
    
    # 检查日志目录
    log_dir = '/app/logs'
    if not os.path.exists(log_dir):
        logger.warning(f"日志目录不存在，尝试创建: {log_dir}")
        try:
            os.makedirs(log_dir, exist_ok=True)
            logger.info(f"日志目录创建成功: {log_dir}")
        except Exception as e:
            logger.error(f"无法创建日志目录: {e}")
            return False
    
    logger.info("环境检查完成")
    return True

def main():
    """
    主函数
    """
    print(f"周期性备份脚本启动 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 检查环境
    if not check_environment():
        logger.error("环境检查失败，退出")
        sys.exit(1)
    
    # 执行备份
    success = run_scheduled_backup()
    
    if success:
        logger.info("周期性备份脚本执行成功")
        sys.exit(0)
    else:
        logger.error("周期性备份脚本执行失败")
        sys.exit(1)

if __name__ == '__main__':
    main()