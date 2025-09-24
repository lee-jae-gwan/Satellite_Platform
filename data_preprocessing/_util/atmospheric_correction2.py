from _util.gdal_class import gdal_data
from datetime import datetime
import xml.etree.ElementTree as ET
from pyproj import Transformer
import copy
import sys
import ee
import math
from Py6S import*
import os
from google.oauth2 import service_account
from PIL import Image
import glob

sys.path.append(os.path.join(os.path.dirname(__file__), 'gee_atmcorr_S2'))

import numpy as np
from bin.atmospheric import Atmospheric


def spectralResponseFunction(bandname):
    """
    Extract spectral response function for given band name
    """
    bandSelect = {
        'B1': PredefinedWavelengths.S2A_MSI_01,
        'B2': PredefinedWavelengths.S2A_MSI_02,
        'B3': PredefinedWavelengths.S2A_MSI_03,
        'B4': PredefinedWavelengths.S2A_MSI_04,
        'B5': PredefinedWavelengths.S2A_MSI_05,
        'B6': PredefinedWavelengths.S2A_MSI_06,
        'B7': PredefinedWavelengths.S2A_MSI_07,
        'B8': PredefinedWavelengths.S2A_MSI_08,
        'B8A': PredefinedWavelengths.S2A_MSI_8A,
        'B9': PredefinedWavelengths.S2A_MSI_09,
        'B10': PredefinedWavelengths.S2A_MSI_10,
        'B11': PredefinedWavelengths.S2A_MSI_11,
        'B12': PredefinedWavelengths.S2A_MSI_12,
    }
    return Wavelength(bandSelect[bandname])

def georeferencing(xml_data, src_data):
    root = xml_data
    
    for tmp in root.iter("ImageGeogTL"):
        lon = tmp.find("Longitude").text
        lat = tmp.find("Latitude").text
    
    
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:5179", always_xy=True)
    x,y = transformer.transform(lon, lat)
    list_geoinfo = list(src_data.geoinfo)
    list_geoinfo[0] = x
    list_geoinfo[3] = y
    src_data.geoinfo = tuple(list_geoinfo)

    return src_data


def get_date(meta_data):
    for tmp_date in meta_data.iter('ImagingStartTime'):
        date = tmp_date.find('UTC').text

    Y = date[:4]
    m = date[4:6]
    d = date[6:8]
    H = date[8:10]
    M = date[10:12]
    S = date[12:14]
    ee_date = ee.Date(Y + '-' + m + '-' + d)

    dt_part = date[:14]
    frac_part = date[15:]

    microsecond = int(frac_part[:6].ljust(6, '0'))
    dt = datetime.strptime(dt_part, '%Y%m%d%H%M%S').replace(microsecond=microsecond)

    return ee_date, dt


def get_geometry(meta_data):
    for child in meta_data.iter('ImageGeogCenter'):
        latitude = float(child.find('Latitude').text)
        longitude = float(child.find('Longitude').text)

    return latitude, longitude


def get_atmos(geom, date):
    h2o = Atmospheric.water(geom, date).getInfo()
    o3 = Atmospheric.ozone(geom, date).getInfo()
    aot = Atmospheric.aerosol(geom, date).getInfo()

    return h2o, o3, aot


def get_solar_zenith(meta_data):
    sun_ang = next(meta_data.iter("SunAngle"))
    solar_zenith = 90 - float(sun_ang.find("Elevation").text)
    return solar_zenith


def get_bandwith(meta):
    for r in meta.iter("MS3"):
        r_b = r.find('Bandwidth').text
        r_bandwidth = (int(r_b.split('-')[0]) + int(r_b.split('-')[1])) / 2

        for i in r.iter('RadianceConversion'):
            r_gain = float(i.find('Gain').text)
            r_offset = float(i.find('Offset').text)

    return r_gain, r_offset


def get_nadir(meta):
    for sen_ang in meta.iter("Angle"):
        offNadir = float(sen_ang.find("OffNadir").text)

    return offNadir


def get_altitude(meta):
    for alti in meta.iter("SatellitePosition"):
        altitude = round(float(alti.find("Altitude").text))

    return altitude


