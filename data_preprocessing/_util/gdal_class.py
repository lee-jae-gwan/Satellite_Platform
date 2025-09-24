from osgeo import gdal, osr
import numpy as np
import os

class gdal_data:
    def __init__(self):
        self.geoinfo = None
        self.xsize = None
        self.ysize = None
        self.band = None
        self.proj = None
        self.filename = None
        self.dtype = None
        self.nodata = None
        self.filepath = None

    @classmethod
    def Open(cls, path):
        obj = cls()

        no_data_value = -9999

        dataset = gdal.Open(path, gdal.GA_ReadOnly)
        obj.geoinfo = dataset.GetGeoTransform()
        obj.xsize = dataset.GetRasterBand(1).ReadAsArray().shape[1]
        obj.ysize = dataset.GetRasterBand(1).ReadAsArray().shape[0]
        obj.filepath = path
        proj_wkt = dataset.GetProjectionRef()

        if not proj_wkt:
            print("좌표계 정보 없음. EPSG:5179 (Korea 2000 / Unified CS)로 설정합니다.")
            srs = osr.SpatialReference()
            srs.ImportFromEPSG(5179)
            proj_wkt = srs.ExportToWkt()

        obj.proj = proj_wkt

        last_slash = max(path.rfind('/'), path.rfind('\\'))
        obj.filename = path[last_slash + 1:]
        raster_count = dataset.RasterCount

        if raster_count >= 2:
            tmp_bands = []
            for i in range(1, raster_count + 1):
                read_raster = dataset.GetRasterBand(i)
                tmp_band = read_raster.ReadAsArray()
                tmp_bands.append(tmp_band)

            stacked = np.dstack(tmp_bands)
        elif raster_count == 1:
            read_raster = dataset.GetRasterBand(1)
            stacked = read_raster.ReadAsArray()

        band_img = stacked
        obj.band = band_img

        return obj

    def copy(self):
        obj_copy = gdal_data()
        obj_copy.__dict__.update(self.__dict__)
        if isinstance(self.band, np.ndarray):
            obj_copy.band = self.band.copy()

        return obj_copy

    def Write(self, path, work):
        band = self.band  # shape: (bands, rows, cols) 또는 (rows, cols)
        geoinfo = self.geoinfo
        proj = self.proj
        driver = gdal.GetDriverByName("GTiff")
        filename = self.filename
        no_data_value = -9999

        # 저장 파일명 설정
        file_format = filename[filename.rfind("."):]
        if work:  # work가 비어있지 않으면
            dst_filename = filename[:filename.rfind(".")] + "_" + work + file_format
        else:  # work가 빈 문자열이면
            dst_filename = filename[:filename.rfind(".")] + file_format

        dstpath = os.path.join(path, dst_filename)

        if band.ndim == 2:
            # (rows, cols) → (1, rows, cols)
            band = np.expand_dims(band, axis=0)
        elif band.ndim == 3:
            pass  # 이미 (bands, rows, cols)
        else:
            raise ValueError(f"지원하지 않는 배열 차원: {band.shape}")

        num_bands, rows, cols = band.shape
        output_dtype = str(band.dtype)

        dtype_map = {
            "uint16": gdal.GDT_UInt16,
            "uint8": gdal.GDT_Byte,
            "uint32": gdal.GDT_UInt32,
            "int16": gdal.GDT_Int16,
            "int32": gdal.GDT_Int32,
            "float32": gdal.GDT_Float32,
            "float64": gdal.GDT_Float64
        }

        if output_dtype not in dtype_map:
            raise ValueError(f"지원하지 않는 데이터 타입: {output_dtype}")

        gdal_dtype = dtype_map[output_dtype]

        output_raster = driver.Create(dstpath, cols, rows, num_bands, gdal_dtype)
        output_raster.SetGeoTransform(geoinfo)
        output_raster.SetProjection(proj)

        for i in range(num_bands):
            band_obj = output_raster.GetRasterBand(i + 1)
            band_obj.SetNoDataValue(no_data_value)
            band_obj.SetScale(1.0)
            band_obj.SetOffset(0.0)
            band_obj.WriteArray(band[i])  # shape: (rows, cols)

        output_raster.FlushCache()
        output_raster = None

        print(f"저장 완료: {dstpath}")

    @classmethod
    def from_dataset(cls, dataset, path=None):
        obj = cls()

        obj.geoinfo = dataset.GetGeoTransform()
        obj.xsize = dataset.RasterXSize
        obj.ysize = dataset.RasterYSize
        obj.proj = dataset.GetProjectionRef()

        if path:
            last_slash = max(path.rfind('/'), path.rfind('\\'))
            obj.filename = path[last_slash + 1:]
        else:
            obj.filename = "unknown.tif"

        band_obj = dataset.GetRasterBand(1)
        obj.dtype = gdal.GetDataTypeName(band_obj.DataType)
        obj.nodata = band_obj.GetNoDataValue()
        obj.band = band_obj.ReadAsArray()

        return obj