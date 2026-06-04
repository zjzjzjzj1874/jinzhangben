"""通用工具函数。"""
import socket

from loguru import logger


def get_client_ip() -> str:
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception as e:
        logger.warning(f'获取IP地址失败: {e}')
        return 'Unknown'
