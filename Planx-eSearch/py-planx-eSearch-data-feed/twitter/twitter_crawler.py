import tweepy
import time
from datetime import datetime

# Twitter API 凭证 (需要你自己申请)
API_KEY = "sw2V2snua7qUcJeHWwNCDj8KQ"
API_SECRET = "dML2cCJfm6FNjv8BGveE9onFqRtncpiCEkzhbE8tSX0RqQ8bVT"
ACCESS_TOKEN = "1804113121377947654-kFuKI2qsRxrl8QvXcDbWEm2q6SgMRx"
ACCESS_TOKEN_SECRET = "INQu11P93H8KpMHmYWlpsg1CuW0ZYBsu5PhCB8VqMaFdQ"
BEARER_TOKEN = "AAAAAAAAAAAAAAAAAAAAAOFczwEAAAAAYPnadWO98Xe17NDsvNt3e5PwpNU%3DVkYixsAGXiBiWz6k10znC2yWPWMgPlLON2FjHplPg7P6ZpecOZ"

# 初始化认证
auth = tweepy.OAuthHandler(API_KEY, API_SECRET)
auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)

# 创建 API 对象
api = tweepy.API(auth, wait_on_rate_limit=True)  # wait_on_rate_limit 处理速率限制

# 使用 Client 来访问 v2 API（推荐）
client = tweepy.Client(
    bearer_token=BEARER_TOKEN,
    consumer_key=API_KEY,
    consumer_secret=API_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_TOKEN_SECRET,
    wait_on_rate_limit=True
)

def crawl_user_tweets(username, max_tweets=100):
    """爬取指定用户的帖子"""
    try:
        id = client.get_user(username=username).data.id
        print(f"用户ID: {id}")
        # 获取用户 timeline
        tweets = client.get_users_tweets(
            id=id,
            max_results=max_tweets,
            tweet_fields=['created_at', 'lang', 'public_metrics']
        )
        
        # 保存结果
        for tweet in tweets.data:
            print(f"时间: {tweet.created_at}")
            print(f"作者ID: {tweet.author_id}")
            print(f"内容: {tweet.text}")
            print(f"点赞数: {tweet.public_metrics['like_count']}")
            print(f"转发数: {tweet.public_metrics['retweet_count']}")
            print("-" * 50)
    except Exception as e:
        print(f"错误: {e}")
    return tweets

def crawl_keyword_tweets(keyword, max_tweets=100):
    """爬取包含特定关键词的帖子"""
    try:
        # 搜索最近的帖子
        tweets = client.search_recent_tweets(
            query=keyword,
            max_results=max_tweets,
            tweet_fields=['created_at', 'author_id', 'public_metrics']
        )
        
        # 保存结果
        for tweet in tweets.data:
            print(f"时间: {tweet.created_at}")
            print(f"作者ID: {tweet.author_id}")
            print(f"内容: {tweet.text}")
            print(f"点赞数: {tweet.public_metrics['like_count']}")
            print(f"转发数: {tweet.public_metrics['retweet_count']}")
            print("-" * 50)
            
    except Exception as e:
        print(f"错误: {e}")

def save_to_file(tweets, filename="tweets.txt"):
    """将结果保存到文件"""
    with open(filename, 'a', encoding='utf-8') as f:
        for tweet in tweets.data:
            f.write(f"时间: {tweet.created_at}\n")
            f.write(f"内容: {tweet.text}\n")
            f.write("-" * 50 + "\n")

if __name__ == "__main__":
    # 示例1：爬取某个用户的帖子
    print("正在爬取用户帖子...")      
    crawl_user_tweets("elonmusk", max_tweets=5)

    # 等待以避免速率限制
    time.sleep(5)