import re

with open("scratch/sample_post_card.html", "r", encoding="utf-8") as f:
    html = f.read()

print("HTML length:", len(html))

# Search for patterns
for pattern in [
    r'urn:li:[a-zA-Z0-9_:\-]+',
    r'urn%3Ali%3A[a-zA-Z0-9_:\-]+',
    r'activity[0-9:\-_]+',
    r'/feed/update/[^\s"\'<>]+',
    r'/posts/[^\s"\'<>]+',
    r'href="([^"]+)"',
    r'data-[a-zA-Z0-9\-]+="([^"]+)"'
]:
    matches = re.findall(pattern, html)
    print(f"\nPattern: {pattern} -> {len(matches)} matches")
    for m in list(set(matches))[:10]:
        print(f"  {repr(m[:100])}")
