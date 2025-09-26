# myapp/kafka_consumer.py
from kafka import KafkaConsumer
import json
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def start_consumer():
    consumer = KafkaConsumer(
        'answer_topic',
        bootstrap_servers='localhost:9092',
        value_deserializer=lambda v: json.loads(v.decode('utf-8')),
        auto_offset_reset = "latest",
        group_id='django-consumer-group'
    )

    channel_layer = get_channel_layer()

    for msg in consumer:
        data = msg.value
        user_id = str(data['user_id'])
        answer = data['answer']
        message_id = str(data['message_id'])
        print(f"user_id: {user_id}, answer: {answer}")

        print(f"[DEBUG] Sending to group: user_123, type: {type(user_id)}")
        async_to_sync(channel_layer.group_send)(
            f"user_{user_id}",
            {
                "type": "chat.message",
                "message": answer
            }
        )
        print("[DEBUG] Message sent")



