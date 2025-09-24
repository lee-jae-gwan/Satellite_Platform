import numpy as np
from _util.gdal_class import gdal_data
import glob
import os


def calc_NDVI(r_dataset, n_dataset, result_path):
    '''
    
    '''
    #r_data_path = glob.glob(os.path.join(src_path, '*_R*.tif'))
    #n_data_path = glob.glob(os.path.join(src_path, '*_N*.tif'))
    
    #if not r_data_path:
    #    raise FileNotFoundError(f"[ERROR] Red 밴드 파일(_R.tif)을 찾을 수 없습니다. in {src_path}")
    
    #if not n_data_path:
    #    raise FileNotFoundError(f"[ERROR] Red 밴드 파일(__N.tif)을 찾을 수 없습니다. in {src_path}")
    

    #r_dataset = gdal_data.Open(r_data_path[0])
    #n_dataset = gdal_data.Open(n_data_path[0])

    r_band = r_dataset.band.astype('float32')
    n_band = n_dataset.band.astype('float32')

    epsilon = 1e-6 #제로디비전 방지를 위한 매우 작은 수

    ndvi = (n_band - r_band) / (n_band + r_band + epsilon)
    ndvi = np.clip(ndvi, -1, 1) # ndvi 지수를 -1~1 사이의 값으로 지정하기 위한 함수, -1~1사이를 벗어나면 -1과 1로 매핑

    r_mask = r_dataset.band > 0
    ndvi_dataset = r_dataset.copy()
    ndvi_dataset.filename = r_dataset.filename[:r_dataset.filename.index('L2G') + 3] + '_NDVI.tif'
    ndvi_dataset.band = ndvi
    ndvi_dataset.band[~r_mask] = -9999
    #ndvi_dataset.Write(result_path, '')

    return ndvi_dataset








