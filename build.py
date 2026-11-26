#!/usr/bin/env python3
"""Build the NEKpress site from catalog.toml, using only the standard library.

    python3 build.py           check the catalog, write _site/, then check what was written
    python3 build.py --check   check the catalog only (writes nothing)

The output check confirms that every shown title's links are on its pages, that no hidden
title's ASIN or DOI appears anywhere, that every relative link resolves, and that any page
mentioning AP(R) carries the College Board disclaimer. Any problem stops the build with an
error, so GitHub never publishes a broken site.
"""

import datetime
import html
import pathlib
import re
import shutil
import sys

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # Python 3.10: pip install tomli
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        sys.exit("build.py needs Python 3.11 or newer (or `pip install tomli` on 3.10).")

ROOT = pathlib.Path(__file__).resolve().parent
CATALOG = ROOT / "catalog.toml"
ASSETS = ROOT / "assets"
OUT = ROOT / "_site"

SHOW = {"featured", "listed", "hidden"}
KINDS = {"annotated", "guide"}
BOOK_KEYS = {
    "id", "title", "subtitle", "shelf", "group", "show", "kindle", "paperback", "doi",
    "version_doi", "doi_label", "supplements", "link", "code", "number", "author", "play",
    "kind", "blurb", "status", "disclaimer",
}
SHELF_KEYS = {"slug", "title", "menu", "intro", "groups", "layout", "free_list"}
SITE_KEYS = {"title", "author", "url", "amazon", "tagline", "intro", "email", "github",
             "youtube", "zenodo", "orcid"}
SITE_REQUIRED = {"title", "author", "url", "amazon"}
RESERVED_SLUGS = {"assets", "index", "404"}

ASIN_RE = re.compile(r"^B0[0-9A-Z]{8}$")
DOI_RE = re.compile(r"^10\.5281/zenodo\.[0-9]+$")
ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class Problems:
    def __init__(self):
        self.errors, self.notes = [], []

    def error(self, msg):
        self.errors.append(msg)

    def note(self, msg):
        self.notes.append(msg)


# ------------------------------------------------------------------ catalog checks

def load_catalog():
    with CATALOG.open("rb") as fh:
        try:
            return tomllib.load(fh)
        except tomllib.TOMLDecodeError as err:
            sys.exit(f"ERROR: catalog.toml is not valid TOML: {err}. Nothing was built.")


