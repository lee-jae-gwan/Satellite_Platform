from kafka import KafkaConsumer
import json
import time

def process_image(file_path):
    print(f'Processing {file_path}...')
    time.sleep(5)
    print(f'Done{file_path}....')

consumer = KafkaConsumer(
    'satellite_topic',
    bootstrap_servers = 'localhost:9092',
    auto_offset_reset='earliest',
    enable_auto_commit = True,
    group_id = 'satellite-group',
    value_deserializer= lambda m : json.laods(m.decode('utf-8'))
)

print("wating for message....")


for message in consumer:
    file_path = message.value['file_path']
    process_image(file_path)

