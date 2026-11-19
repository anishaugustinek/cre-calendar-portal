import os, json, time, hashlib
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, WebDriverException

URL = "https://rciregistration.nic.in/rehabcouncil/CreCalendarnew.jsp"
OUT = Path("docs/downloads")
XLSX = OUT / "RCI_CRE_Calendar.xlsx"
META = OUT / "metadata.json"
HEADLESS = os.getenv("HEADLESS", "1") == "1"
MAX_PAGES = int(os.getenv("MAX_PAGES", "100"))

def make_driver():
    o = webdriver.ChromeOptions()
    if HEADLESS: o.add_argument("--headless=new")
    for arg in ["--no-sandbox", "--disable-dev-shm-usage", "--window-size=1920,1080"]:
        o.add_argument(arg)
    o.add_argument("--disable-blink-features=AutomationControlled")
    return webdriver.Chrome(options=o)

def main_table(d):
    candidates = []
    for t in d.find_elements(By.TAG_NAME, "table"):
        try:
            if t.is_displayed():
                rows = t.find_elements(By.CSS_SELECTOR, "tbody tr") or t.find_elements(By.CSS_SELECTOR, "tr")
                if rows: candidates.append((len(rows), t))
        except StaleElementReferenceException:
            pass
    if not candidates: raise RuntimeError("No visible HTML table found.")
    return sorted(candidates, key=lambda x: x[0], reverse=True)[0][1]

def read_rows(d):
    t = main_table(d)
    rows = t.find_elements(By.CSS_SELECTOR, "tbody tr") or t.find_elements(By.CSS_SELECTOR, "tr")
    data = []
    for r in rows:
        cells = r.find_elements(By.CSS_SELECTOR, "th,td")
        vals = [c.text.strip() for c in cells]
        if vals and any(vals): data.append(vals)
    return t, data

def fingerprint(rows):
    return hashlib.sha256(json.dumps(rows, ensure_ascii=False).encode()).hexdigest()

def select_largest_page_size(d):
    for el in d.find_elements(By.TAG_NAME, "select"):
        try:
            if not el.is_displayed(): continue
            s = Select(el)
            opts = []
            for op in s.options:
                val, label = (op.get_attribute("value") or "").strip(), op.text.strip()
                if val == "-1" or "all" in label.lower(): opts.append((10**9, val, label))
                else:
                    digits = "".join(c for c in (val or label) if c.isdigit())
                    if digits: opts.append((int(digits), val, label))
            if opts:
                _, val, label = max(opts)
                if val: s.select_by_value(val)
                else: s.select_by_visible_text(label)
                time.sleep(2)
                print("Selected page size:", label or val)
                return
        except Exception:
            continue

def next_control(d):
    selectors = ["a.next", "button.next", "a[aria-label='Next']", "button[aria-label='Next']",
                 ".paginate_button.next", "li.next a", "li.page-item.next a", "a[rel='next']"]
    found = []
    for sel in selectors:
        try: found += d.find_elements(By.CSS_SELECTOR, sel)
        except WebDriverException: pass
    try:
        found += d.find_elements(By.XPATH,
            "//*[self::a or self::button][normalize-space(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'))='next']")
    except WebDriverException: pass
    for e in found:
        try:
            if not e.is_displayed(): continue
            cls = (e.get_attribute("class") or "").lower()
            parent = (e.find_element(By.XPATH, "..").get_attribute("class") or "").lower()
            if "disabled" in cls or "disabled" in parent: continue
            if e.get_attribute("aria-disabled") == "true" or e.get_attribute("disabled") is not None: continue
            return e
        except Exception: pass
    return None

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    d = make_driver()
    collected, headers, pages = [], [], 0
    try:
        print("Opening", URL)
        d.get(URL)
        wait = WebDriverWait(d, 50)
        wait.until(lambda x: x.execute_script("return document.readyState") == "complete")
        wait.until(lambda x: main_table(x) is not None)
        time.sleep(3)
        select_largest_page_size(d)
        table = main_table(d)
        headers = [x.text.strip() for x in table.find_elements(By.CSS_SELECTOR, "thead th")]
        if not headers:
            headers = [x.text.strip() for x in table.find_elements(By.CSS_SELECTOR, "tr:first-child th, tr:first-child td")]

        seen_pages = set()
        for page in range(1, MAX_PAGES + 1):
            _, rows = read_rows(d)
            if not rows: raise RuntimeError("Table found but no rows extracted.")
            fp = fingerprint(rows)
            if fp in seen_pages:
                print("Repeated page detected; stopping.")
                break
            seen_pages.add(fp)
            collected.extend(rows)
            pages += 1
            print(f"Page {page}: {len(rows)} rows; total collected: {len(collected)}")
            nxt = next_control(d)
            if nxt is None:
                print("No enabled Next button; pagination complete.")
                break
            old = fp
            d.execute_script("arguments[0].scrollIntoView({block:'center'});", nxt)
            d.execute_script("arguments[0].click();", nxt)
            try:
                wait.until(lambda x: fingerprint(read_rows(x)[1]) != old)
            except TimeoutException:
                print("Table did not change after Next; stopping.")
                break
            time.sleep(1)
        else:
            print("MAX_PAGES reached; increase MAX_PAGES if required.")

        unique, seen = [], set()
        for row in collected:
            key = tuple(row)
            if key not in seen: seen.add(key); unique.append(row)
        if not unique: raise RuntimeError("No rows collected; refusing to publish an empty file.")
        width = max(len(r) for r in unique)
        unique = [r + [""] * (width-len(r)) for r in unique]
        if len(headers) != width: headers = [f"Column_{i+1}" for i in range(width)]
        df = pd.DataFrame(unique, columns=headers)
        stamp = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        meta = {"source_url": URL, "updated_at": stamp, "record_count": len(df),
                "pages_read": pages, "filename": "RCI_CRE_Calendar.xlsx",
                "note": "Automatically extracted from the publicly accessible RCI CRE Calendar webpage. Verify details with RCI."}
        with pd.ExcelWriter(XLSX, engine="openpyxl") as w:
            df.to_excel(w, sheet_name="All_Programmes", index=False)
            pd.DataFrame([meta]).to_excel(w, sheet_name="Update_Info", index=False)
            ws = w.sheets["All_Programmes"]; ws.freeze_panes = "A2"; ws.auto_filter.ref = ws.dimensions
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = min(max(max(len(str(c.value or "")) for c in col[:200])+2, 12), 45)
        META.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        (OUT / "calendar_page_backup.html").write_text(d.page_source, encoding="utf-8")
        print(f"SUCCESS: {len(df)} unique records from {pages} pages. Saved {XLSX}")
    finally:
        d.quit()

if __name__ == "__main__":
    main()
