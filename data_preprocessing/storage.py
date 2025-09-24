from minio import Minio
import sys
from _util.gdal_class import gdal_data
import xml.etree.ElementTree as ET
from osgeo import gdal

def get_minio_client():
    return Minio(
        "localhost:9000",
        access_key = "minioadmin",
        secret_key = "minioadmin",
        secure = False
    )


def minioto_file(client, uuid):
    print("minio에사 파일 가져오기")
    img_list = []
    PS_img_list = []
    xml_list = []
    for obj in client.list_objects('satellite-images',prefix = uuid,recursive=True):
        print(obj.object_name)
        response = client.get_object('satellite-images',obj.object_name)
        
        if obj.object_name.endswith("PS.tif"):
            data = response.read()
            
            filename = obj.object_name.split('/')[-1]
            minio_path = f'/vsimem/{filename}'
            
            gdal.FileFromMemBuffer(minio_path,data)
            
            tif_data = gdal_data.Open(minio_path)
            PS_img_list.append(tif_data)

            gdal.Unlink(minio_path)
            
        elif obj.object_name.endswith(".tif"):
            data = response.read()
            
            filename = obj.object_name.split('/')[-1]
            minio_path = f'/vsimem/{filename}'
            
            gdal.FileFromMemBuffer(minio_path,data)
            
            tif_data = gdal_data.Open(minio_path)
            img_list.append(tif_data)

            gdal.Unlink(minio_path)
        elif obj.object_name.endswith("Aux.xml"):
            data = response.read()
            xml_data = data.decode("utf-8")
            xml_data = ET.fromstring(xml_data)
            xml_list.append(xml_data)
        else:
            print(f'지원하지 않는 데이터타입 입니다 {obj.object_name}')
        response.close()
        response.release_conn()

    return img_list, PS_img_list, xml_list


