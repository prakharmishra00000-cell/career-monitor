import re

with open("scratch/sample_post_card.html", "r", encoding="utf-8") as f:
    html = f.read()

keys = re.findall(r'componentkey="([^"]+)"', html)
print(f"Total component keys: {len(keys)}")
for k in set(keys):
    print(k)
