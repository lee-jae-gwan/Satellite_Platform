import xml.etree.ElementTree as ET
import glob

meta_path = r'D:\project\RS_img_preprocess\data\resource/'

def meta_check(meta_path):
    meta_list = glob.glob(meta_path + '*_Aux.xml')
    xml_data = ET.parse(meta_list[0])
    for sen_ang in xml_data.iter("Angle"):
        offNadir = float(sen_ang.find("OffNadir").text)

    for tmp_c in xml_data.iter("CloudCover"):
        cloud_rate = float(tmp_c.text)

    if (offNadir < 10) and (cloud_rate == 0):
        return True
















