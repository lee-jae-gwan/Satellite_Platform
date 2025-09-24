from kafka import KafkaConsumer
import json
import urllib
from minio import Minio
from minio.error import S3Error
import os


def start_consumer(topic, callback):
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers="127.0.0.1:9092",
        auto_offset_reset="latest",
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
    )
    for message in consumer:
        print("메세지 수신 성공")
        print(message)
        callback(message.value)

