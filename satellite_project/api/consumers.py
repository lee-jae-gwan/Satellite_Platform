from channels.generic.websocket import AsyncWebsocketConsumer
import json

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = str(self.scope['url_route']['kwargs']['user_id'])
        print(f"[DEBUG] WebSocket user_id type: {type(self.user_id)}, value: {self.user_id}")

        self.group_name = f"user_{self.user_id}"
        print(f"[DEBUG] Joining group: {self.group_name}")
        # 그룹에 참여
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()
        print(f"[DEBUG] 웹소켓 입장: {self.group_name}")  # ← 디버그 로그

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    # Kafka에서 보낸 메시지 처리
    async def chat_message(self, event):
        message = event['message']
        print(f"[DEBUG] ChatConsumer received: {message}")
        await self.send(text_data=json.dumps({"message": message}))