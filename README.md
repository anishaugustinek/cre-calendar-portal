# CRE Calendar Portal — GitHub Pages + automatic updates

This project creates a public website with an Excel download of entries collected from the RCI CRE Calendar webpage. GitHub Actions runs the scraper every Sunday at 09:00 India Standard Time (03:30 UTC), and can also be run manually.

## Important
- This is an independent convenience resource, not an official RCI website.
- The scraper collects publicly displayed webpage table entries. It is not an official RCI export.
- The source site's HTML, pagination, access policy or availability may change. The scraper may then need maintenance.
- Check the Actions log and verify the record count after the first run. Do not assume every entry was collected merely because the workflow succeeded.
- Verify programme dates, venue, eligibility, CRE points and registration status with RCI or the organiser.
- A failed scrape does not replace the last committed workbook.

## 1. Create a GitHub repository
1. Sign in to GitHub and create a **public** repository, e.g. `cre-calendar-portal`.
2. Extract this ZIP on your computer.
3. Open Command Prompt in the extracted folder and run (replace YOUR-USERNAME):

```bash
git init
git add .
git commit -m "Initial CRE calendar website"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/cre-calendar-portal.git
git push -u origin main
```

Complete GitHub authentication if prompted.

## 2. Enable GitHub Pages
1. Repository → **Settings → Pages**.
2. Under Build and deployment choose **Deploy from a branch**.
3. Select branch `main`, folder `/docs`, then Save.
4. Your website URL will be `https://YOUR-USERNAME.github.io/cre-calendar-portal/`.

## 3. Enable and test automatic updates
1. Open the repository's **Actions** tab and enable workflows if prompted.
2. Select **Update RCI CRE Calendar**.
3. Click **Run workflow**.
4. Inspect the **Scrape RCI CRE Calendar** step. Check its `Page N` messages and final unique record count.
5. Confirm the run completes and commits the updated Excel workbook.
6. Open the Pages website and test the download link.

The scheduled update runs Sundays at 09:00 IST. GitHub scheduled runs may be delayed. Use **Run workflow** to update on demand.

## 4. Local test on Windows
Install Python 3.10+ and Chrome, then run from the project folder:

```cmd
python -m pip install -r requirements.txt
python scraper.py
```

To display Chrome during a local test:

```cmd
set HEADLESS=0
python scraper.py
```

## 5. Change the schedule
Edit `.github/workflows/update-calendar.yml`. Cron uses UTC:
- Daily 09:00 IST: `30 3 * * *`
- Monday 09:00 IST: `30 3 * * 1`
- Sunday 09:00 IST: `30 3 * * 0`

## 6. Troubleshooting
- **Only 10 rows:** pagination selectors may have changed. Check the action logs and inspect `docs/downloads/calendar_page_backup.html`; adjust `next_control()` in `scraper.py`.
- **Action fails:** inspect the failed step in Actions. The source site may be unavailable or its layout may have changed.
- **Website not refreshed:** wait for Pages deployment, then hard-refresh the browser.
- **No scheduled run:** run manually and check repository Actions settings. GitHub may disable scheduled workflows in inactive repositories.
- **Access restrictions/CAPTCHA:** do not attempt to bypass login, CAPTCHA or other access controls.

The public download URL remains stable because the workflow replaces `docs/downloads/RCI_CRE_Calendar.xlsx` on each successful run.
