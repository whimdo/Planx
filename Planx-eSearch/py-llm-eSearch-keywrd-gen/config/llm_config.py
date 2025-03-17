class llm_Config:
    def __init__(
        self,
        keyWordCount=20,
        sys_prompt=None,
        openai_base_url="http://deep.tapdeep.ai:31141/v1",
        openai_api_key="olama",
        openai_model="llama3.1:latest",
        openai_temp=0.5,
        openai_max_tokens=14000,
        openai_use_stream=False
    ):
        # 关键词数量，默认为 10
        self.keyWordCount = keyWordCount if keyWordCount is not None else 10

        # 系统提示，如果未提供则使用默认值
        self.sys_prompt = sys_prompt if sys_prompt is not None else (
            f"""You are an advanced language model tasked with extracting keywords from a given text. """
            f"""Given the input text provided by the user, identify and extract the top N = {self.keyWordCount} keywords """
            f"""based on their importance and relevance to the text. Importance should be determined by context, """
            f"""and semantic significance. Attantion!Sort the keywords in descending order of priority and return them in a Python """
            f"""list format, e.g., ['key1', 'key2', 'key3', ...]. Your response should be a single valid Python list """
            f"""containing exactly {self.keyWordCount} keywords as strings, with no additional explanation or text outside the list.And Must be in English!!."""
            f"""If the input is vague or lacks sufficient context, infer reasonable keywords based on common sense."""
        )

        # OpenAI 配置参数
        self.openai_base_url = openai_base_url
        self.openai_api_key = openai_api_key
        self.openai_model = openai_model
        self.openai_temp = openai_temp
        self.openai_max_tokens = openai_max_tokens
        self.openai_use_stream = openai_use_stream

    def __str__(self):
        """返回配置的字符串表示，便于调试"""
        return (
            f"Config(keyWordCount={self.keyWordCount}, "
            f"openai_model={self.openai_model}, "
            f"openai_base_url={self.openai_base_url}, "
            f"openai_temp={self.openai_temp}, "
            f"openai_max_tokens={self.openai_max_tokens}, "
            f"openai_use_stream={self.openai_use_stream})"
        )
# logging_config.py
import logging
import os

def setup_logging(log_file="keyword_extraction.log", log_level=logging.INFO):
    """
    配置日志，输出到文件和控制台
    - log_file: 日志文件路径
    - log_level: 日志级别（默认 INFO）
    """
    # 确保日志目录存在
    log_dir = os.path.dirname(os.path.abspath(log_file))
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 创建日志器
    logger = logging.getLogger(__name__)
    logger.setLevel(log_level)

    # 清除现有处理器（避免重复添加）
    if logger.hasHandlers():
        logger.handlers.clear()

    # 日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 文件处理器
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    # 添加处理器到日志器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# 默认配置（可选，主文件中直接调用时使用）
logger = setup_logging()

