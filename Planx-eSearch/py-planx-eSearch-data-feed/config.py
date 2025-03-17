# py-planx-eSearch-data-feed/config.py

# Telegram API 配置
# TELEGRAM_API_ID = '28991940'
# TELEGRAM_API_HASH = 'f9e4c708e68ee236297ea9dc6c5322a4'
TELEGRAM_API_ID = '2040'
TELEGRAM_API_HASH = 'b18441a1ff607e10a989891a5462e627'
TELEGRAM_PHONE = '+8619102844501'

# Clash 代理配置（SOCKS5）
PROXY_TYPE = 'socks5'
PROXY_HOST = '192.168.1.222'
PROXY_PORT = 7890

# MongoDB 配置
MONGO_HOST = '192.168.1.204'
MONGO_PORT = 27017
MONGO_DB = 'planx1'
MONGO_COLLECTION = 'telegroups'

# 日志配置
LOG_DIR = 'log'
LOG_FILE = 'crawler.log'
LOG_LEVEL = 'DEBUG'
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOG_FILEMODE = 'a'  # 追加模式