import os
from _util.gdal_class import gdal_data
import copy
from osgeo import gdal
import numpy as np
import glob
from sklearn.linear_model import LinearRegression

def array_to_dataset(array, geoinfo, crs_wkt):
    height, width = array.shape
    driver = gdal.GetDriverByName("MEM")
    ds = driver.Create("", width, height, 1, gdal.GDT_UInt16)
    ds.SetGeoTransform(geoinfo)
    ds.SetProjection(crs_wkt)
    ds.GetRasterBand(1).WriteArray(array)
    return ds


def run_resample(ms_data, p_data):
    # 목표 GSD
    p_geoinfo = (p_data.geoinfo[1], p_data.geoinfo[5])

    # 출력 영역 계산
    outbounds = p_data.geoinfo
    x_min = outbounds[0]
    y_max = outbounds[3]
    x_max = x_min + p_data.xsize * outbounds[1]
    y_min = y_max + p_data.ysize * outbounds[5]
    outbounds = (x_min, y_min, x_max, y_max)

    # gdal_data → 메모리 Dataset 변환
    src_ds = array_to_dataset(ms_data.band, ms_data.geoinfo, ms_data.proj)

    # GDAL Warp로 리샘플링
    resampled_ds = gdal.Warp(
        "",
        src_ds,
        format="MEM",
        xRes=p_geoinfo[0],
        yRes=p_geoinfo[1],
        outputBounds=outbounds,
        resampleAlg="cubic",
    )

    # 다시 gdal_data로 변환
    tmp_gdal_data = gdal_data.from_dataset(resampled_ds)
    tmp_gdal_data.filename = ms_data.filename

    return tmp_gdal_data

def estimate_coefficients(ms_low, pan_low):

    H, W, C = ms_low.shape
    X = ms_low.reshape(-1, C)  # (H*W, 4)
    y = pan_low.reshape(-1, 1)  # (H*W, 1)
    reg = LinearRegression().fit(X, y)
    return reg.coef_[0].astype('float32'), reg.intercept_.astype('float32')


def make_GIHSA_pansharpen_img(datasets, resampled_datas):
    ms_list = ["B","G","R","N"]
    
    hir_pan = datasets['P']
    hir_pan_mask = hir_pan.band > 0

    low_pan = run_resample(datasets['P'], datasets['B'])
    low_pan = low_pan.band

    ms_bands = np.dstack([datasets["B"].band, datasets["G"].band, datasets["R"].band, datasets["N"].band])

    H = min(ms_bands.shape[0], low_pan.shape[0])
    W = min(ms_bands.shape[1], low_pan.shape[1])

    ms_bands = ms_bands[:H, :W, :]
    low_pan = low_pan[:H, :W]

    w, b = estimate_coefficients(ms_bands, low_pan)
    
    nrow, ncol = resampled_datas["B"].band.shape
    hir_pan.band = hir_pan.band[:nrow, :ncol]
    hir_pan_mask = hir_pan_mask[:nrow, :ncol]

    intensity = 0
    for idx, i in enumerate(ms_list):
        tmp_band = np.where(hir_pan_mask > 0, resampled_datas[i].band, 0)
        intensity += w[idx] * tmp_band

    intensity = intensity +b
    delta = np.where(hir_pan_mask, hir_pan.band - intensity, 0)

    for band in ms_list:
        resampled_datas[band].band = (resampled_datas[band].band + delta).astype('uint16')

    return resampled_datas

def run_pansharpening(input_dict):
    result = copy.deepcopy(input_dict)
    band_list = ["B","G","R","N","P"]
    
    print("----------------------start resampleing-------------------------------------")
    for i in band_list:
        if i != "P":
            result['band'][i] = run_resample(result['band'][i], result['band']['P'])

    print("----------------------start GIHSA-------------------------------------")
    GIHSA_dict = make_GIHSA_pansharpen_img(input_dict['band'], result['band'])   
    
    for i in band_list:    
        if i !="P":
            tmp_band = GIHSA_dict[i].band
            min_val = tmp_band.min()
            if min_val < 0:
                GIHSA_dict[i].band = (tmp_band - min_val)
            else:
                GIHSA_dict[i].band = (tmp_band + min_val)
    
    input_dict['band'] = GIHSA_dict
    input_dict['resolution'] = GIHSA_dict["B"].geoinfo[1]
    input_dict['stage'] = 'pansharpened'
    
    return input_dict