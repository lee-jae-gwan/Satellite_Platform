import os
import numpy as np
import pywt
from multiprocessing import Pool, cpu_count


# ----------------- Wavelet Denoise 함수 -----------------
def wavelet_denoise(img, wavelet='db1', level=1, threshold=0.04, threshold_mode='hard'):
     # 1. 이미지 2D 웨이블릿 분해 (다중 해상도 표현)
    coeffs = pywt.wavedec2(img, wavelet, level)
    cA, detail_coeffs = coeffs[0], coeffs[1:]  # cA: 저주파 성분 (전체 윤곽), detail: 고주파 성분 (노이즈 포함)

    # 2. 고주파 계수들에 대해 threshold 적용 (노이즈 제거 핵심 단계)
    new_detail_coeffs = []
    for (cH, cV, cD) in detail_coeffs:
        cH_th = pywt.threshold(cH, threshold, mode=threshold_mode) # 수평 방향 계수
        cV_th = pywt.threshold(cV, threshold, mode=threshold_mode) # 수직 방향 계수
        cD_th = pywt.threshold(cD, threshold, mode=threshold_mode) # 대각선 방향 계수
        new_detail_coeffs.append((cH_th, cV_th, cD_th))
    
    # 3. 수정된 계수로 이미지 재구성 (역변환)
    coeffs_denoised = [cA] + new_detail_coeffs
    denoised_img = pywt.waverec2(coeffs_denoised, wavelet)

    # 4. 원본의 픽셀 값 범위로 클리핑하여 값 손실 방지
    return np.clip(denoised_img, img.min(), img.max())

def process_wrapper(args):
    input_dict = args[0]
    band_name = args[1]

    band = input_dict.band
    result = wavelet_denoise(band)

    return band_name, result


def run_denoise_parallel(input_dict, wavelet="db1", level=1, threshold=0.04, threshold_mode="hard"):
    band_list = ['B','G','R','N']
    task_list = []
    
    for i in band_list:
        task_list.append((input_dict['band'][i],i))

    # CPU 개수만큼 병렬 실행
    with Pool(processes=cpu_count()) as pool:
        results = pool.map(process_wrapper, task_list)

    denoised_dict = {band:arr for band, arr in results}

    for band_name in ['B', 'G', 'R', 'N']:
       input_dict['band'][band_name].band = denoised_dict[band_name]

    input_dict['stage'] = 'denoised'
    print(f"병렬 노이즈 제거 완료")
    return input_dict
