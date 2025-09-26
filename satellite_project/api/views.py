from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import SatelliteImageSerializer
from .models import SatelliteImage
from kafka import KafkaProducer
from kafka import KafkaConsumer
import json
import uuid
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from minio import Minio
from datetime import timedelta
from minio.error import S3Error
import urllib

from collections import defaultdict
import uuid

producer = KafkaProducer(
    bootstrap_servers = '127.0.0.1:9092',
    value_serializer = lambda v : json.dumps(v).encode('utf-8')
)

consumer = KafkaConsumer(
    'answer_topic',
    bootstrap_servers='localhost:9092',
    value_deserializer=lambda v: json.loads(v.decode('utf-8')),
    group_id='django-consumer-group'
)

# Create your views here.
class UploadSatelliteImage(APIView):

    def get(self, request):
        return render(request, 'api/upload.html')

    def post(self, request):
        print("POST 요청 들어옴")
        print("FILES:", request.FILES)
        print("DATA:", request.data)

        serializer = SatelliteImageSerializer(data=request.data)
        if serializer.is_valid():
            obj = serializer.save()

            # Kafka producer
            producer = KafkaProducer(
                bootstrap_servers='localhost:9092',
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            message = {'file_path': obj.file.path}
            producer.send('satellite_topic', message)

            return render(request, 'api/upload.html', {'uploaded_url': obj.file.url, 'message': '업로드 완료!'})
        return render(request, 'api/upload.html', {'errors': serializer.errors})
    

def index_page(request):
    bucket_name = "satellite-images"
    
    # 버킷이 존재하지 않으면 생성
    try:
        if not minio_client.bucket_exists(bucket_name):
            minio_client.make_bucket(bucket_name)
    except S3Error as err:
        print(f"MinIO 에러: {err}")

    return render(request, 'index.html')


minio_client = Minio(
    "localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False
)


def get_presigned_url(request):
    bucket = "satellite-images"
    original_name = request.GET.get("filename")

    file_uuid = str(uuid.uuid4())

    object_name = f"{file_uuid}_{original_name}"
    print(object_name)

    # presigned url 생성 (유효기간: 1시간)
    url = minio_client.presigned_put_object(bucket, object_name, expires=timedelta(hours=1))
    
    return JsonResponse({"url": url, "uuid": file_uuid, "filename": original_name ,"objectname": object_name})


@csrf_exempt
def get_presigned_folderurl(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST 요청만 허용"}, status=400)

    import json
    data = json.loads(request.body)
    files = data.get("files")  # ["img1.tif", "img2.tif", ...]

    bucket = "satellite-images"
    folder_uuid = str(uuid.uuid4())  # 폴더 단위 UUID
    urls = []

    for file_name in files:
        object_name = f"{folder_uuid}/{file_name}"
        url = minio_client.presigned_put_object(bucket, object_name, expires=timedelta(hours=1))
        urls.append({"file_name": file_name, "object_name": object_name, "url": url})

    return JsonResponse({"folder_uuid": folder_uuid, "files": urls})


def check_file(request):
    bucket = "satellite-images"
    object_name = request.GET.get("object_name")
    try:
        info = minio_client.stat_object(bucket, object_name)
        return JsonResponse({"exists": True, "size": info.size})
    except S3Error:
        return JsonResponse({"exists": False})

def upload_status(request):
    if request.method == "POST":
        data= json.loads(request.body)
        object_name = data.get("object_name")
        upload_status = data.get("status")
        file_size = data.set("size")

        print(f"파일: {object_name}, 업로드 성공: {status}, 크기: {file_size}")

        return JsonResponse({"Message": "status received"})
    return JsonResponse({"error": "POST 요청만 허용"}, status = 400)


@csrf_exempt
def minio_event(request):
    if request.method=="POST":
        try:
            events = json.loads(request.body)
            uuid_dict = defaultdict(list)

            for record in events.get("Records",[]):
                key = record['S3']['object']['key']
                decode_key = urllib.parse.unquote(key)
                folder_uuid = decode_key.split('/')[0]
                uuid_dict[folder_uuid].append(record)
            
            for uuid, records in uuid_dict.items():
                message = {'uuid':uuid, 'files':records}
                producer.send("satellite_topic",key = uuid.encode('utf-8'), value = message)

            producer.flush()
            return JsonResponse({'stataus':'OK'})
        
        except Exception as e:
            return JsonResponse({'status':'error', 'message':str(e)}, status=500)
    
    return JsonResponse({'status':'method not allowed'}, status =405)

@csrf_exempt
def ask(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user_id = str(123)
        message_id = str(uuid.uuid4())
        question = data.get("query")

        print("사용자 질문", question)

        producer.send('question_topic', {'user_id':user_id, 'message_id':message_id,'question':question})
        print('question topic 전송')
        producer.flush()

        return JsonResponse({'status': 'ok'}) 
    else:
        return JsonResponse({'error':'POST 요청만 허용됩니다.'})
