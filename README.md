# nekpress.ca

The source of the NEKpress site. It lives in the `nicholaskarlson.github.io` repository, and GitHub
publishes it at https://nicholaskarlson.github.io/ (and at https://nekpress.ca once the domain is
switched; see `DNS-SWITCH.md`).

There is no WordPress, database or theme. `catalog.toml` lists every title. `build.py` (Python
standard library only) checks it, writes the pages into `_site/`, checks what it wrote, and GitHub
publishes the result.

## How the links are handled

- **One entry per title.** All 56 titles on the KDP Bookshelf (November 26, 2026) and the 8 free
  records that exist only on Zenodo are in `catalog.toml`, 64 entries in all.
- **Every title has a shelf and a visibility.** `show = "featured"` puts it on its shelf page and
  the home page. `"listed"` (the default) puts it on its shelf page. `"hidden"` keeps it in the
  catalog as a record but leaves it off the site entirely, and the build checks that none of its
  ASINs or DOIs leak onto any page. Hidden now: the two Douay–Rheims titles, the two Ubuntu drafts,
  and the 2016 and 2023 drafts. A shelf with nothing shown gets no page and no menu entry, which is
  why there is no Religious Studies page.
- **Only identifiers are stored.** The catalog keeps ASINs and DOIs, not URLs. Every Amazon link is
  `https://<amazon>/dp/<ASIN>`, and `amazon` is set once in `[site]`. KDP gives a book the same ASIN
  in every Amazon store, so changing `www.amazon.com` to `www.amazon.ca` moves the whole site to
  the other store. Every Zenodo link is `https://doi.org/<DOI>`.
- **Free records attach to their book.** A quick-start guide, workbook or teacher's guide has
  `supplements = "<book id>"`. It then shows as a green link on that book's card and in the "Free
  on Zenodo" list, but its DOI is written only once.
- **Shakespeare is one row per play.** Each annotated edition and its dictionary, pronunciation and
  study guide share a row, and the plays are grouped as in the First Folio.
- **No prices.** They differ from store to store and they change, so the pages link to Amazon and
  let Amazon show the price.

## Everyday changes

| To... | Do this in `catalog.toml` |
| --- | --- |
| add a book | copy a similar `[[book]]` entry, then change its id, titles and ASINs |
| hide or show a title | set `show = "hidden"`, or delete the line to list it again |
| feature a title on the home page | set `show = "featured"` |
| publish a draft | add its ASINs and delete `show = "hidden"` |
| change the Amazon store | edit `amazon` in `[site]` |
| add a shelf | add a `[[shelf]]` and point books at its slug |

Then run `python3 build.py`, and commit and push. On GitHub you can also edit `catalog.toml` in the
browser and commit. The workflow builds and checks the site and publishes it. If a check fails,
nothing is published and the old site stays up.

**Four DOIs are still version DOIs** (`version_doi = true`), so each time they link to that one
version: *Establishing Facts*, the Causal open edition, and the two jamovi workbooks. Each record's
page on Zenodo shows the concept DOI under "Cite all versions". Paste it in and delete the
`version_doi` line. The build prints a reminder until all four are done.

## Build and preview on your computer

```bash
python3 build.py                      # check, build _site/, check the result
python3 -m http.server -d _site 8000  # then open http://localhost:8000
python3 build.py --check              # check catalog.toml only
```

`build.py` needs Python 3.11 or newer for `tomllib`. Ubuntu 22.04 has 3.10, so there you'd run
`pip install tomli` first, or let GitHub do the building. A good build ends with a line like this:

```
SITE_OK titles=64 shown=58 hidden=6 featured=2 pages=7 amazon_links=75 doi_links=23
```

## What the checks catch

- **In `catalog.toml`:**
  - an unknown field, which is usually a typo such as `paperbak`;
  - a malformed ASIN or DOI, or one used twice;
  - a shelf or group that doesn't exist;
  - a shown title with nothing to link to;
  - a `supplements` that points nowhere;
  - two study guides for the same play.
- **In the built site:**
  - a shown title whose links are missing from its page;
  - a hidden title's ASIN or DOI on any page;
  - a relative link that leads nowhere;
  - an `http://` link;
  - "AP" without ®;
  - a page that mentions AP® without the College Board disclaimer.

## Publishing for the first time

1. On GitHub, create a **public**, empty repository named `nicholaskarlson.github.io`.
2. Put these files in it, then commit and push to `main`. Include the hidden `.github/` folder and
   `.gitignore`.
3. Go to the repository's **Settings → Pages → Build and deployment** and set **Source** to
   **GitHub Actions**. Then open the **Actions** tab and re-run the "Site" workflow if it ran before
   you made that change.
4. Open https://nicholaskarlson.github.io/. Also check that
   https://nicholaskarlson.github.io/longitudinal/ still loads. Project sites are not affected.
5. When you're happy with the site, follow `DNS-SWITCH.md`.

A shelf's slug becomes a folder at the root of the site (`/statistics/`), so never give a shelf the
name of a repository that has its own Pages site, such as `longitudinal`.
