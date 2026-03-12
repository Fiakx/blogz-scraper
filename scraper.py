#!/usr/bin/env python3
"""
scraper.py v3 — Scrape IT-Connect et génère articles.json
Le fichier est ensuite commité sur GitHub.
InfinityFree viendra le lire lui-même via fetch.php
"""

import os
import re
import json
import hashlib
import requests
from datetime import datetime
from bs4 import BeautifulSoup

SOURCES = [
    {
        "url":      "https://www.it-connect.fr/actualites/actu-securite/",
        "cat_slug": "cyber",
        "selectors": {
            "articles": "article",
            "title":    "h2 a, h3 a, .entry-title a",
            "link":     "h2 a, h3 a, .entry-title a",
            "image":    "img",
            "excerpt":  "p",
            "author":   ".author a, .byline a, [class*='author'] a",
            "date":     "time, [datetime]",
            "tags":     "[rel='tag'], .tags-links a",
        }
    },
    # Ajoute d'autres sources ici :
    # {
    #     "url":      "https://www.it-connect.fr/actualites/actu-logiciel-os/",
    #     "cat_slug": "tech",
    #     "selectors": { ... même structure ... }
    # },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
}

# ============================================================
#  UTILITAIRES
# ============================================================
def article_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:32]

def estimate_read_time(text: str) -> int:
    return max(1, round(len(text.split()) / 250))

def parse_date(raw: str) -> str:
    raw = (raw or "").strip()
    try:
        return datetime.fromisoformat(raw).strftime("%Y-%m-%d %H:%M:%S")
    except: pass
    try:
        return datetime.strptime(raw, "%d/%m/%Y").strftime("%Y-%m-%d %H:%M:%S")
    except: pass
    mois = {"janvier":"01","février":"02","mars":"03","avril":"04",
            "mai":"05","juin":"06","juillet":"07","août":"08",
            "septembre":"09","octobre":"10","novembre":"11","décembre":"12"}
    m = re.match(r"(\d{1,2})\s+(\w+)\s+(\d{4})", raw.lower())
    if m:
        d, mn, y = m.groups()
        return f"{y}-{mois.get(mn,'01')}-{d.zfill(2)} 00:00:00"
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_image(el) -> str:
    if not el:
        return ""
    for attr in ["data-src", "data-lazy-src", "src"]:
        val = el.get(attr, "")
        if val and not val.startswith("data:"):
            return val
    for attr in ["data-srcset", "srcset"]:
        srcset = el.get(attr, "")
        if srcset:
            parts = [p.strip().split()[0] for p in srcset.split(",") if p.strip()]
            if parts:
                return parts[-1]
    return ""

# ============================================================
#  SCRAPER — PAGE LISTE
# ============================================================
def scrape_list(source: dict) -> list:
    print(f"\n🔍  {source['url']}")
    try:
        r = requests.get(source["url"], headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print(f"  ❌ Requête échouée : {e}")
        return []

    soup   = BeautifulSoup(r.text, "html.parser")
    sel    = source["selectors"]
    blocks = soup.select(sel["articles"])
    print(f"  → {len(blocks)} blocs trouvés")

    results = []
    for block in blocks:
        try:
            title_el = block.select_one(sel["title"])
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            link  = title_el.get("href", "").strip()
            if not title or not link:
                continue

            image_url  = get_image(block.select_one(sel["image"]))
            excerpt_el = block.select_one(sel["excerpt"])
            excerpt    = excerpt_el.get_text(strip=True) if excerpt_el else ""
            author_el  = block.select_one(sel["author"])
            author     = author_el.get_text(strip=True) if author_el else ""
            date_el    = block.select_one(sel["date"])
            date_raw   = (date_el.get("datetime") or date_el.get_text(strip=True)) if date_el else ""
            tags       = list(set([t.get_text(strip=True) for t in block.select(sel["tags"])]))

            results.append({
                "hash":      article_hash(link),
                "cat_slug":  source["cat_slug"],
                "title":     title,
                "link":      link,
                "image_url": image_url,
                "excerpt":   excerpt,
                "author":    author,
                "date":      parse_date(date_raw),
                "tags":      tags,
            })
            print(f"  ✅ {title[:70]}")
        except Exception as e:
            print(f"  ⚠️  Bloc ignoré : {e}")

    return results

# ============================================================
#  SCRAPER — CONTENU COMPLET DE L'ARTICLE
# ============================================================
def scrape_content(url: str) -> dict:
    if not url:
        return {"content": "", "read_time": 1}
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print(f"    ⚠️  Contenu inaccessible : {e}")
        return {"content": "", "read_time": 1}

    soup    = BeautifulSoup(r.text, "html.parser")
    content = (
        soup.select_one("div.entry-content") or
        soup.select_one("div.post-content")  or
        soup.select_one("article .content")
    )
    if not content:
        return {"content": "", "read_time": 1}

    # Nettoyer les éléments parasites
    for el in content.select(
        "script,style,.sharedaddy,.jp-relatedposts,.wpcnt,"
        ".adsbygoogle,nav,.navigation,.post-navigation,"
        ".comments-area,#comments,.sidebar,aside,.widget,"
        "[class*='banner'],[class*='advert'],[id*='advert'],"
        ".itc-newsletter,.itc-pub"
    ):
        el.decompose()

    # Corriger les images lazy-load
    for img in content.select("img"):
        real = get_image(img)
        if real:
            img["src"] = real
        else:
            img.decompose()

    html      = str(content)
    read_time = estimate_read_time(content.get_text(separator=" ", strip=True))
    return {"content": html, "read_time": read_time}

# ============================================================
#  MAIN
# ============================================================
def main():
    print("=" * 60)
    print(f"🚀 Scraper v3 — {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 60)

    all_articles = []

    for source in SOURCES:
        articles = scrape_list(source)
        for art in articles:
            print(f"\n  📄 Récupération contenu : {art['title'][:60]}")
            full             = scrape_content(art["link"])
            art["content"]   = full["content"]
            art["read_time"] = full["read_time"]
            all_articles.append(art)

    # Écrire le fichier JSON
    output = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "count":        len(all_articles),
        "articles":     all_articles,
    }

    with open("articles.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"📦 articles.json généré — {len(all_articles)} articles")
    print("=" * 60)

if __name__ == "__main__":
    main()
