import os, traceback
from huggingface_hub import InferenceClient
from dotenv import load_dotenv
load_dotenv()
try:
    token = os.environ.get('HF_TOKEN')
    model = os.environ.get('HF_MODEL')
    print(f"Using model: {model}")
    # client = InferenceClient("gpt2")
    # print(client.text_generation("Hello", max_new_tokens=10))
    client = InferenceClient(token=token)
    print('InferenceClient created; api_url attr:', getattr(client, 'api_url', None))
    response = client.chat.completions.create(
        model=model, 
        messages=[{"role": "system", "content": "Hello, world!"}]
        )
    print(response)
except Exception as e:
    print('Error creating InferenceClient:', e)
    traceback.print_exc()
