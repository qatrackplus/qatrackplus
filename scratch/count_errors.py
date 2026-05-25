import json
import collections
from pathlib import Path

data = json.loads(Path(r'c:\Users\nsmel\source\repos\qatrackplusplus\ruff.json').read_text(encoding='utf-8'))
counts = collections.Counter(item['code'] for item in data)
for code, count in counts.most_common():
    print(f"{code}: {count}")
