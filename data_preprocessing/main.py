import os
import shutil
#from data_preprocessing3 import*
import xml.etree.ElementTree as ET
import glob
#import psycopg2
from datetime import datetime
from config_path import*
from consumer2 import start_consumer
from storage import get_minio_client, minioto_file
from pipeline import process_data, setup_dict, Write_dict

INPUT_DIR = r'D:\project\backup\data\test_db'
WORK_DIR = r'D:\project\backup\data\test_db_work'
OUTPUT_DIR = r'D:\project\backup\data\test_db_output'
GoogleEE_authKey =r'D:\project\backup\data\workspace\data_preprocessing\_util\practice-ljg-276507-a423d69137ea.json'

def process_message(msg):
    uuid = msg['uuid']
    client = get_minio_client()
    img_list, PS_img_list, xml_list = minioto_file(client,uuid)
    print("이미지 가져오기 성공")
    resource_img_dict = setup_dict(img_list,xml_list)
    print("이미지 dict 성공")
    processed_img_dict = process_data(resource_img_dict)
    
    print(f"작업 완료{processed_img_dict['filename']} 상태:{processed_img_dict['stage']}")

    Write_dict(processed_img_dict)
   


def main():
    start_consumer('satellite_topic',process_message)
    

if __name__ == "__main__":
    main()














