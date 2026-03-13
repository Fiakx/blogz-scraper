#!/usr/bin/env python3
“””
Blogz Des Fous Crazy – Scraper multi-sources
Sources :

- IT-Connect  : https://www.it-connect.fr/actualites/actu-securite/  -> cat: cyber
- INCYBER     : https://incyber.org/categorie/cyber/                 -> cat: cyber

Sortie : articles.json (commité par GitHub Actions)
“””

import hashlib
import json
import re
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

# ── Config ──────────────────────────────────────────────────────────────────

HEADERS = {
“User-Agent”: (
“Mozilla/5.0 (Windows NT 10.0; Win64; x64) “
“AppleWebKit/537.36 (KHTML, like Gecko) “
“Chrome/122.0.0.0 Safari/537.36”
)
}
TIMEOUT      = 15
DELAY        = 1.2   # secondes entre requêtes
MAX_ARTICLES = 15    # par source

# ── Helpers ──────────────────────────────────────────────────────────────────

def get(url: str) -> BeautifulSoup | None:
try:
r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
r.raise_for_status()
return BeautifulSoup(r.text, “lxml”)
except Exception as e:
print(f”  ⚠️  GET failed: {url} – {e}”)
return None

def make_hash(url: str) -> str:
return hashlib.sha256(url.encode()).hexdigest()

def clean_html(tag) -> str:
“”“Supprime scripts, styles et lazy-load depuis un tag BS4.”””
if not tag:
return “”
for el in tag.find_all([“script”, “style”, “noscript”, “iframe”]):
el.decompose()
# Lazy-load -> src réel
for img in tag.find_all(“img”):
src = img.get(“data-src”) or img.get(“data-lazy-src”) or img.get(“src”, “”)
if src and not src.startswith(“data:”):
img[“src”] = src
else:
img.decompose()
return str(tag)

def read_time(html: str) -> int:
words = len(re.sub(r”<[^>]+>”, “ “, html).split())
return max(1, round(words / 200))

def parse_date_fr(text: str) -> str:
“”“Convertit ‘10.03.26’ ou ‘10.03.2026’ en datetime ISO.”””
text = text.strip()
# Format incyber : DD.MM.YY ou DD.MM.YYYY
m = re.search(r”(\d{1,2}).(\d{2}).(\d{2,4})”, text)
if m:
d, mo, y = m.group(1), m.group(2), m.group(3)
if len(y) == 2:
y = “20” + y
try:
return datetime(int(y), int(mo), int(d), tzinfo=timezone.utc).strftime(
“%Y-%m-%d %H:%M:%S”
)
except ValueError:
pass
return datetime.now(timezone.utc).strftime(”%Y-%m-%d %H:%M:%S”)

# ════════════════════════════════════════════════════════════════════════════

# SOURCE 1 – IT-Connect

# ════════════════════════════════════════════════════════════════════════════

def scrape_itconnect() -> list[dict]:
print(”\n IT-Connect”)
LIST_URL = “https://www.it-connect.fr/actualites/actu-securite/”
soup = get(LIST_URL)
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
    print(f"  -> {url}")
    art = scrape_itconnect_article(url)
    if art:
        articles.append(art)
    time.sleep(DELAY)

print(f"  ✅ {len(articles)} articles récupérés")
return articles
```

def scrape_itconnect_article(url: str) -> dict | None:
soup = get(url)
if not soup:
return None

```
title_tag = soup.select_one("h1.entry-title, h1")
title = title_tag.get_text(strip=True) if title_tag else ""
if not title:
    return None

# Image principale
image_url = ""
hero = soup.select_one(".post-thumbnail img, .featured-image img, article img")
if hero:
    image_url = (
        hero.get("data-src") or hero.get("data-lazy-src") or hero.get("src", "")
    )
    if image_url.startswith("data:"):
        image_url = ""

# Auteur
author = ""
for sel in [".author a", ".entry-author a", '[rel="author"]']:
    a = soup.select_one(sel)
    if a:
        author = a.get_text(strip=True)
        break

# Date
date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
for sel in ["time[datetime]", ".entry-date", ".published"]:
    t = soup.select_one(sel)
    if t:
        dt = t.get("datetime") or t.get_text(strip=True)
        if dt:
            date_str = dt[:19].replace("T", " ")
        break

# Contenu
content_tag = soup.select_one("div.entry-content, div.post-content, article .content")
content_html = clean_html(content_tag)

# Excerpt
excerpt = ""
meta = soup.find("meta", {"name": "description"})
if meta:
    excerpt = meta.get("content", "")
if not excerpt and content_tag:
    excerpt = content_tag.get_text(" ", strip=True)[:250]

