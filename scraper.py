#!/usr/bin/env python3

# Blogz Des Fous Crazy - Scraper multi-sources

# Sources :

# - IT-Connect : https://www.it-connect.fr/actualites/actu-securite/

# - INCYBER    : https://incyber.org/categorie/cyber/

import hashlib
import json
import re
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

HEADERS = {
"User-Agent": (
"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
"AppleWebKit/537.36 (KHTML, like Gecko) "
"Chrome/122.0.0.0 Safari/537.36"
)
}
TIMEOUT = 15
DELAY = 1.2
MAX_ARTICLES = 15

def get(url):
try:
r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
r.raise_for_status()
return BeautifulSoup(r.text, "lxml")
except Exception as e:
print("  WARNING GET failed: " + url + " - " + str(e))
return None

def make_hash(url):
return hashlib.sha256(url.encode()).hexdigest()

def clean_html(tag):
if not tag:
return ""
for el in tag.find_all(["script", "style", "noscript" , "iframe"]):
el.decompose()
for img in tag.find_all("img"):
src = img.get("data-src") or img.get("data-lazy-src") or img.get("src", "")
if src and not src.startswith("data:"):
img["src"] = src
else:
img.decompose()
return str(tag)

def read_time(html):
words = len(re.sub(r"<[^>]+>", " ", html).split())
return max(1, round(words / 200))

def parse_date_fr(text):
text = text.strip()
m = re.search(r"(\d{1,2}).(\d{2}).(\d{2,4})", text)
if m:
d, mo, y = m.group(1), m.group(2), m.group(3)
if len(y) == 2:
y = "20" + y
try:
return datetime(int(y), int(mo), int(d), tzinfo=timezone.utc).strftime(
"%Y-%m-%d %H:%M:%S"
)
except ValueError:
pass
return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

# –– IT-Connect ––

def scrape_itconnect():
print("\n[IT-Connect]")
soup = get("https://www.it-connect.fr/actualites/actu-securite/")
if not soup:
return []

```
links = []
for a in soup.select("article h2 a, article h3 a, .entry-title a"):
    href = a.get("href", "")
    if href and href not in links:
        links.append(href)
    if len(links) >= MAX_ARTICLES:
        break

articles = []
for url in links:
    print("  -> " + url)
    art = scrape_itconnect_article(url)
    if art:
        articles.append(art)
    time.sleep(DELAY)

print("  OK: " + str(len(articles)) + " articles")
return articles
```

def scrape_itconnect_article(url):
soup = get(url)
if not soup:
return None

```
title_tag = soup.select_one("h1.entry-title, h1")
title = title_tag.get_text(strip=True) if title_tag else ""
if not title:
    return None

image_url = ""
hero = soup.select_one(".post-thumbnail img, .featured-image img, article img")
if hero:
    image_url = hero.get("data-src") or hero.get("data-lazy-src") or hero.get("src", "")
    if image_url.startswith("data:"):
        image_url = ""

author = ""
for sel in [".author a", ".entry-author a", '[rel="author"]']:
    a = soup.select_one(sel)
    if a:
        author = a.get_text(strip=True)
        break

date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
for sel in ["time[datetime]", ".entry-date", ".published"]:
    t = soup.select_one(sel)
    if t:
        dt = t.get("datetime") or t.get_text(strip=True)
        if dt:
            date_str = dt[:19].replace("T", " ")
        break

content_tag = soup.select_one("div.entry-content, div.post-content, article .content")
content_html = clean_html(content_tag)

excerpt = ""
meta = soup.find("meta", {"name": "description"})
if meta:
    excerpt = meta.get("content", "")
if not excerpt and content_tag:
    excerpt = content_tag.get_text(" ", strip=True)[:250]

tags = [a.get_text(strip=True) for a in soup.select(".tags a, .post-tags a, .entry-tags a")]

return {
    "hash":      make_hash(url),
    "cat_slug":  "cyber",
    "source":    "IT-Connect",
    "title":     title,
    "link":      url,
    "image_url": image_url,
    "excerpt":   excerpt,
    "author":    author or "IT-Connect",
    "date":      date_str,
    "tags":      tags,
    "content":   content_html,
    "read_time": read_time(content_html),
}
```

