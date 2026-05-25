import json
import os

data = json.load(open(r'c:\Users\nsmel\source\repos\qatrackplusplus\ruff.json', encoding='utf-16'))
for item in data:
    if item['code'] != 'UP031':
        print(f"{item['code']}:{item['location']['row']}:{item['filename']} {item['message']}")
