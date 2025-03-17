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
        # 关键词数量，默认为 20
        self.keyWordCount = keyWordCount if keyWordCount is not None else 20

        # 系统提示，如果未提供则使用默认值
        self.sys_prompt = sys_prompt if sys_prompt is not None else (
            f"""You are an advanced language model designed to analyze user input and extract relevant keywords. """
            f"""The user will provide either a description of a Telegram group they want to query (e.g., 'a group about cryptocurrency trading') """
            f"""or a random piece of text. Your task is to identify and extract the top N = {self.keyWordCount} keywords """
            f"""that best represent the main topics, themes, or interests in the input text, based on their contextual importance and semantic significance. """
            f"""Sort the keywords in descending order of priority and return them in a Python list format, e.g., ['key1', 'key2', 'key3', ...]. """
            f"""Your response must be a single valid Python list containing exactly {self.keyWordCount} keywords as strings, """
            f"""with no additional explanation or text outside the list. All keywords must be in English, and avoid duplicates. """
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
        
# {
#   "text": "I want to join a group about cryptocurrency trading.",
#   "keyword_count": 20,
#   "model": "llama3.1:latest",
#   "use_stream": false,
#   "sys_prompt": "You are an advanced language model designed to analyze user input and extract relevant keywords. The user will provide either a description of a Telegram group they want to query (e.g., 'a group about cryptocurrency trading') or a random piece of text. Your task is to identify and extract the top N = 20 keywords that best represent the main topics, themes, or interests in the input text, based on their contextual importance and semantic significance. Sort the keywords in descending order of priority and return them in a Python list format, e.g., ['key1', 'key2', 'key3', ...]. Your response must be a single valid Python list containing exactly 20 keywords as strings, with no additional explanation or text outside the list. All keywords must be in English, and avoid duplicates. If the input is vague or lacks sufficient context, infer reasonable keywords based on common sense.",
#   "temp": 0.5,
#   "max_tokens": 14000
# }