### 메인코드
def transform_atmos(img, xml_data, band_num):
    band = img
    meta_data = xml_data
 
    s = SixS(r'D:\Download\6SV-1.1\6SV1.1\sixsV1.1')
    
    ee_date, dt = get_date(meta_data)  # 날짜 추출 및 구글어스엔진의 날짜 타입으로 변환
    longitude, latitude = get_geometry(meta_data)  # 위치 좌표 추출
    geom = ee.Geometry.Point(longitude, latitude)  # 구글어스엔진으로 좌표 저장
    h2o, o3, aot = get_atmos(geom, ee_date)  # 구글어스엔진으로 수증기, 오존, 에어로졸 추출
    solar_zenith = get_solar_zenith(meta_data)  # 태양천정각 계산
    offNadir = get_nadir(meta_data)  # 센서 시야각
    altitude = get_altitude(meta_data)  # 태양 고도
    # sat_alti = get_sat_altitude(meta_data)

    ###대기 모델 제작
    s.atmos_profile = AtmosProfile.UserWaterAndOzone(h2o, o3)
    s.aero_profile = AeroProfile.Continental
    s.aot550 = aot
    s.geometry = Geometry.User()
    s.geometry.view_z = offNadir  # 모델에 센서 시야각 설정
    s.geometry.solar_z = solar_zenith  # 모델에 태양 천정각 설정
    s.geometry.month = dt.month
    s.geometry.day = dt.day
    s.altitudes.set_sensor_satellite_level()
    # s.altitudes.set_target_custom_altitude(altitude)
    # bandwith = get_bandwith(meta_data)#밴드 대역폭 추출

    s.wavelength = spectralResponseFunction(band_num)  # SRFf를 sentinel 영상에 근사
    s.run()


    Edir = s.outputs.direct_solar_irradiance  # 직접 태양 복사에너지양
    Edif = s.outputs.diffuse_solar_irradiance  # 산란 태양 복사에너지양
    Lp = s.outputs.atmospheric_intrinsic_radiance  # 대기 방출, 산란 복사에너지양
    absorb = s.outputs.trans['global_gas'].upward  # 대기 가스에 의한 상향 투과율 => 가스 흡수 없이 위로 통과할 확률
    scatter = s.outputs.trans['total_scattering'].upward  # 전체 대기 산란 효과를 반영한 => 상향 방향의 총 투과율
    tau2 = absorb * scatter  # 복사에너지가 위로 올라가면서 대기 중 가스 흡수와 산란을 모두 통과할 수 있는 비율

    ref = (band - Lp) * (math.pi) / (tau2 * (Edir + Edif))  # 산출식에 의한 대기보정 결과 저장

    # band.band = ref
    # band.Write(result_path, 'atmos_correction')

    return ref


def normalize_img(img):
    img = img.astype(np.float32) 

    img_min = img.min()
    img_max = img.max()

    if img_max == img_min:
        return np.zeros_like(img, dtype=np.uint16)

    if img_min < 0:
        img = img - img_min
        img_max = img.max()

    normalized_img = ((img - img.min()) / (img.max() - img.min())) * 65535.0
    return normalized_img.astype(np.uint16)

def normalize_img8bit(img):
    img = img.astype(np.float32) 

    img_min = img.min()
    img_max = img.max()

    if img_max == img_min:
        return np.zeros_like(img, dtype=np.uint8)

    if img_min < 0:
        img = img - img_min
        img_max = img.max()

    normalized_img = ((img - img.min()) / (img.max() - img.min())) * 255.0
    return normalized_img.astype(np.uint8)

def normalize_img8bit_safe(img):
    img = img.astype(np.float32)
    
    # NaN/Inf 제거
    img = np.nan_to_num(img, nan=0.0, posinf=0.0, neginf=0.0)
    
    img_min = img.min()
    img_max = img.max()

    # 모든 값이 동일하면 0 반환
    if img_max == img_min:
        return np.zeros_like(img, dtype=np.uint8)

    # 0~1로 정규화
    img = (img - img_min) / (img_max - img_min)
    # 0~255 스케일 후 uint8 변환
    img8 = (img * 255.0).round().astype(np.uint8)

    return img8


def run_atmos_correction(input_dict):
    ms_list = ["B","G","R","N"]
    
    SERVICE_ACCOUNT_KEY = input_dict['EE_authKey']
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_KEY,
        scopes=['https://www.googleapis.com/auth/earthengine']
    )

    ee.Initialize(credentials)
    
    xml_data = input_dict['xml']
    ac_data_dict = input_dict['band']

    band_num = "-"
    for i in ms_list:
        if  i == "B":
            band_num = "B2"
        elif i == "G":
            band_num = "B3"
        elif i == "R":
            band_num = "B4"
        elif i == "N":
            band_num = "B8"

        img_dataset = ac_data_dict[i]
        img_dataset = georeferencing(xml_data, img_dataset)
        band = img_dataset.band

        tmp_corr_band = transform_atmos(band, xml_data,band_num)
        tmp_norm_band = normalize_img8bit_safe(tmp_corr_band)

        ac_data_dict[i].band = tmp_norm_band

    input_dict['band'] = ac_data_dict
    input_dict['stage'] = 'atmos_corrected'

    return input_dict