def check_catalog(cat):
    p = Problems()
    site = cat.get("site", {})
    shelves = cat.get("shelf", [])
    books = cat.get("book", [])

    for key in sorted(set(site) - SITE_KEYS):
        p.error(f"[site]: unknown key '{key}'")
    for key in sorted(SITE_REQUIRED - set(site)):
        p.error(f"[site]: missing '{key}'")
    if not str(site.get("url", "")).startswith("https://"):
        p.error("[site] url must start with https://")
    if str(site.get("url", "")).endswith("/"):
        p.error("[site] url must not end with /")

    slugs = {}
    for i, sh in enumerate(shelves):
        where = f"shelf #{i + 1} ({sh.get('slug', '?')})"
        for key in sorted(set(sh) - SHELF_KEYS):
            p.error(f"{where}: unknown key '{key}'")
        slug = sh.get("slug", "")
        if not ID_RE.match(slug):
            p.error(f"{where}: slug must be lowercase letters, digits and hyphens")
        if slug in RESERVED_SLUGS:
            p.error(f"{where}: slug '{slug}' is reserved")
        if slug in slugs:
            p.error(f"{where}: duplicate slug")
        for key in ("title", "menu"):
            if not sh.get(key):
                p.error(f"{where}: missing '{key}'")
        if sh.get("layout") not in (None, "plays"):
            p.error(f"{where}: layout must be \"plays\" or left out")
        slugs[slug] = sh

    ids, asins, dois, plays = {}, {}, {}, {}
    for i, b in enumerate(books):
        bid = b.get("id", "")
        where = f"book '{bid or '#' + str(i + 1)}'"
        for key in sorted(set(b) - BOOK_KEYS):
            p.error(f"{where}: unknown key '{key}' (a typo?)")
        if not ID_RE.match(bid):
            p.error(f"{where}: id must be lowercase letters, digits and hyphens")
        if bid in ids:
            p.error(f"{where}: duplicate id")
        ids[bid] = b
        if not b.get("title"):
            p.error(f"{where}: missing title")
        shelf = slugs.get(b.get("shelf"))
        if shelf is None:
            p.error(f"{where}: shelf '{b.get('shelf')}' is not one of the [[shelf]] slugs")
        show = b.get("show", "listed")
        if show not in SHOW:
            p.error(f"{where}: show must be featured, listed or hidden")
        group = b.get("group")
        if group is not None and shelf is not None and group not in shelf.get("groups", []):
            p.error(f"{where}: group '{group}' is not in shelf '{shelf['slug']}' groups")
        for fmt in ("kindle", "paperback"):
            asin = b.get(fmt)
            if asin is None:
                continue
            if not ASIN_RE.match(asin):
                p.error(f"{where}: {fmt} ASIN '{asin}' is not 10 characters starting B0")
            if asin in asins:
                p.error(f"{where}: {fmt} ASIN {asin} is also used by '{asins[asin]}'")
            asins[asin] = bid
        doi = b.get("doi")
        if doi is not None:
            if not DOI_RE.match(doi):
                p.error(f"{where}: DOI '{doi}' should look like 10.5281/zenodo.12345")
            if doi in dois:
                p.error(f"{where}: DOI {doi} is also used by '{dois[doi]}'")
            dois[doi] = bid
            if b.get("version_doi"):
                p.note(f"{bid}: {doi} is a version DOI; swap in the concept DOI when you have it")
        elif b.get("version_doi") or b.get("doi_label"):
            p.error(f"{where}: version_doi/doi_label without a doi")
        if show != "hidden" and not (b.get("kindle") or b.get("paperback") or doi):
            p.error(f"{where}: shown, but has no Kindle, paperback or DOI to link to")
        if b.get("supplements") and not b.get("link"):
            p.error(f"{where}: 'supplements' needs a 'link' (the text on the other book's card)")
        if b.get("link") and not b.get("supplements"):
            p.error(f"{where}: 'link' without 'supplements'")
        if b.get("supplements") and not doi:
            p.error(f"{where}: 'supplements' needs a doi to link to")
        code = b.get("code")
        if code is not None and not code.startswith("https://"):
            p.error(f"{where}: code must be an https:// link")
        if (b.get("play") is None) != (b.get("kind") is None):
            p.error(f"{where}: play and kind go together")
        if b.get("play") is not None:
            if b["kind"] not in KINDS:
                p.error(f"{where}: kind must be annotated or guide")
            if shelf is not None and shelf.get("layout") != "plays":
                p.error(f"{where}: play is only used on a shelf with layout = \"plays\"")
            key = (b["play"], b["kind"])
            if key in plays:
                p.error(f"{where}: {b['play']} already has a {b['kind']} entry ('{plays[key]}')")
            plays[key] = bid
        if shelf is not None and shelf.get("layout") == "plays" and show != "hidden":
            if b.get("play") is None and not group:
                p.error(f"{where}: on the plays shelf, a non-play title needs a group")

    for b in books:
        target = b.get("supplements")
        if target and target not in ids:
            p.error(f"book '{b.get('id')}': supplements '{target}', which is not an id")
        elif target and b.get("show", "listed") != "hidden" and ids[target].get("show", "listed") == "hidden":
            p.note(f"{b['id']}: supplements hidden '{target}', so it shows only in lists")
    return p


# ------------------------------------------------------------------ helpers

def esc(text):
    return html.escape(str(text), quote=True)


def visible(b):
    return b.get("show", "listed") != "hidden"


def full_title(b):
    return f"{b['title']}: {b['subtitle']}" if b.get("subtitle") else b["title"]


def amazon(site, asin):
    return f"https://{site['amazon']}/dp/{asin}"


def doi_url(doi):
    return f"https://doi.org/{doi}"


def link_li(href, text, cls, label):
    return f'<li><a class="{cls}" href="{esc(href)}" aria-label="{esc(label)}">{esc(text)}</a></li>'


class Catalog:
    def __init__(self, cat):
        self.site = cat["site"]
        self.shelves = cat["shelf"]
        self.books = cat["book"]
        self.by_id = {b["id"]: b for b in self.books}
        self.extras = {}  # book id -> free records that supplement it (shown ones only)
        for b in self.books:
            if b.get("supplements") and visible(b):
                self.extras.setdefault(b["supplements"], []).append(b)

    def shown_on(self, slug):
        return [b for b in self.books if b["shelf"] == slug and visible(b)]

    def live_shelves(self):
        return [s for s in self.shelves if self.shown_on(s["slug"])]