# –– INCYBER ––

def scrape_incyber():
print("\n[INCYBER]")
soup = get("https://incyber.org/categorie/cyber/")
if not soup:
return []

```
links = []
for a in soup.select("a[href*='/article/']"):
    href = a.get("href", "")
    if href and href not in links:
        links.append(href)
    if len(links) >= MAX_ARTICLES:
        break

articles = []
for url in links:
    print("  -> " + url)
    art = scrape_incyber_article(url)
    if art:
        articles.append(art)
    time.sleep(DELAY)

print("  OK: " + str(len(articles)) + " articles")
return articles
```

def scrape_incyber_article(url):
soup = get(url)
if not soup:
return None

```
title_tag = soup.select_one("h1")
title = title_tag.get_text(strip=True) if title_tag else ""
if not title:
    return None

image_url = ""
for img in soup.select("img[src*='wp-content/uploads']"):
    src = img.get("src", "")
    if src and "885x690" not in src and "150x150" not in src:
        image_url = src
        break
if not image_url:
    hero = soup.select_one("img[src*='wp-content/uploads']")
    if hero:
        image_url = hero.get("src", "")

author = ""
a_tag = soup.select_one("a[href*='/contributeur/']")
if a_tag:
    author = a_tag.get_text(strip=True)

date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
date_match = re.search(r"\d{2}\.\d{2}\.\d{2,4}", soup.get_text())
if date_match:
    date_str = parse_date_fr(date_match.group())

content_tag = soup.select_one(
    ".entry-content, .article-content, .post-content, article .content"
)
if not content_tag:
    h1 = soup.select_one("h1")
    if h1:
        paragraphs = []
        for sib in h1.find_all_next(["p", "h2", "h3", "ul", "ol", "blockquote"]):
            if sib.find_parent(class_=re.compile(r"nav|menu|sidebar|footer|related")):
                continue
            paragraphs.append(str(sib))
            if len(paragraphs) > 60:
                break
        fake = BeautifulSoup("<div>" + "".join(paragraphs) + "</div>", "lxml")
        content_tag = fake.find("div")

content_html = clean_html(content_tag)

excerpt = ""
meta = soup.find("meta", {"name": "description"})
if meta:
    excerpt = meta.get("content", "")
if not excerpt and content_tag:
    excerpt = content_tag.get_text(" ", strip=True)[:250]

tags = [
    a.get_text(strip=True)
    for a in soup.select("a[href*='/categorie/']")
    if a.get_text(strip=True) not in ("Cyber +", "")
]
tags = list(dict.fromkeys(tags))[:5]

return {
    "hash":      make_hash(url),
    "cat_slug":  "cyber",
    "source":    "INCYBER",
    "title":     title,
    "link":      url,
    "image_url": image_url,
    "excerpt":   excerpt,
    "author":    author or "INCYBER",
    "date":      date_str,
    "tags":      tags,
    "content":   content_html,
    "read_time": read_time(content_html),
}
```

# –– MAIN ––

def main():
print("Scraper Blogz Des Fous Crazy")
print("=" * 40)

```
all_articles = []
all_articles += scrape_itconnect()
all_articles += scrape_incyber()

seen = set()
unique = []
for a in all_articles:
    if a["hash"] not in seen:
        seen.add(a["hash"])
        unique.append(a)

output = {
    "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
    "count":        len(unique),
    "articles":     unique,
}

with open("articles.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print("\nDone: " + str(len(unique)) + " articles sauvegardes")
itc = sum(1 for a in unique if a["source"] == "IT-Connect")
inc = sum(1 for a in unique if a["source"] == "INCYBER")
print("  IT-Connect : " + str(itc))
print("  INCYBER    : " + str(inc))
```

if **name** == "**main**":
main()