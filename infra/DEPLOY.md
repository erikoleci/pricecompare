# Deploying PriceCompare

## Before you deploy anything

**No merchant is live yet, and that's intentional.** Every merchant is
registered with `is_supported=false` until a human opens robots.txt and the
ToS and approves it via the admin UI (`/admin`, spec section 3). Deploying
this app does not start crawling anything - the crawler container in
`infra/docker-compose.yml` has no default command for exactly this reason.

**These Dockerfiles are written but not build-tested.** The sandbox this
project was built in blocks `repo.maven.apache.org` (confirmed directly -
see the README's "Live verification session" notes) and can't reach Docker
Hub either, so neither `mvn compile` nor `docker build` could be run here.
Everything else that *could* be tested was: all SQL (including the
Flyway-mirrored migrations these Dockerfiles rely on), the crawler's 16
Python tests, and the frontend's production build (`vue-tsc -b && vite
build`, zero errors). Run `docker compose build` once on your own machine
before trusting a deploy - if `mvn package` fails, the error will be a real
compile problem, not this same sandbox limitation.

## Option A: Docker Compose (any VPS)

Simplest if you already have a server (Hetzner, DigitalOcean, a home
server, etc.) with Docker installed.

```bash
git clone https://github.com/erikoleci/pricecompare.git
cd pricecompare/infra
cp .env.example .env        # edit DB_PASSWORD at minimum
docker compose build
docker compose up -d postgres redis backend frontend
```

- Backend: `http://<server>:8080` (Swagger UI at `/api/docs`)
- Frontend: `http://<server>:5173`
- Flyway runs automatically on backend startup - `V1` through `V9`
  (schema, seed data, search, the 15 registered Albanian merchants) apply
  with no manual step.
- Put nginx or Caddy in front for a real domain + HTTPS (Let's Encrypt).
  A minimal reverse-proxy config isn't included here - add one once you
  know the real domain.
- The crawler container stays off unless you explicitly need it:
  `docker compose --profile crawler run crawler pytest` to run its test
  suite, or `... run crawler python3 -m tools.merchant_audit --domain X`
  to audit a merchant. There's no `docker compose up` service for
  continuous crawling yet - see the README's Phase 2 status for why
  (no merchant has passed compliance review, and no scheduler entry
  point has been written yet either).

## Option B: Render (same platform as your 365sim project)

Render doesn't read `docker-compose.yml` directly - each service is
created separately, pointing at the same repo with a different
root/Dockerfile path.

1. **Postgres**: New "PostgreSQL" instance on Render. Copy its internal
   connection string.
2. **Redis**: New "Key Value" (Render's managed Redis) instance. Copy its
   internal URL.
3. **Backend**: New "Web Service" → connect the `pricecompare` repo →
   root directory `backend`, Docker runtime (it'll pick up
   `backend/Dockerfile` automatically). Environment variables:
   - `DB_URL` = `jdbc:postgresql://<postgres-internal-host>:5432/<db-name>`
   - `DB_USER`, `DB_PASSWORD` = from the Postgres instance
   - `REDIS_URL` = the Redis instance's internal URL
   - `CORS_ORIGINS` = your frontend's Render URL, once you have it
   - Render sets `PORT` itself - `application.properties` already reads
     `${PORT:8080}`, so nothing else to configure there.
4. **Frontend**: New "Static Site" (simpler and cheaper than running the
   nginx Docker image for a plain SPA) → root directory `frontend`,
   build command `npm ci && npm run build`, publish directory `dist`.
   Add a rewrite rule `/* → /index.html` (Render's static site settings)
   for Vue Router's history mode. Then add an env var or a small
   `_redirects`/proxy rule so `/api/*` reaches the backend service's URL -
   Render static sites don't proxy by default the way the Docker/nginx
   path does, so either set `VITE_API_BASE` to the backend's full URL and
   update `frontend/src/api/client.ts`'s `baseURL` to use it, or use
   Render's static-site rewrite rules to proxy `/api/*` to the backend
   service URL.
5. Once the backend is live, open `https://<backend>/api/docs` to confirm
   Flyway applied all 9 migrations and the API responds, then open
   `https://<frontend>/admin` to do the actual robots.txt/ToS review for
   whichever merchants you want to approve first.

## What's still missing before this is production-ready

- No auth/user accounts, so `/admin` is open to anyone who reaches the
  URL - put it behind a reverse-proxy basic-auth rule or a VPN at minimum
  until real auth exists.
- No reverse-proxy/HTTPS config included (Option A) - needed before any
  public traffic.
- No CI - `docker compose build` (or Render's build) is the only thing
  that will actually catch a Maven/npm compile error right now.

## Fixing "Failed to fetch dynamically imported module" / 404 on old chunk hashes

If you deployed and see console errors like:

```
GET https://<your-site>.onrender.com/assets/VCheckboxBtn-BsrGIdV-.js 404 (Not Found)
TypeError: Failed to fetch dynamically imported module: .../SearchView-DB-LsWLY.js
```

This is **not a broken build** - `npm run build` produced a working
`dist/` (verified: 16/16 crawler tests + a clean `vue-tsc -b && vite build`
every time this repo's frontend has changed). The cause is caching:

- Vite content-hashes every JS/CSS chunk filename. Any file whose content
  changed gets a **new** filename on the next build (e.g.
  `VCheckboxBtn-BwJzXNGk.js` this build vs. `VCheckboxBtn-BsrGIdV-.js` last
  build).
- `index.html` is what references those hashed filenames. If a browser (or
  Render's CDN) has an `index.html` cached from *before* your latest
  deploy, it still points at the *previous* build's filenames - which
  genuinely no longer exist once the new build replaces them. That's the
  literal 404 you're seeing, and it'll keep happening on every redeploy
  until `index.html` itself stops being cached.

**Fix — CORRECTION: this originally claimed `_headers`/`_redirects` work
automatically on Render the way they do on Netlify/Cloudflare Pages. That
was wrong.** Render Static Sites do **not** read a `_headers` or
`_redirects` file from the publish directory at all - both are
Netlify/Cloudflare-specific conventions. Render's own docs confirm this:
redirect/rewrite rules and custom headers for static sites are configured
**only** via the Dashboard (see
[render.com/docs/redirects-rewrites](https://render.com/docs/redirects-rewrites)
and
[render.com/docs/static-site-headers](https://render.com/docs/static-site-headers)
- a `_headers`-file feature request for Render has been open, unimplemented,
since 2019). `frontend/public/_headers` and `_redirects` are harmless to
leave in the repo (Vite still copies them into `dist/`, and they're the
correct mechanism for the Docker/nginx path - `nginx.conf` reads its own
equivalent rules directly, not these files), but **on a Render Static
Site specifically, configure both by hand**:

- **Redirects/Rewrites tab** → add a rule: Source `/*`, Destination
  `/index.html`, Action **Rewrite** (not Redirect - a Redirect would change
  the URL in the browser, breaking Vue Router's history mode). This alone
  fixes a 404 on any route besides `/` (e.g. `/admin`, `/search`,
  `/products/<id>`).
- **Headers tab** → add two rules:
  - Path `/index.html`, Name `Cache-Control`, Value
    `no-cache, no-store, must-revalidate`
  - Path `/assets/*`, Name `Cache-Control`, Value
    `public, max-age=31536000, immutable`

  This is optional but recommended - it's what actually fixes the
  stale-chunk-404-after-redeploy problem this section is about, on Render
  specifically (the `_headers` file does not do this on Render, contrary to
  what this section previously said).

There's also a small client-side safety net now (`router/index.ts` +
`main.ts`): if a tab was already open right when a new deploy went live, it
will hit this same stale-reference error once - the app now catches that
specific error and does **one** automatic page reload to recover, instead
of leaving the user on a broken white screen. This is a fallback for that
narrow timing window, not a substitute for the cache-header fix above.

If it's a Docker/nginx deployment (Option A) instead of a Static Site,
`frontend/nginx.conf` got the equivalent fix directly (separate `location`
blocks for `/index.html` vs `/assets/`) - just rebuild the image.
