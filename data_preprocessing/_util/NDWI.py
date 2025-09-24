import numpy as np
from _util.gdal_class import gdal_data
import glob
import os



def run_NDWI(input_dict):
    
    # g_data_path = glob.glob(os.path.join(src_path, '*_G*.tif'))
    # n_data_path = glob.glob(os.path.join(src_path, '*_N*.tif'))

    
    # if not g_data_path:
    #     raise FileNotFoundError(f"[ERROR] 밴드 파일을 찾을 수 없습니다. in {src_path}")
    
    # if not n_data_path:
    #     raise FileNotFoundError(f"[ERROR] 밴드 파일을 찾을 수 없습니다. in {src_path}")

    # g_dataset = gdal_data.Open(g_data_path[0])
    # n_dataset = gdal_data.Open(n_data_path[0])

    g_band = input_dict['band']['G'].band.astype('float32')
    n_band = input_dict['band']['N'].band.astype('float32')
    tmp_filename = input_dict['filename']
    ext = '.tif'

    epsilon = 1e-6 #제로디비전 방지를 위한 매우 작은 수
    ndwi = (g_band - n_band) / (n_band + g_band + epsilon)
    ndwi = np.clip(ndwi, -1, 1)# ndwi 지수를 -1~1 사이의 값으로 지정하기 위한 함수, -1~1사이를 벗어나면 -1과 1로 매핑

    g_mask = input_dict['band']['G'].band > 0
    ndwi_dataset = input_dict['band']['G'].copy()
    
    ndwi_dataset.filename = tmp_filename + "_NDWI" + ext

    ndwi_dataset.band = ndwi
    ndwi_dataset.dtype = ndwi_dataset.band.dtype
    ndwi_dataset.band[~g_mask] = -9999

    input_dict['band']['NDWI'] = ndwi_dataset
    input_dict['stage'] = 'Spectral_IDX(NDWI)'

    #ndwi_dataset.Write(result_path, '')

    return input_dict
