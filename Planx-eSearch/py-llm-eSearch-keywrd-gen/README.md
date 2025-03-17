py-llm-eSearch-keywrd-gen

nohup python main_with_kafka.py > log/app.log 2>&1 &

ps -ef | grep main_with_kafka

lsof -i :9001