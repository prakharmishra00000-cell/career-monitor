with open("scratch/sample_post_card.html", "r", encoding="utf-8") as f:
    html = f.read()

from bs4 import BeautifulSoup
soup = BeautifulSoup(html, "html.parser")

for p in soup.find_all("p"):
    if "59m" in p.get_text():
        print("P element:\n", p.prettify())
        print("P parent:\n", p.parent.prettify())
