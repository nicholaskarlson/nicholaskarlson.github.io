# Moving nekpress.ca from WordPress to this site (Namecheap)

Keep WordPress running until the last step. Do the steps in this order.

## Before you start

- The new site is live and correct at https://nicholaskarlson.github.io/.
- Save anything from WordPress you want to keep. The current site is one page, so that means its
  text and the site icon (`wp-content/uploads/2026/03/cropped-wp-site-icon-270x270.jpg`).
- **Email.** The MX records for nekpress.ca are Namecheap's free email forwarding
  (`eforward1` to `eforward5.registrar-servers.com`), not the WordPress hosting. Leave
  **Advanced DNS → Mail Settings** exactly as it is, and email keeps working.

## 1. Verify the domain with GitHub (prevents takeover)

1. On GitHub, open your **profile** Settings, not the repository's. Then go to
   **Pages → Add a domain**, enter `nekpress.ca`, and copy the TXT record that GitHub shows.
2. In Namecheap, go to **Domain List → nekpress.ca → Manage → Advanced DNS → Add new record**:
   - Type: **TXT Record**
   - Host: the part of GitHub's name before `.nekpress.ca`, something like
     `_github-pages-challenge-nicholaskarlson`
   - Value: the code that GitHub shows
3. Back on GitHub, click **Verify**. DNS can take a while, so if it fails, try again later.

## 2. Add the domain to the repository

In `nicholaskarlson.github.io`, go to **Settings → Pages → Custom domain**, enter `nekpress.ca`,
and click **Save**. The site is published by GitHub Actions, so no CNAME file is needed. The setting
lives in Settings.

## 3. Change the records in Namecheap (Advanced DNS)

**Delete** the old `@` and `www` records that point at the WordPress host: A records, a CNAME, or a
URL Redirect.

**Add** these records:

| Type | Host | Value |
| --- | --- | --- |
| A Record | @ | 185.199.108.153 |
| A Record | @ | 185.199.109.153 |
| A Record | @ | 185.199.110.153 |
| A Record | @ | 185.199.111.153 |
| AAAA Record (optional) | @ | 2606:50c0:8000::153 |
| AAAA Record (optional) | @ | 2606:50c0:8001::153 |
| AAAA Record (optional) | @ | 2606:50c0:8002::153 |
| AAAA Record (optional) | @ | 2606:50c0:8003::153 |
| CNAME Record | www | nicholaskarlson.github.io. |

Don't add a wildcard (`*`) record. Leave the TXT verification record and the Mail Settings alone.

## 4. Wait, then turn on HTTPS

DNS can take up to 24 hours. Once GitHub's DNS check passes on the Pages settings page and the
certificate has been issued, tick **Enforce HTTPS**. The box stays greyed out until then.

## 5. Check everything

- https://nekpress.ca and https://www.nekpress.ca show the new site, and www redirects to the
  bare domain.
- http://nekpress.ca redirects to https.
- https://nicholaskarlson.github.io/ redirects to https://nekpress.ca/.
- https://nekpress.ca/longitudinal/ loads, and so does the old
  https://nicholaskarlson.github.io/longitudinal/, which now redirects there.
- An email sent to your nekpress.ca forwarding address still arrives.

## 6. Then, and only then

- Cancel the WordPress hosting plan in Namecheap (Hosting List or Apps), along with any paid SSL
  certificate. GitHub's certificate is free.
- Turn on **auto-renew** for nekpress.ca. Once the domain is the site's address, every
  `nicholaskarlson.github.io` link redirects to it. If the domain ever lapsed, those links, including
  any printed in books, would lead nowhere. In books, keep citing DOIs and github.com repository
  URLs, which don't depend on the domain.
