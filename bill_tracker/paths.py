"""项目根目录与 data/logs 路径（Docker 可通过环境变量覆盖）。"""
import os

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(PACKAGE_DIR)


def get_data_root() -> str:
    return os.getenv('DATA_DIR', os.path.join(PROJECT_ROOT, 'data'))


def get_log_dir() -> str:
    return os.getenv('LOG_DIR', os.path.join(PROJECT_ROOT, 'logs'))


def get_snapshots_dir() -> str:
    return os.path.join(get_data_root(), 'snapshots')


def get_pre_restore_dir() -> str:
    return os.path.join(get_data_root(), 'pre_restore')


def get_yearly_dir() -> str:
    return os.path.join(get_data_root(), 'yearly')


def get_manifest_path() -> str:
    return os.path.join(get_data_root(), 'manifest.json')


def csv_dir(provider: str) -> str:
    """导入账单默认目录：csv/alipay、csv/wechat。"""
    return os.path.join(PROJECT_ROOT, 'csv', provider)