# ------------------------------------------------------------------ rendering

def book_links(cat, b):
    """The list of links for one title, in a fixed order."""
    site, name = cat.site, full_title(b)
    items = []
    if b.get("kindle"):
        items.append(link_li(amazon(site, b["kindle"]), "Kindle", "buy", f"{name}, Kindle edition on Amazon"))
    if b.get("paperback"):
        items.append(link_li(amazon(site, b["paperback"]), "Paperback", "buy", f"{name}, paperback on Amazon"))
    if b.get("doi"):
        if b.get("kindle") or b.get("paperback"):
            text = b.get("doi_label", "Free edition")
        else:
            text = "Read free on Zenodo"
        items.append(link_li(doi_url(b["doi"]), text, "free", f"{name}, {text.lower()} on Zenodo"))
    for extra in cat.extras.get(b["id"], []):
        items.append(link_li(doi_url(extra["doi"]), extra["link"], "free",
                             f"{full_title(extra)}, free on Zenodo"))
    if b.get("code"):
        items.append(link_li(b["code"], "Companion code", "code", f"{name}, companion code on GitHub"))
    return f'<ul class="links">{"".join(items)}</ul>'


def card(cat, b, heading="h3"):
    parts = [f'<article class="book" id="{esc(b["id"])}">']
    if b.get("number"):
        parts.append(f'<p class="label">{esc(b["number"])}</p>')
    parts.append(f'<{heading} class="title">{esc(b["title"])}</{heading}>')
    if b.get("subtitle"):
        parts.append(f'<p class="subtitle">{esc(b["subtitle"])}</p>')
    if b.get("author"):
        parts.append(f'<p class="author">by {esc(b["author"])}</p>')
    if b.get("blurb"):
        parts.append(f'<p class="blurb">{esc(b["blurb"])}</p>')
    parts.append(book_links(cat, b))
    parts.append("</article>")
    return "".join(parts)


def cards(cat, books, heading="h3"):
    return '<div class="cards">' + "".join(card(cat, b, heading) for b in books) + "</div>"


def plays_table(cat, books):
    rows, order = {}, []
    for b in books:
        if b["play"] not in rows:
            rows[b["play"]] = {}
            order.append(b["play"])
        rows[b["play"]][b["kind"]] = b
    out = ['<div class="table-wrap"><table class="plays"><thead><tr><th scope="col">Play</th>'
           '<th scope="col">Annotated edition</th>'
           '<th scope="col">Dictionary, pronunciation and study guide</th></tr></thead><tbody>']
    for play in order:
        out.append(f'<tr><th scope="row">{esc(play)}</th>')
        for kind in ("annotated", "guide"):
            b = rows[play].get(kind)
            out.append(f"<td>{book_links(cat, b)}</td>" if b else '<td class="none" aria-label="Not available">–</td>')
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def shelf_body(cat, shelf):
    books = cat.shown_on(shelf["slug"])
    sell = [b for b in books if b.get("kindle") or b.get("paperback")]
    out = [f'<h1>{esc(shelf["title"])}</h1>']
    if shelf.get("intro"):
        out.append(f'<p class="lead">{esc(shelf["intro"])}</p>')

    groups = shelf.get("groups", [])
    ungrouped = [b for b in sell if not b.get("group")]
    if ungrouped:
        out.append(cards(cat, ungrouped, "h2" if not groups else "h3"))
    for g in groups:
        members = [b for b in sell if b.get("group") == g]
        if not members:
            continue
        out.append(f'<section class="group"><h2>{esc(g)}</h2>')
        if shelf.get("layout") == "plays":
            in_play = [b for b in members if b.get("play")]
            others = [b for b in members if not b.get("play")]
            if in_play:
                out.append(plays_table(cat, in_play))
            if others:
                out.append(cards(cat, others))
        else:
            out.append(cards(cat, members))
        out.append("</section>")

    if shelf.get("free_list"):
        free = [b for b in books if b.get("doi")]
        if free:
            out.append('<section class="group"><h2>Free on Zenodo</h2>'
                       '<p>Open-access editions, quick-start guides and workbooks, each with a DOI.</p>'
                       '<ul class="free-list">')
            for b in free:
                tail = ""
                if b.get("kindle") or b.get("paperback"):
                    label = b.get("doi_label", "Free edition").lower()
                    tail = f' <span class="note">({esc(label)}; also on Amazon)</span>'
                out.append(f'<li><a href="{esc(doi_url(b["doi"]))}">{esc(full_title(b))}</a>{tail}</li>')
            out.append("</ul></section>")
    return "".join(out)


