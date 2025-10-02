from kafka import KafkaConsumer
import json
import os
import torch
from transformers import pipeline, AutoModelForCausalLM
from kafka import KafkaProducer



def load_model():
    
    MODEL_NAME = 'beomi/KoAlpaca-Polyglot-5.8B'

    MODEL = None
    PIPE = None
    if MODEL is None or PIPE is None:
        MODEL = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            torch_dtype=torch.float16,
            low_cpu_mem_usage=True,
        ).to('cpu')
        MODEL.eval()

        PIPE = pipeline(
            'text-generation',
            model=MODEL,
            tokenizer=MODEL_NAME,
            device=0
        )
    return PIPE

def ask(question, pipe, context=''): 

    prompt = f"### 질문: {question}\n\n### 맥락: {context}\n\n### 답변:" if context else f"### 질문: {question}\n\n### 답변:"

    ans = pipe(
        prompt,
        do_sample=True,
        max_new_tokens=512,
        temperature=0.7,
        top_p=0.9,
        return_full_text=False,
        eos_token_id=2,
    )
    return ans[0]['generated_text']


def main():
    consumer = KafkaConsumer(
        'question_topic',
        bootstrap_servers = "127.0.0.1:9092",
        auto_offset_reset = "latest",
        value_deserializer = lambda x: json.loads(x.decode('utf-8')),
        group_id = "question_group"
    )
    
    producer = KafkaProducer(
        bootstrap_servers='localhost:9092',
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    PIPE = load_model() 

    last_message = None

    for msg in consumer:
        data = msg.value
        user_id = str(data['user_id'])
        message_id = str(data['message_id'])
        question = data['question']
        print(f"받은 질문: {question} (user_id={user_id})")

        if last_message == message_id:
            continue

        answer = ask(question, PIPE)
        producer.send('answer_topic', {'user_id': user_id,'message_id':message_id, 'answer': answer})
        producer.flush()

        last_message = message_id
        consumer.commit()

if __name__=="__main__":
    main()









