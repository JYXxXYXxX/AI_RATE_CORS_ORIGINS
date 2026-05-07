import httpx

# 构造一个模拟的 .doc 文件内容
content = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1' + '这是一段测试文本，用于验证doc文件解析功能是否正常。'.encode('utf-8') * 20

files = {'file': ('test.doc', content, 'application/msword')}
data = {'title': 'Test Doc', 'subject': '计算机', 'degree_level': '本科'}

r = httpx.post('http://localhost:8010/v1/documents/upload', files=files, data=data, timeout=30)
print('Status:', r.status_code)
print('Response:', r.text[:500])