def home_body(cat):
    site = cat.site
    out = [f'<h1>{esc(site.get("tagline", site["title"]))}</h1>']
    if site.get("intro"):
        out.append(f'<p class="lead">{esc(site["intro"])}</p>')
    featured = [b for b in cat.books if b.get("show") == "featured"]
    if featured:
        out.append('<section class="group"><h2>Start here</h2>' + cards(cat, featured) + "</section>")
    out.append('<section class="group"><h2>Shelves</h2><div class="cards shelves">')
    for s in cat.live_shelves():
        books = cat.shown_on(s["slug"])
        on_amazon = sum(1 for b in books if b.get("kindle") or b.get("paperback"))
        free = sum(1 for b in books if b.get("doi"))
        counts = []
        if on_amazon:
            counts.append(f"{on_amazon} on Amazon")
        if free:
            counts.append(f"{free} free on Zenodo")
        out.append(f'<a class="shelf" href="{esc(s["slug"])}/"><span class="title">{esc(s["title"])}</span>'
                   f'<span class="intro">{esc(s.get("intro", ""))}</span>'
                   f'<span class="count">{esc(" · ".join(counts))}</span></a>')
    out.append("</div></section>")
    return "".join(out)


def disclaimers_for(cat, books):
    seen = []
    for b in books:
        for x in [b] + cat.extras.get(b["id"], []):
            d = x.get("disclaimer")
            if d and d not in seen:
                seen.append(d)
    return seen


def page(cat, *, title, body, depth, current, disclaimers, canonical, prefix=None):
    """depth: how many folders below the site root the page lives; prefix overrides it
    (the 404 page is served at any path, so it uses root-absolute links)."""
    site = cat.site
    up = prefix if prefix is not None else "../" * depth
    nav = []
    for s in cat.live_shelves():
        attr = ' aria-current="page"' if s["slug"] == current else ""
        nav.append(f'<li><a href="{up}{esc(s["slug"])}/"{attr}>{esc(s["menu"])}</a></li>')
    contact = []
    if site.get("email"):
        contact.append(f'<li><a href="mailto:{esc(site["email"])}">{esc(site["email"])}</a></li>')
    for key, text in (("github", "GitHub"), ("youtube", "YouTube"), ("zenodo", "Zenodo")):
        if site.get(key):
            contact.append(f'<li><a href="{esc(site[key])}">{text}</a></li>')
    if site.get("orcid"):
        contact.append(f'<li><a href="https://orcid.org/{esc(site["orcid"])}">ORCID {esc(site["orcid"])}</a></li>')
    notes = "".join(f'<p class="disclaimer">{esc(d)}</p>' for d in disclaimers)
    year = datetime.date.today().year
    full = title if title == site["title"] else f"{title} | {site['title']}"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(full)}</title>
