with open("scratch/sample_post_card.html", "r", encoding="utf-8") as f:
    html = f.read()

from bs4 import BeautifulSoup
soup = BeautifulSoup(html, "html.parser")
for idx, a in enumerate(soup.find_all("a")):
    print(f"Anchor #{idx+1}: href={repr(a.get('href'))} text={repr(a.get_text(strip=True)[:40])} attrs={a.attrs}")
