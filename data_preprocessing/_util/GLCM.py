import numpy as np
import glob
import cv2
from _util.gdal_class import gdal_data
import os
import cupy as cp
from cupyx.scipy.ndimage import convolve
import copy


def glcm_homogeneity(img, levels=8, kernel_size=5):
    angles = [(1, 0), (1, -1), (0, -1), (-1, -1)]  # GLCM 계산 방향(0번-> 오른쪽, 1번-> 오른쪽 아래(대각), 2번-> 아래쪽, 3번-> 왼쪽 아래(대각)
    h, w = img.shape  # 이미지 너비, 높이
    pix_val = 256 // levels  # level map-> 0~255 사이의 픽셀 값을 0~7 사이의 값으로 매핑, 이유: 연산량 감소
    level_img = (img // pix_val).astype(np.uint8)  # level map-> 0~255 사이의 픽셀 값을 0~7 사이의 값으로 매핑

    tmp_i = np.arange(levels).reshape((-1, 1))  # GLCM의 행(0~7사이의 값)
    tmp_j = np.arange(levels).reshape((1, -1))  # GLCM의 열(0~7사이의 값)
    weight = 1.0 / (1.0 + (tmp_i - tmp_j) ** 2)  # 가중치(균질성) 구하는 수식

    feature_map_sum = np.zeros((h, w), dtype=np.float32)  # 출력값인 균질성 영상

    # GLCM 계산 시작
    for dx, dy in angles:  # GLCM 구하는 방향에 따른 반복문
        mat = np.array([[1.0, 0.0, -dx], [0.0, 1.0, -dy]], dtype=np.float32)  # GLCM을 구하는 방향 설정(총 4번, angles 설명 참조)
        shifted = cv2.warpAffine(level_img, mat, (w, h), flags=cv2.INTER_NEAREST,
                                 borderMode=cv2.BORDER_REPLICATE)  # 커널을 이동하는 함수

        glcm = np.zeros((levels, levels, h, w),
                        dtype=np.uint8)  # GLCM 행렬 초기화(level * level 크기의 2차원 행렬이 전체 이미지의 너비*높이만큼 제작됨)
        for i in range(levels):
            for j in range(levels):
                mask = (level_img == i) & (shifted == j)  # 인접한 픽셀의 조합이(i,j)인 경우를 추출
                glcm[i, j][mask] = 1

        kernel = np.ones((kernel_size, kernel_size), dtype=np.uint8)  # 국소적 GLCM 계산을 위한 커널 크기 지정
        for i in range(levels):  # levels * levels 만큼 도는 이유: GLCM의 크기가 levels * levels이기 때문
            for j in range(levels):
                glcm[i, j] = cv2.filter2D(glcm[i, j], -1,
                                          kernel)  # 전역적 GLCM을 기반으로 국소적 GLCM을 계산하는 함수(픽셀별로 순회하며 커널 내의 값을 합산하여 국소적 GLCM 구성)

        feature_map = np.zeros((h, w), dtype=np.float32)
        for i in range(levels):
            for j in range(levels):
                feature_map += glcm[i, j] * weight[i, j]  # 국소적 GLCM들을 기반으로 가중치를 곱하여 하나의 균질성 영상 제작

        feature_map_sum += feature_map

    # GLCM 계산 종료
    feature_map_avg = feature_map_sum / len(angles)
    return feature_map_avg


def glcm_homogeneity_gpu(img_cp, levels=8, kernel_size=5):

    # 1. Normalize and quantize
    img_min, img_max = img_cp.min(), img_cp.max()
    img_scaled = ((img_cp - img_min) / (img_max - img_min + 1e-5)) * (levels - 1)
    img_q = img_scaled.astype(cp.uint8)

    # 2. Shift image by 1 pixel to the right (for 0° direction)
    img_right = cp.pad(img_q[:, 1:], ((0, 0), (0, 1)), mode='edge')

    # 3. Prepare GLCM stack
    H, W = img_cp.shape
    glcm = cp.zeros((levels, levels, H, W), dtype=cp.float32)

    # 4. Count co-occurrences for each (i, j) pair
    for i in range(levels):
        mask_i = (img_q == i).astype(cp.uint8)
        for j in range(levels):
            mask_j = (img_right == j).astype(cp.uint8)
            combined = mask_i * mask_j
            glcm[i, j] = convolve(combined, cp.ones((kernel_size, kernel_size), dtype=cp.uint8), mode='reflect')

    # 5. Homogeneity computation
    i_idx = cp.arange(levels).reshape((-1, 1, 1, 1))
    j_idx = cp.arange(levels).reshape((1, -1, 1, 1))
    weight = 1.0 / (1.0 + (i_idx - j_idx)**2)

    homogeneity = cp.sum(glcm * weight, axis=(0, 1))

    return homogeneity

# 영상을 8비트로 변환하는 함수
def band_normalize_8bit(band):
    """
    0단계: 밴드의 최소값 최대값을 구함
    1단계: (픽셀 값 - 최소값) / (최대값 - 최소값) ==> 모든 픽셀들의 값이 0~1 사이의 값으로 정규화됨
    2단계: 정규화된 픽셓 값들에 8bit 영상의 최대값인 255를 곱하여 0 ~ 255 사이의 값으로 재분배
    """
    min_val = band.min()  # 밴드의 최대값
    max_val = band.max()  # 밴드의 최소값
    return (((band - min_val) / (max_val - min_val)) * 255).astype(np.uint8)


# 영상을 16비트로 변환하는 함수
def band_normalize_16bit(band):
    """
    0단계: 밴드의 최소값 최대값을 구함
    1단계: (픽셀 값 - 최소값) / (최대값 - 최소값) ==> 모든 픽셀들의 값이 0~1 사이의 값으로 정규화됨
    2단계: 정규화된 픽셓 값들에 8bit 영상의 최대값인 255를 곱하여 0 ~ 255 사이의 값으로 재분배
    """
    min_val = band.min()  # 밴드의 최소값
    max_val = band.max()  # 밴드의 최대값
    return (((band - min_val) / (max_val - min_val)) * 65535).astype(np.uint16)


def get_tiles(image, tile_size, overlap=0):
    tiles = []
    h, w = image.shape
    step = tile_size - overlap

    for y in range(0, h, step):
        for x in range(0, w, step):
            y_end = min(y + tile_size, h)
            x_end = min(x + tile_size, w)
            tile = image[y:y_end, x:x_end]
            tiles.append((tile, y, x))  # 타일과 좌표 함께 저장
    return tiles


def run_GLCM(src_path, result_path):
    ndvi_path = glob.glob(src_path + '/*_NDVI.tif')
    ndwi_path = glob.glob(src_path + '/*_NDWI.tif')

    ndvi_dataset = gdal_data.Open(ndvi_path[0])
    ndwi_dataset = gdal_data.Open(ndwi_path[0])

    ndvi_band = ndvi_dataset.band + 1
    ndwi_band = ndwi_dataset.band + 1

    ndvi_band = np.where(ndvi_band == -9998, 0, ndvi_dataset.band)
    ndwi_band = np.where(ndwi_band == -9998, 0, ndwi_dataset.band)

    ndvi_8bit = band_normalize_8bit(ndvi_band)
    ndwi_8bit = band_normalize_8bit(ndwi_band)

    kernel_size = 5
    levels = 8

    img_tiles = []
    img_tiles = get_tiles(ndvi_8bit, 1024)

    ndvi_feature_map = np.zeros_like(ndvi_8bit, dtype=np.float32)
    ndwi_feature_map = np.zeros_like(ndwi_8bit, dtype=np.float32)

    for tile, y, x in get_tiles(ndvi_8bit, tile_size=1024, overlap=0):
        result = glcm_homogeneity(tile, levels=8, kernel_size=5)
        h, w = result.shape
        ndvi_feature_map[y:y + h, x:x + w] = result

    for tile, y, x in get_tiles(ndwi_8bit, tile_size=1024, overlap=0):
        result = glcm_homogeneity(tile, levels=8, kernel_size=5)
        h, w = result.shape
        ndwi_feature_map[y:y + h, x:x + w] = result

    ndvi_feature_map = ndvi_feature_map.astype(np.uint8)
    ndwi_feature_map = ndwi_feature_map.astype(np.uint8)

    ndvi_dataset.band = band_normalize_16bit(ndvi_feature_map)
    ndwi_dataset.band = band_normalize_16bit(ndwi_feature_map)

    ndvi_dataset.dtype = np.uint16
    ndwi_dataset.dtype = np.uint16

    ndvi_dataset.Write(result_path, 'GLCM')
    ndwi_dataset.Write(result_path, 'GLCM')


def run_GLCM_gpu(input_dict):
    #ndvi_path = glob.glob(src_path + '/*_NDVI.tif')
    #ndwi_path = glob.glob(src_path + '/*_NDWI.tif')

    #ndvi_dataset = gdal_data.Open(ndvi_path[0])
    #ndwi_dataset = gdal_data.Open(ndwi_path[0])
    ndvi_dataset = copy.deepcopy(input_dict['band']['NDVI'])
    ndwi_dataset = copy.deepcopy(input_dict['band']['NDWI'])

    ndvi_band = ndvi_dataset.band + 1
    ndwi_band = ndwi_dataset.band + 1

    ndvi_band = np.where(ndvi_band == -9998, 0, ndvi_dataset.band)
    ndwi_band = np.where(ndwi_band == -9998, 0, ndwi_dataset.band)

    ndvi_8bit = band_normalize_8bit(ndvi_band)
    ndwi_8bit = band_normalize_8bit(ndwi_band)

    ndvi_8bit = cp.array(ndvi_8bit)
    ndwi_8bit = cp.array(ndwi_8bit)
    
    kernel_size = 5
    levels = 8

    img_tiles = []
    img_tiles = get_tiles(ndvi_8bit, 1024)

    ndvi_feature_map = cp.zeros_like(ndvi_8bit, dtype=cp.float32)
    ndwi_feature_map = cp.zeros_like(ndwi_8bit, dtype=cp.float32)

    for tile, y, x in get_tiles(ndvi_8bit, tile_size=1024, overlap=5):
        result = glcm_homogeneity_gpu(tile, levels=8, kernel_size=5)
        h, w = result.shape
        ndvi_feature_map[y:y + h, x:x + w] = result

    for tile, y, x in get_tiles(ndwi_8bit, tile_size=1024, overlap=5):
        result = glcm_homogeneity_gpu(tile, levels=8, kernel_size=5)
        h, w = result.shape
        ndwi_feature_map[y:y + h, x:x + w] = result

    ndvi_feature_map_cp = ndvi_feature_map.astype(cp.uint8)
    ndwi_feature_map_cp = ndwi_feature_map.astype(cp.uint8)

    ndvi_feature_map = ndvi_feature_map_cp.get()
    del ndvi_feature_map_cp
    
    ndwi_feature_map = ndwi_feature_map_cp.get()
    del ndwi_feature_map_cp

    ndvi_dataset.band = band_normalize_16bit(ndvi_feature_map)
    ndwi_dataset.band = band_normalize_16bit(ndwi_feature_map)
    
    ndvi_dataset.dtype = np.uint16
    ndwi_dataset.dtype = np.uint16
    
    tmp_filename = input_dict['filename']
    ext = '.tif'

    ndvi_dataset.filename = tmp_filename + "_GLCM" + ext
    ndwi_dataset.filename = tmp_filename + "_GLCM" + ext

    input_dict['band']['NDVI_GLCM'] = ndvi_dataset
    input_dict['band']['NDWI_GLCM'] = ndwi_dataset
    input_dict['stage'] = 'Spectral_IDX(GLCM)'

    #ndvi_dataset.Write(result_path, 'GLCM')
    #ndwi_dataset.Write(result_path, 'GLCM')

    return input_dict