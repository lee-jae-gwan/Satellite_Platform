import os
import shutil
#from data_preprocessing3 import*
import xml.etree.ElementTree as ET
import glob
#import psycopg2
from datetime import datetime
from _util.pansharpening import run_pansharpening
from _util.atmospheric_correction2 import run_atmos_correction
from _util.NDVI import run_NDVI
from _util.NDWI import run_NDWI
from _util.GLCM import run_GLCM_gpu
from _util.gdal_class import*
from _util.wavelet_denoise import run_denoise_parallel
from config_path import*

INPUT_DIR = r'D:\project\backup\data\test_db'
WORK_DIR = r'D:\project\backup\data\test_db_work'
OUTPUT_DIR = r'D:\project\backup\data\test_db_output'
GoogleEE_authKey =r'D:\project\backup\data\workspace\data_preprocessing\_util\practice-ljg-276507-a423d69137ea.json'

def ensure_dirs():
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(WORK_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def setup_dict(imgdata_list,xml_list):
    ensure_dirs()

    process_img_dict = {}
    bands = {}
    filename = "_".join(os.path.splitext(imgdata_list[0].filename)[0].split("_")[:-1])
    process_img_dict["filename"] = filename
    
    for tmp_file in imgdata_list:
        band_name = tmp_file.filename.split("_")[-1].replace(".tif","")
        bands[band_name] = tmp_file

    process_img_dict['band'] = bands
    process_img_dict['resolution'] = process_img_dict['band']['B'].geoinfo[1]
    process_img_dict['stage'] = 'setup'
    process_img_dict['xml'] = xml_list[0]
    process_img_dict['EE_authKey'] = GoogleEE_authKey
    
    return process_img_dict


# def setup_dict(folder_path):
    
#     ensure_dirs() 
#     process_img_dict = {}
#     bands = {}
#     file_name = os.path.basename(folder_path)
#     process_img_dict["filename"] = file_name

#     tif_list = glob.glob(os.path.join(folder_path,'*.tif'))
#     img_list = [f for f in tif_list if not f.endswith("_PS.tif")]
    
#     xml_path=os.path.join(folder_path, f"{os.path.basename(folder_path)}_Aux.xml")
    
#     for tmp_file in img_list:
#         band_name = tmp_file.split("_")[-1].replace(".tif","")

#         bands[band_name] = gdal_data.Open(os.path.join(folder_path,tmp_file))        

#     process_img_dict['band'] = bands
#     process_img_dict['resolution'] = process_img_dict['band']['B'].geoinfo[1]
#     process_img_dict['stage'] = 'setup'
#     process_img_dict['xml_path'] = xml_path
#     process_img_dict['EE_authKey'] = GoogleEE_authKey
    
#     return process_img_dict


def Write_dict(input_dict, result_path=WORK_DIR):
    stage = input_dict['stage']
    result_path = os.path.join(result_path, input_dict['filename'])
    
    os.makedirs(result_path, exist_ok=True)

    for i in input_dict['band'].keys():
        tmp_dataset = input_dict['band'][i]
        tmp_dataset.Write(result_path, stage)

def process_data(process_img_dict):
    #잡음제거
    process_img_dict = run_denoise_parallel(process_img_dict)

    #해상도 변환
    # if (process_img_dict['resolution'] != 0.5) and (process_img_dict['stage']=='denoised'):
    #      process_img_dict= run_pansharpening(process_img_dict)

    # else:
    #     process_img_dict['stage'] = 'pansharpened'

    #대기보정
    process_img_dict= run_atmos_correction(process_img_dict)

    #분광지수 계산
    process_img_dict = run_NDVI(process_img_dict)
    process_img_dict = run_NDWI(process_img_dict)
    process_img_dict = run_GLCM_gpu(process_img_dict)

    process_img_dict['stage'] = 'processed'

    return process_img_dict