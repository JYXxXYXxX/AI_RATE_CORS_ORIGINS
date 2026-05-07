from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

model_path = 'data/models/aigc-detector'
tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForSequenceClassification.from_pretrained(model_path)

text = '这是一个测试文本，用于验证模型是否加载成功。'
inputs = tokenizer(text, return_tensors='pt', truncation=True, max_length=512)
with torch.no_grad():
    outputs = model(**inputs)
    probs = torch.softmax(outputs.logits, dim=-1)
    pred = torch.argmax(probs, dim=-1).item()

label = "AI生成" if pred == 1 else "人工撰写"
print(f'预测结果: {label}')
print(f'置信度: {probs[0][pred].item():.4f}')
