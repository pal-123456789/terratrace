# Deployment — `terratrace.fit` on GitHub Pages

The website is a plain static directory tree at `site/`. There is **no build step** and **no rewrite
table**: GitHub Pages resolves `site/index.html` at `/`, and `site/<name>/index.html` at `/<name>/`,
which is exactly the shape the site already has. That is why this migration needed no HTML changes —
only links normalised to the canonical trailing-slash form so each route answers without a redirect.

| route | file | what it is |
|---|---|---|
| `/` | `site/index.html` | the landing page: the question, the three acts, the result |
| `/study/` | `site/study/index.html` | the v3 result rendered as a study |
| `/viewer/` | `site/viewer/index.html` | the raw study viewer |
| `/CNAME` | `site/CNAME` | marks the custom domain for branch-based deploys |
| `/.nojekyll` | `site/.nojekyll` | stops Jekyll processing the tree |

## 1. What is already in the repository

- `.github/workflows/pages.yml` — publishes `site/` to Pages on every push to `main` that touches it
  (and on manual dispatch). Uses the official `configure-pages` / `upload-pages-artifact` /
  `deploy-pages` actions; the versions are the current majors from GitHub's own
  `pages/static.yml` starter, not from memory.
- `site/CNAME` — `terratrace.fit`.
- `site/.nojekyll` — an empty file. **Do not delete it**: without it Pages runs Jekyll and silently
  drops any path starting with `_`.
- `site/vercel.json` — kept because it describes the identical routes for Vercel. The site is
  deployable, unmodified, on either host; nothing depends on Vercel.

## 2. Two settings only a repository owner can change

I cannot do these; both are a few clicks. Do them **in this order**.

**a. Point Pages at the workflow.** Repository → **Settings** → **Pages** → *Build and deployment* →
**Source: GitHub Actions**. (Without this step the workflow runs and then fails at the deploy step
with "Pages is not enabled".)

**b. Set the custom domain.** Same screen → *Custom domain* → `terratrace.fit` → **Save**.
Note that with an Actions-based deploy **the `site/CNAME` file is ignored** — GitHub's own docs say
so; the Settings field is what actually configures the domain. The file is kept so a branch-based
deploy would still work if you ever switch.

After the certificate is provisioned, tick **Enforce HTTPS**. The checkbox is greyed out until then.
It is usually minutes; GitHub allows up to 24 hours.

## 3. DNS records at Porkbun

Porkbun → **Domain Management** → `terratrace.fit` → **DNS Records**. Values below are from GitHub's
official Pages documentation, which I read rather than recalled.

Four `A` records on the apex (host left blank / `@`):

| Type | Host | Answer |
|---|---|---|
| A | (blank) | `185.199.108.153` |
| A | (blank) | `185.199.109.153` |
| A | (blank) | `185.199.110.153` |
| A | (blank) | `185.199.111.153` |

Four `AAAA` records on the apex (optional but recommended — IPv6):

| Type | Host | Answer |
|---|---|---|
| AAAA | (blank) | `2606:50c0:8000::153` |
| AAAA | (blank) | `2606:50c0:8001::153` |
| AAAA | (blank) | `2606:50c0:8002::153` |
| AAAA | (blank) | `2606:50c0:8003::153` |

One `CNAME` for the www subdomain, so `www.terratrace.fit` redirects to the canonical host:

| Type | Host | Answer |
|---|---|---|
| CNAME | `www` | `pal-123456789.github.io` |

**Remove anything else on the apex first.** Porkbun parks new domains with its own `A`/`ALIAS`
records; leaving them alongside GitHub's produces an unreliable, intermittently-resolving site. If
Porkbun's **URL Forwarding** is switched on, turn it off — it competes with the `CNAME`.

Do not create a `CNAME` on the apex. Apex domains cannot have one (the apex has no name to alias);
that is what the `A`/`AAAA` records are for.

## 4. Verify

DNS first — this can take from a minute to a few hours to propagate:

```bash
dig +short terratrace.fit          # expect the four 185.199.108-111.153 addresses
dig +short www.terratrace.fit      # expect pal-123456789.github.io, then GitHub's IPs
```

Then the site, once **Settings → Pages** shows a green "Your site is live" and the `Deploy site`
workflow has a successful run:

```bash
curl -sI https://terratrace.fit | head -1                 # HTTP/2 200
curl -sI https://terratrace.fit/study/ | head -1          # HTTP/2 200
curl -sI https://terratrace.fit/viewer/ | head -1         # HTTP/2 200
```

All three routes are also checked mechanically in the repository, independent of the deploy:
`terratrace/scripts/doc_consistency_check.py` resolves every internal `href` and every `#fragment`
against the files as they exist, so a route that would 404 fails the build before it ever reaches
Pages. That guard is what makes this migration safe to do blind.

## 5. If something goes wrong

| symptom | cause |
|---|---|
| Workflow fails at "Deploy to GitHub Pages" | Pages source is not set to **GitHub Actions** (§2a) |
| Site loads on `pal-123456789.github.io` but not on the domain | DNS not propagated, or apex parking records still present (§3) |
| `www` works, apex does not (or the reverse) | only one of the two record groups was added |
| Certificate never issues | a `CAA` record on the domain is blocking Let's Encrypt; GitHub's docs name `letsencrypt.org` — add a `CAA` record allowing it |
| A path 404s that exists in the repo | a leading-underscore path and `.nojekyll` is missing |
| 404 page looks like GitHub's, not the site's | there is no custom `site/404.html`; add one if desired |

## 6. Status

| item | status |
|---|---|
| Site restructured for Pages | **NOT NEEDED** — already a directory tree; links normalised |
| Workflow, `CNAME`, `.nojekyll` | **IMPLEMENTED, NOT YET VERIFIED LIVE** — cannot be verified from here (no network) |
| Repository Pages settings | **NOT STARTED** — owner action, §2 |
| Porkbun DNS records | **NOT STARTED** — owner action, §3 |
| `www` redirect, HTTPS enforcement | **NOT STARTED** — follows §2 and §3 |