# Tags
tags = [
    a.get_text(strip=True)
    for a in soup.select(".tags a, .post-tags a, .entry-tags a")
]

return {
    "hash":       make_hash(url),
    "cat_slug":   "cyber",
    "source":     "IT-Connect",
    "title":      title,
    "link":       url,
    "image_url":  image_url,
    "excerpt":    excerpt,
    "author":     author or "IT-Connect",
    "date":       date_str,
    "tags":       tags,
    "content":    content_html,
    "read_time":  read_time(content_html),
}
```

# ════════════════════════════════════════════════════════════════════════════

# SOURCE 2 – INCYBER

# ════════════════════════════════════════════════════════════════════════════

def scrape_incyber() -> list[dict]:
print(”\n INCYBER”)
LIST_URL = “https://incyber.org/categorie/cyber/”
soup = get(LIST_URL)
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
    print(f"  -> {url}")
    art = scrape_incyber_article(url)
    if art:
        articles.append(art)
    time.sleep(DELAY)

print(f"  ✅ {len(articles)} articles récupérés")
return articles
```

def scrape_incyber_article(url: str) -> dict | None:
soup = get(url)
if not soup:
return None

```
# Titre
title_tag = soup.select_one("h1")
title = title_tag.get_text(strip=True) if title_tag else ""
if not title:
    return None

# Image principale (première grande image de l'article)
image_url = ""
for img in soup.select("img[src*='wp-content/uploads']"):
    src = img.get("src", "")
    # Préférer les images larges (pas les thumbnails 885x690 de nav)
    if src and "885x690" not in src and "150x150" not in src:
        image_url = src
        break
if not image_url:
    # fallback : première image wp-content
    hero = soup.select_one("img[src*='wp-content/uploads']")
    if hero:
        image_url = hero.get("src", "")

# Auteur
author = ""
a_tag = soup.select_one("a[href*='/contributeur/']")
if a_tag:
    author = a_tag.get_text(strip=True)

# Date : chercher le pattern DD.MM.YY dans le texte de la page
date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
date_match = re.search(r"\d{2}\.\d{2}\.\d{2,4}", soup.get_text())
if date_match:
    date_str = parse_date_fr(date_match.group())

# Contenu : le bloc principal après le h1
# Sur incyber, le contenu est dans .entry-content ou .article-content
content_tag = soup.select_one(
    ".entry-content, .article-content, .post-content, article .content"
)
# Fallback : prendre les <p> qui suivent le h1
if not content_tag:
    h1 = soup.select_one("h1")
    if h1:
        # Créer un div synthétique avec tous les p/h2/h3 suivants
        paragraphs = []
        for sib in h1.find_all_next(["p", "h2", "h3", "ul", "ol", "blockquote"]):
            # Stopper sur les sections de navigation
            if sib.find_parent(class_=re.compile(r"nav|menu|sidebar|footer|related")):
                continue
            paragraphs.append(str(sib))
            if len(paragraphs) > 60:
                break
        fake = BeautifulSoup("<div>" + "".join(paragraphs) + "</div>", "lxml")
        content_tag = fake.find("div")

content_html = clean_html(content_tag)

# Excerpt (meta description)
excerpt = ""
meta = soup.find("meta", {"name": "description"})
if meta:
    excerpt = meta.get("content", "")
if not excerpt and content_tag:
    excerpt = content_tag.get_text(" ", strip=True)[:250]

# Tags (catégories incyber)
tags = [
    a.get_text(strip=True)
    for a in soup.select("a[href*='/categorie/']")
    if a.get_text(strip=True) not in ("Cyber +", "")
]
tags = list(dict.fromkeys(tags))[:5]  # dédoublonner, max 5

return {
    "hash":       make_hash(url),
    "cat_slug":   "cyber",
    "source":     "INCYBER",
    "title":      title,
    "link":       url,
    "image_url":  image_url,
    "excerpt":    excerpt,
    "author":     author or "INCYBER",
    "date":       date_str,
    "tags":       tags,
    "content":    content_html,
    "read_time":  read_time(content_html),
}
```

# ════════════════════════════════════════════════════════════════════════════

# MAIN

# ════════════════════════════════════════════════════════════════════════════

def main():
print(“ Scraper Blogz Des Fous Crazy”)
print(”=” * 50)

```
all_articles = []
all_articles += scrape_itconnect()
all_articles += scrape_incyber()

# Dédoublonner par hash (au cas où)
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

print(f"\n✅ {len(unique)} articles sauvegardés dans articles.json")
print(f"   IT-Connect : {sum(1 for a in unique if a['source'] == 'IT-Connect')}")
print(f"   INCYBER    : {sum(1 for a in unique if a['source'] == 'INCYBER')}")
```

if **name** == “**main**”:
main()