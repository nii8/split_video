import logging
import os
from logging.handlers import TimedRotatingFileHandler


def setup_logger(log_dir, log_file):
    """初始化日志（只需调用一次）"""

    # 确保日志目录存在
    os.makedirs(log_dir, exist_ok=True)

    # 创建 Logger
    log = logging.getLogger('shared_logger')  # 固定名称
    log.setLevel(logging.INFO)

    # 避免重复添加 Handler
    if not log.handlers:
        # 文件日志（按天滚动）
        file_handler = TimedRotatingFileHandler(
            f'{log_dir}/{log_file}',
            when='midnight',
            encoding='utf-8'
        )

        # 控制台日志
        console_handler = logging.StreamHandler()

        # 日志格式
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # 添加 Handler
        log.addHandler(file_handler)
        log.addHandler(console_handler)

    return log

