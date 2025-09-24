from kafka import KafkaConsumer
import json
import urllib
from minio import Minio
from minio.error import S3Error
import os



def main():
    consumer = KafkaConsumer(
        'satellite_topic',
        bootstrap_servers = "127.0.0.1:9092",
        auto_offset_reset = "latest",
        value_deserializer = lambda x: json.loads(x.decode('utf-8')),
        group_id = "satellite_group"
    )

    for message in consumer:
        uuid = message.value['uuid']
        file_paths = list(map(lambda f: f['S3']['object']['key'], message.value['files']))
        # key = message.value['Records'][0]['s3']['object']['key']
        # decode_key = urllib.parse.unquote(key)
        # folder_uuid = decode_key.split('/')[0]
        # folder_name = decode_key.split('/')[1]
        # s3_path = f"s3a://satellite-images/{folder_uuid}/{folder_name}/"
        # print(f"consumser1: {s3_path}")




if __name__=="__main__":
    main()
