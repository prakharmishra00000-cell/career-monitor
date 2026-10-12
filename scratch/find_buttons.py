with open("scratch/sample_post_card.html", "r", encoding="utf-8") as f:
    html = f.read()

from bs4 import BeautifulSoup
soup = BeautifulSoup(html, "html.parser")
btn2 = soup.find_all("button")[1]
print("Btn 2 outerHTML:\n", btn2.prettify())
print("\nBtn 2 parent outerHTML:\n", btn2.parent.prettify()[:1000])
