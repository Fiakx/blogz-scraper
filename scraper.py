#!/usr/bin/env python3
"""
scraper.py — Scraper IT-Connect → Blogz Des Fous Crazy
Récupère les articles et les envoie à l'API PHP.
"""

import os
import re
import json
import hashlib
import requests
from datetime import datetime
from bs4 import BeautifulSoup

# ============================================================
#  CONFIG — lues depuis les secrets GitHub Actions
# ============================================================
API_URL    = os.environ["BLOG_API_URL"]    # https://tonsite.infinityfree.net/api.php
API_SECRET = os.environ["BLOG_API_SECRET"] # clé secrète de ton config.php

SOURCES = [
    {
        "url":      "https://www.it-connect.fr/actualites/actu-securite/",
        "cat_slug": "cyber",
        "selectors": {
            "articles": "article.post",
            "title":    "h2.entry-title a, h3.entry-title a",
            "link":     "h2.entry-title a, h3.entry-title a",
            "image":    ".post-thumbnail img, figure img",
            "excerpt":  ".entry-summary p",
            "author":   ".author a, .byline a",
            "date":     "time.entry-date, .entry-date",
            "tags":     ".tags-links a, .post-tags a",
        }
    },
    # Ajoute facilement d'autres sources :
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
def slugify(text: str) -> str:
    text = text.lower().strip()
    for src, dst in [
        ("àáâãäå","a"),("èéêë","e"),("ìíîï","i"),
        ("òóôõö","o"),("ùúûü","u"),("ç","c"),("ñ","n")
    ]:
        for c in src:
            text = text.replace(c, dst)
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    return text[:180]

def article_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:32]

def estimate_read_time(text: str) -> int:
    return max(1, round(len(text.split()) / 250))

def parse_date(raw: str) -> str:
    raw = (raw or "").strip()
    # Format ISO
    try:
        return datetime.fromisoformat(raw).strftime("%Y-%m-%d %H:%M:%S")
    except: pass
    # dd/mm/yyyy
    try:
        return datetime.strptime(raw, "%d/%m/%Y").strftime("%Y-%m-%d %H:%M:%S")
    except: pass
    # "12 mars 2026"
    mois = {"janvier":"01","février":"02","mars":"03","avril":"04",
            "mai":"05","juin":"06","juillet":"07","août":"08",
            "septembre":"09","octobre":"10","novembre":"11","décembre":"12"}
    m = re.match(r"(\d{1,2})\s+(\w+)\s+(\d{4})", raw.lower())
    if m:
        d, mn, y = m.groups()
        return f"{y}-{mois.get(mn,'01')}-{d.zfill(2)} 00:00:00"
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_image(el):
    """Extrait la vraie URL d'image même avec le lazy-load."""
    if not el:
        return ""
    for attr in ["data-src", "data-lazy-src", "src"]:
        val = el.get(attr, "")
        if val and not val.startswith("data:"):
            return val
    # Tenter srcset
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
        print(f" Requête échouée : {e}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    sel  = source["selectors"]
    blocks = soup.select(sel["articles"])
    print(f"  → {len(blocks)} articles trouvés")

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
            tags       = [t.get_text(strip=True) for t in block.select(sel["tags"])]

            results.append({
                "title":    title,
                "link":     link,
                "image_url": image_url,
                "excerpt":  excerpt,
                "author":   author,
                "date_raw": date_raw,
                "tags":     tags,
                "cat_slug": source["cat_slug"],
            })
        except Exception as e:
            print(f"  Bloc ignoré : {e}")

    return results

# ============================================================
#  SCRAPER — ARTICLE COMPLET
# ============================================================
def scrape_article(url: str) -> dict:
    if not url:
        return {"content": "", "read_time": 1}
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print(f"  Article inaccessible : {e}")
        return {"content": "", "read_time": 1}

    soup = BeautifulSoup(r.text, "html.parser")

    content = (
        soup.select_one("div.entry-content") or
        soup.select_one("div.post-content")  or
        soup.select_one("article .content")
    )
    if not content:
        return {"content": "", "read_time": 1}

    # Supprimer les éléments parasites
    for el in content.select(
        "script,style,.sharedaddy,.jp-relatedposts,.wpcnt,"
        ".adsbygoogle,nav,.navigation,.post-navigation,"
        ".comments-area,#comments,.sidebar,aside,.widget,"
        "[class*='banner'],[class*='advert'],[id*='advert'],"
        ".itc-newsletter,.itc-pub,.wp-block-group.is-style-outline"
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
#  ENVOI À L'API PHP
# ============================================================
def push(art: dict) -> str:
    """Retourne 'added', 'skipped' ou 'error'."""
    try:
        r = requests.post(API_URL, data={
            "action":        "scraper_push",
            "secret":        API_SECRET,
            "cat_slug":      art["cat_slug"],
            "titre":         art["title"],
            "slug":          slugify(art["title"]) + "-" + article_hash(art["link"])[:6],
            "resume":        art["excerpt"],
            "contenu":       art["content"],
            "image_url":     art["image_url"],
            "tags_json":     json.dumps(art["tags"], ensure_ascii=False),
            "auteur":        art["author"],
            "temps_lecture": art["read_time"],
            "publie_le":     art["date_pub"],
            "source_url":    art["link"],
            "source_hash":   article_hash(art["link"]),
        }, timeout=20)
        r.raise_for_status()
        d = r.json()
        if d.get("ok"):
            return "skipped" if d.get("skipped") else "added"
        print(f" API : {d.get('error','?')}")
        return "error"
    except Exception as e:
        print(f" Envoi : {e}")
        return "error"

# ============================================================
#  MAIN
# ============================================================
def main():
    print("=" * 60)
    print(f" Scraper — {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 60)

    added = skipped = errors = 0

    for source in SOURCES:
        articles = scrape_list(source)

        for art in articles:
            print(f"\n {art['title'][:70]}")
            full            = scrape_article(art["link"])
            art["content"]  = full["content"]
            art["read_time"] = full["read_time"]
            art["date_pub"]  = parse_date(art["date_raw"])

            result = push(art)
            if result == "added":
                print(" Ajouté !")
                added += 1
            elif result == "skipped":
                print("    ⏭  Déjà en BDD")
                skipped += 1
            else:
                errors += 1

    print("\n" + "=" * 60)
    print(f" Ajoutés  : {added}")
    print(f"⏭  Ignorés  : {skipped}")
    print(f" Erreurs  : {errors}")
    print("=" * 60)

if __name__ == "__main__":
    main()