<meta name="description" content="{esc(site.get('intro', ''))}">
<link rel="canonical" href="{esc(canonical)}">
<link rel="stylesheet" href="{up}assets/style.css">
<link rel="icon" href="{up}assets/favicon.svg" type="image/svg+xml">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site">
<div class="wrap">
<a class="brand" href="{up or './'}">{esc(site['title'])}</a>
<nav aria-label="Shelves"><ul>{"".join(nav)}</ul></nav>
</div>
</header>
<main id="main" class="wrap">
{body}
</main>
<footer class="site">
<div class="wrap">
<ul class="contact">{"".join(contact)}</ul>
<p>© {year} {esc(site['author'])}. Books are sold on Amazon; free editions are on Zenodo.</p>
{notes}
</div>
</footer>
</body>
</html>
"""


def build(cat):
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "assets").mkdir(parents=True)
    for f in ASSETS.iterdir():
        if f.is_file():
            shutil.copy2(f, OUT / "assets" / f.name)
    site = cat.site
    pages = {}

    featured = [b for b in cat.books if b.get("show") == "featured"]
    pages["index.html"] = page(cat, title=site["title"], body=home_body(cat), depth=0, current=None,
                               disclaimers=disclaimers_for(cat, featured), canonical=site["url"] + "/")
    for s in cat.live_shelves():
        books = cat.shown_on(s["slug"])
        pages[f"{s['slug']}/index.html"] = page(
            cat, title=s["title"], body=shelf_body(cat, s), depth=1, current=s["slug"],
            disclaimers=disclaimers_for(cat, books), canonical=f"{site['url']}/{s['slug']}/")
    pages["404.html"] = page(
        cat, title="Page not found",
        body='<h1>Page not found</h1><p class="lead">That page is not here. '
             f'<a href="{esc(site["url"])}/">Go to the home page</a>.</p>',
        depth=0, current=None, disclaimers=[], canonical=site["url"] + "/", prefix="/")

    for rel, text in pages.items():
        path = OUT / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    urls = [site["url"] + "/"] + [f"{site['url']}/{s['slug']}/" for s in cat.live_shelves()]
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{esc(u)}</loc></url>\n" for u in urls)
        + "</urlset>\n", encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {site['url']}/sitemap.xml\n",
                                    encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    return pages


# ------------------------------------------------------------------ output checks

HREF_RE = re.compile(r'href="([^"]+)"')
TAG_RE = re.compile(r"<[^>]+>")


def check_output(cat, pages):
    p = Problems()
    text_all = {rel: (OUT / rel).read_text(encoding="utf-8") for rel in pages}
    blob = "".join(text_all.values())
    counts = {"amazon": 0, "doi": 0}

    for b in cat.books:
        targets = [f"/dp/{b[f]}" for f in ("kindle", "paperback") if b.get(f)]
        if b.get("doi"):
            targets.append(doi_url(b["doi"]))
        if not visible(b):
            for t in targets:
                if t in blob:
                    p.error(f"hidden '{b['id']}' leaked: {t} appears in the site")
            continue
        homes = [f"{b['shelf']}/index.html"]
        if b.get("show") == "featured":
            homes.append("index.html")
        for rel in homes:
            for t in targets:
                if t not in text_all.get(rel, ""):
                    p.error(f"'{b['id']}': {t} is missing from {rel}")
        if b.get("supplements") and visible(cat.by_id[b["supplements"]]):
            rel = f"{cat.by_id[b['supplements']]['shelf']}/index.html"
            if f'{doi_url(b["doi"])}" aria-label' not in text_all[rel]:
                p.error(f"'{b['id']}' is not on the card of '{b['supplements']}'")

    disclaimers = {b["disclaimer"] for b in cat.books if b.get("disclaimer")}
    for rel, text in text_all.items():
        counts["amazon"] += text.count(f"https://{cat.site['amazon']}/dp/")
        counts["doi"] += text.count("https://doi.org/")
        words = html.unescape(TAG_RE.sub(" ", text))
        if re.search(r"\bAP\b(?!®)", words):
            p.error(f"{rel}: 'AP' without ® (the College Board's marks are never abbreviated or bare)")
        if "AP®" in words and not any(d in words for d in disclaimers):
            p.error(f"{rel}: mentions AP® but has no College Board disclaimer")
        for href in HREF_RE.findall(text):
            if href.startswith(("https://", "mailto:", "#")):
                continue
            if href.startswith("http://"):
                p.error(f"{rel}: insecure link {href}")
                continue
            if href.startswith("/"):
                target = OUT / href.lstrip("/")
            else:
                target = (OUT / rel).parent / href
            if href.endswith("/") or href in ("./", ""):
                target = target / "index.html"
            if not target.resolve().exists():
                p.error(f"{rel}: link '{href}' does not resolve")
    return p, counts


# ------------------------------------------------------------------ main

def report(p):
    for n in p.notes:
        print(f"note: {n}")
    for e in p.errors:
        print(f"ERROR: {e}", file=sys.stderr)
    return not p.errors


def main(argv):
    raw = load_catalog()
    if not report(check_catalog(raw)):
        sys.exit("catalog.toml has problems; nothing was built.")
    cat = Catalog(raw)
    shown = sum(1 for b in cat.books if visible(b))
    summary = (f"titles={len(cat.books)} shown={shown} hidden={len(cat.books) - shown} "
               f"featured={sum(1 for b in cat.books if b.get('show') == 'featured')}")
    if "--check" in argv:
        print(f"CATALOG_OK {summary}")
        return
    pages = build(cat)
    problems, counts = check_output(cat, pages)
    if not report(problems):
        sys.exit("The built site failed its checks; do not publish it.")
    print(f"SITE_OK {summary} pages={len(pages)} amazon_links={counts['amazon']} doi_links={counts['doi']}")
    print(f"Built {OUT.relative_to(ROOT)}/. Preview: python3 -m http.server -d _site 8000")


if __name__ == "__main__":
    main(sys.argv[1:])
