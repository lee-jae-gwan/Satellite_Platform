# 기초 경로(149 서버 버전)
INPUT_DIR = "/data/workspace/data_preprocessing/data/input"
WORK_DIR  = "/data/workspace/data_preprocessing/data/work"
OUTPUT_DIR = "/data/workspace/data_preprocessing/output"
TASK_TYPES = ["rd", "bd", "land", "fire", "water"]

# container_name: 공유 마운트된 input 경로
HOST_SHARED_PATHS = {
    'bd':'/data/mountFolder/bd/',
    'rd':'/data/mountFolder/rd/',
    'water':'/data/mountFolder/water/',
    'fire':'/data/mountFolder/fire/',
    'land':'/data/mountFolder/land/'
}

MERGE_BAND_ORDERS ={
    "rd" : ['B4', 'B3', 'B2'], 
    "bd"   : ['B4', 'B3', 'B2'],
    "fire" : ['B4', 'B3', 'B2'],
    "land" : ["B2", "B3", "B4", "B8","NDWI", "NDVI", "NDWI_GLCM", "NDVI_GLCM"], 
    "water": ["B3", "B8", "NDWI"]
}

DB_CONFIG = {
    "host" : "192.168.0.148",
    "port" : "5432",
    "dbname" : "ngii_cs",
    "user" : "ngii_cs",
    "password" : "ngii_cs"
}

DOCKER_CONTAINERS = [
    {"name": "fire_v2.0", "script": "python /home/workspace/fire_new/inferenc_run.py", "input_dir": "/home/deploy/data/fire"},
    {"name": "bd_v2.0", "script": "python /home/workspace/bd/mmsegmentation/cas_process/main.py", "input_dir": "/home/deploy/data/bd"},
    {"name": "rd", "script": "python /home/workspace/rd/mmsegmentation/cas_process/main.py", "input_dir": "/home/deploy/data/rd"},
    {"name": "land", "script": "python /home/workspace/land/job02/run.py", "input_dir": "/home/deploy/data/land"},
    {"name": "water_v1.0", "script": "python /home/workspace/water/test_copy.py", "input_dir": "/home/deploy/data/water"}
]

Preprocessed_path = {
    'bd':'/data/mountFolder/bd/',
    'rd':'/data/mountFolder/rd/',
    'water':'/data/mountFolder/water/',
    'fire':'/data/mountFolder/fire/',
    'land':'/data/mountFolder/land/'
}