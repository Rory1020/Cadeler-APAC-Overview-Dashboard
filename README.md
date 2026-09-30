# APAC Sector Overview Dashboard (Cadeler)
Static site. News refreshes daily via GitHub Actions; no server needed.

## Deploy (10 minutes, free)
1. Create a GitHub repo, upload all files in this folder (keep `.github/`).
2. Settings > Pages > Source: "Deploy from a branch", branch `main`, folder `/ (root)`.
3. Actions tab > "Update dashboard news" > Run workflow (first refresh). It then runs daily at 06:00 Taipei.
4. Site URL: https://<user>.github.io/<repo>/  (private/company hosting: use GitHub Enterprise Pages, Netlify, or any static host).

## Update
- News (industry / competitors / Cadeler): automatic, edit queries in `scripts/update_news.py`.
- Tenders & auction timeline: edit `data/tenders.js`.
- Vessel positions & 12-month projects: typed in the page, saved in your browser.
