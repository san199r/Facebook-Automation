# save as facebook_dealmachine_scraper.py
import os
import re
import time
import tkinter as tk
from tkinter import messagebox
from urllib.parse import urlparse, parse_qs, unquote

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None


START_URL = "https://www.facebook.com/dealmachineapp/followers/"
OUT_XLSX = "facebook_dealmachine_results.xlsx"

HEADERS = [
    "S.No",
    "Facebook Name",
    "Facebook Page URL",
    "Location",
    "Phone",
    "Email",
    "Website",
    "External Facebook",
    "External LinkedIn",
    "External Instagram",
]


def show_message_box():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    messagebox.showinfo("Info", "Enter the search/login details on the website, then click OK to begin.")
    root.destroy()


def show_resume_box(existing_rows: int):
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    messagebox.showinfo(
        "Resume",
        f"Found existing Excel with {existing_rows} rows.\n"
        f"I will resume and UPDATE rows that have blank contact fields."
    )
    root.destroy()


def show_end_box(msg: str):
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    messagebox.showinfo("Completed", msg)
    root.destroy()


def normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-infobars")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()),
        options=options
    )
    driver.set_page_load_timeout(60)
    return driver


def _last_saved_url_from_sheet(ws):
    try:
        for r in range(ws.max_row, 1, -1):
            v = ws.cell(r, 3).value
            if v and str(v).strip():
                return str(v).strip()
    except Exception:
        pass
    return ""


def load_or_create_workbook(path: str):
    """
    Returns:
      wb, ws, url_to_row, processed_urls, next_sno, last_saved_url
    """
    if os.path.exists(path):
        wb = load_workbook(path)
        ws = wb.active
        url_to_row = {}
        processed = set()
        max_sno = 0

        for r in range(2, ws.max_row + 1):
            sno = ws.cell(r, 1).value
            url = ws.cell(r, 3).value

            if sno and str(sno).isdigit():
                max_sno = max(max_sno, int(sno))

            if url:
                url = str(url).strip()
                url_to_row[url] = r

                # mark processed ONLY if any contact field exists
                fields = [ws.cell(r, c).value for c in range(4, 11)]
                if any(v not in (None, "", "None") for v in fields):
                    processed.add(url)

        last_saved_url = _last_saved_url_from_sheet(ws)
        return wb, ws, url_to_row, processed, max_sno + 1, last_saved_url

    wb = Workbook()
    ws = wb.active
    ws.title = "Results"
    bold = Font(bold=True)
    for c, h in enumerate(HEADERS, start=1):
        cell = ws.cell(1, c, h)
        cell.font = bold
    wb.save(path)
    return wb, ws, {}, set(), 1, ""


def upsert_row_and_save(wb, ws, xlsx_path: str, url_to_row: dict, row_values: list):
    url = str(row_values[2]).strip()
    if url in url_to_row:
        r = url_to_row[url]
        for c, val in enumerate(row_values, start=1):
            ws.cell(r, c).value = val
    else:
        ws.append(row_values)
        url_to_row[url] = ws.max_row

    wb.save(xlsx_path)


def wait_for_names_ready(driver, wait: WebDriverWait):
    wait.until(EC.presence_of_element_located((By.XPATH, "//div[@role='main']")))
    wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//div[@role='main']//a[@role='link' and @tabindex='0' and .//span[@dir='auto']]")
        )
    )


def get_name_anchor_candidates(driver):
    anchors = driver.find_elements(
        By.XPATH,
        "//div[@role='main']//a[@role='link' and @tabindex='0' and contains(@href,'facebook.com/') and .//span[@dir='auto']]"
    )

    bad_text = {
        "follow", "following", "message", "search", "more",
        "posts", "about", "mentions", "reviews", "reels", "photos",
        "privacy", "terms", "cookies", "advertising", "ad choices"
    }

    out = []
    seen = set()
    for a in anchors:
        try:
            href = (a.get_attribute("href") or "").strip()
            name = normalize_ws(a.text)
            if not href or not name:
                continue

            if name.lower() in bad_text:
                continue

            if "/dealmachineapp/" in href and "/followers" in href:
                continue

            key = (href, name)
            if key in seen:
                continue
            seen.add(key)

            out.append((name, href))
        except Exception:
            continue

    return out


# ---------------------------
# ✅ NEW helpers to STOP "going up" after resume / after opening tabs
# ---------------------------
def get_scroll_y(driver) -> int:
    try:
        return int(driver.execute_script("return window.pageYOffset || document.documentElement.scrollTop || 0;") or 0)
    except Exception:
        return 0


def set_scroll_y(driver, y: int):
    try:
        driver.execute_script("window.scrollTo(0, arguments[0]);", int(y))
    except Exception:
        pass


def element_abs_y(driver, el):
    try:
        return float(driver.execute_script(
            "var r=arguments[0].getBoundingClientRect();"
            "return r.top + (window.pageYOffset||document.documentElement.scrollTop||0);",
            el
        ))
    except Exception:
        return None


def bring_into_view_down_only(driver, el) -> bool:
    """
    ✅ Only scroll DOWN to make element clickable.
    If element is above current scroll (would require scrolling up), return False.
    """
    try:
        cur_y = get_scroll_y(driver)
        abs_y = element_abs_y(driver, el)
        if abs_y is None:
            return False

        # If element is above where we currently are -> do NOT go up (skip it)
        if abs_y < (cur_y - 50):
            return False

        # Check viewport position
        top = driver.execute_script("return arguments[0].getBoundingClientRect().top;", el)
        bottom = driver.execute_script("return arguments[0].getBoundingClientRect().bottom;", el)
        vh = driver.execute_script("return window.innerHeight || document.documentElement.clientHeight || 800;") or 800

        # If below viewport, scroll DOWN just enough
        if bottom > vh:
            delta = int(bottom - vh + 120)
            driver.execute_script("window.scrollBy(0, arguments[0]);", delta)
            time.sleep(0.3)

        # If still above viewport, that means we'd need to scroll UP -> don't
        top2 = driver.execute_script("return arguments[0].getBoundingClientRect().top;", el)
        if top2 < 0:
            return False

        return True
    except Exception:
        return False


def ctrl_click_open_new_tab(driver, element, timeout_sec: int = 10):
    """
    ✅ CHANGED: DO NOT scrollIntoView here (that caused jumping up/down).
    We'll ensure visibility with bring_into_view_down_only() before calling this.
    """
    before = set(driver.window_handles)

    try:
        ActionChains(driver).key_down(Keys.CONTROL).move_to_element(element).click(element).key_up(Keys.CONTROL).perform()
    except Exception:
        # fallback click without move
        try:
            ActionChains(driver).key_down(Keys.CONTROL).click(element).key_up(Keys.CONTROL).perform()
        except Exception:
            return False

    end_time = time.time() + timeout_sec
    while time.time() < end_time:
        now = set(driver.window_handles)
        diff = list(now - before)
        if diff:
            driver.switch_to.window(diff[0])
            return True
        time.sleep(0.2)

    return False


def close_current_tab_and_back(driver, main_handle: str):
    try:
        driver.close()
    except Exception:
        pass
    driver.switch_to.window(main_handle)


EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{6,}\d)")
DOMAIN_RE = re.compile(r"\b([a-z0-9-]+\.)+[a-z]{2,}\b", re.IGNORECASE)


def _decode_fb_redirect(url: str) -> str:
    try:
        p = urlparse(url)
        if "l.facebook.com" in p.netloc and p.path.startswith("/l.php"):
            qs = parse_qs(p.query)
            u = qs.get("u", [""])[0]
            if u:
                return unquote(u)
    except Exception:
        pass
    return url


def scrape_contact_info_robust(driver):
    location = ""
    phone = ""
    email = ""
    website_text = ""
    website_href = ""

    try:
        WebDriverWait(driver, 25).until(
            EC.presence_of_element_located((By.XPATH, "//div[@role='main']"))
        )
    except Exception:
        pass

    try:
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.4)
        driver.execute_script("window.scrollBy(0, 900);")
        time.sleep(1.2)
        driver.execute_script("window.scrollBy(0, 900);")
        time.sleep(1.2)
    except Exception:
        pass

    xieb = None
    try:
        intro_span = WebDriverWait(driver, 18).until(
            EC.presence_of_element_located((By.XPATH, "//span[normalize-space()='Intro']"))
        )
        intro_card = intro_span.find_element(
            By.XPATH, "ancestor::div[.//div[contains(@class,'xieb3on')]][1]"
        )
        xieb = intro_card.find_element(By.XPATH, ".//div[contains(@class,'xieb3on')]")
    except Exception:
        xieb = None

    texts = []
    links = []

    if xieb is not None:
        try:
            for sp in xieb.find_elements(By.XPATH, ".//span[@dir='auto']"):
                t = normalize_ws(sp.text)
                if t and t not in texts:
                    texts.append(t)

            for a in xieb.find_elements(By.XPATH, ".//a[@href]"):
                h = (a.get_attribute("href") or "").strip()
                t = normalize_ws(a.text)
                if h:
                    links.append((h, t))
        except Exception:
            pass

    for h, t in links:
        hh = h.lower()
        if hh.startswith("mailto:") and not email:
            email = h.split("mailto:", 1)[1].split("?", 1)[0].strip()
        if hh.startswith("tel:") and not phone:
            phone = normalize_ws(h.split("tel:", 1)[1].strip())

    for t in texts:
        if not email:
            m = EMAIL_RE.search(t)
            if m:
                email = m.group(0)

        if not phone:
            m = PHONE_RE.search(t)
            if m and ("@" not in t):
                digits = re.sub(r"\D", "", m.group(1))
                if len(digits) >= 7:
                    phone = normalize_ws(m.group(1))

    for h, t in links:
        dec = _decode_fb_redirect(h)
        if not dec.startswith("http"):
            continue
        netloc = (urlparse(dec).netloc or "").lower()
        if "facebook.com" in netloc or "fb.com" in netloc:
            continue
        website_href = dec
        website_text = t or dec
        break

    candidates = []
    for t in texts:
        if not t:
            continue
        if email and email in t:
            continue
        if website_text and website_text in t:
            continue
        if phone and phone in t:
            continue
        if "Not yet rated" in t:
            continue
        if "Page" in t and "·" in t:
            continue

        if 8 <= len(t) <= 120:
            candidates.append(t)

    for t in candidates:
        if "," in t and re.search(r"\d", t):
            location = t
            break

    if not location:
        for t in candidates:
            if "," in t:
                location = t
                break

    return location, phone, email, website_text, website_href


def parse_social_links_from_html(html: str):
    out = {"facebook": "", "linkedin": "", "instagram": ""}
    if not html:
        return out

    if BeautifulSoup is not None:
        soup = BeautifulSoup(html, "html.parser")

        for k in ["facebook", "linkedin", "instagram"]:
            a = soup.find("a", id=k)
            if a and a.get("href"):
                out[k] = (a.get("href") or "").strip()

        hrefs = [a.get("href", "").strip() for a in soup.select("a[href]")]

        def pick(domain: str):
            for h in hrefs:
                if domain in (h or "").lower():
                    return h
            return ""

        if not out["facebook"]:
            out["facebook"] = pick("facebook.com")
        if not out["linkedin"]:
            out["linkedin"] = pick("linkedin.com")
        if not out["instagram"]:
            out["instagram"] = pick("instagram.com")

        return out

    patterns = {
        "facebook": r"(https?://[^\s\"'>]*facebook\.com[^\s\"'>]*)",
        "linkedin": r"(https?://[^\s\"'>]*linkedin\.com[^\s\"'>]*)",
        "instagram": r"(https?://[^\s\"'>]*instagram\.com[^\s\"'>]*)",
    }
    for k, pat in patterns.items():
        m = re.search(pat, html, flags=re.IGNORECASE)
        if m:
            out[k] = m.group(1)
    return out


def scrape_external_socials(driver, website_url: str):
    out = {"facebook": "", "linkedin": "", "instagram": ""}
    if not website_url:
        return out

    main_handle = driver.current_window_handle
    try:
        driver.execute_script("window.open(arguments[0], '_blank');", website_url)
        time.sleep(0.6)
        driver.switch_to.window(driver.window_handles[-1])
        time.sleep(2)

        for key in ["facebook", "linkedin", "instagram"]:
            try:
                el = driver.find_elements(By.CSS_SELECTOR, f"#{key}")
                if el:
                    href = el[0].get_attribute("href") or ""
                    if href:
                        out[key] = href.strip()
            except Exception:
                pass

        if not (out["facebook"] or out["linkedin"] or out["instagram"]):
            out.update(parse_social_links_from_html(driver.page_source or ""))

    except Exception:
        pass
    finally:
        try:
            driver.close()
        except Exception:
            pass
        driver.switch_to.window(main_handle)

    return out


def _try_find_anchor_by_url(driver, url: str):
    try:
        key_part = url.split("facebook.com/")[-1].split("?")[0].strip("/")
        if not key_part:
            return None
        els = driver.find_elements(
            By.XPATH,
            f"//div[@role='main']//a[@role='link' and @tabindex='0' and contains(@href,'{key_part}') and .//span[@dir='auto']]"
        )
        return els[0] if els else None
    except Exception:
        return None


def scroll_to_resume_point_down_only(driver, last_saved_url: str):
    """
    Resume: from CURRENT position, only scroll DOWN until last_saved_url appears below,
    then scroll a bit more so next scraping continues after it.
    """
    if not last_saved_url:
        return

    max_steps = 80
    step_px = 1400

    for _ in range(max_steps):
        cur_y = get_scroll_y(driver)

        el = _try_find_anchor_by_url(driver, last_saved_url)
        if el is not None:
            el_y = element_abs_y(driver, el)
            if el_y is not None and el_y >= cur_y:
                try:
                    # this will only go down (because el_y >= cur_y)
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                    time.sleep(0.8)
                    driver.execute_script("window.scrollBy(0, 1200);")
                    time.sleep(0.8)
                except Exception:
                    pass
                break

        try:
            driver.execute_script("window.scrollBy(0, arguments[0]);", step_px)
            time.sleep(1.2)
        except Exception:
            time.sleep(1.0)


def facebook_dealmachine_scraper():
    driver = None
    wb = ws = None
    url_to_row = {}
    processed = set()
    next_sno = 1
    last_saved_url = ""

    saved_count = 0
    updated_count = 0
    skipped_count = 0

    try:
        wb, ws, url_to_row, processed, next_sno, last_saved_url = load_or_create_workbook(OUT_XLSX)
        resume_mode = (ws.max_row > 1)

        if resume_mode:
            show_resume_box(ws.max_row - 1)

        driver = init_driver()
        wait = WebDriverWait(driver, 30)

        driver.get(START_URL)
        show_message_box()

        if resume_mode:
            time.sleep(2)
        else:
            time.sleep(0.5)

        wait_for_names_ready(driver, wait)
        main_handle = driver.current_window_handle

        if resume_mode and last_saved_url:
            scroll_to_resume_point_down_only(driver, last_saved_url)

        no_new_scrolls = 0
        max_no_new_scrolls = 6

        # ✅ prevents repeating same name over and over in the SAME run
        attempted_this_run = set()

        while no_new_scrolls < max_no_new_scrolls:
            candidates = get_name_anchor_candidates(driver)
            todo = [(n, h) for (n, h) in candidates]

            did_any_work_this_round = False

            for name, href in todo:
                href = (href or "").strip()
                if not href:
                    continue

                if href in attempted_this_run:
                    continue
                attempted_this_run.add(href)

                exists = href in url_to_row
                already_good = href in processed
                if exists and already_good:
                    skipped_count += 1
                    continue

                try:
                    # ✅ IMPORTANT: remember current scroll, and NEVER allow this record click to move us UP
                    scroll_before = get_scroll_y(driver)

                    key_part = href.split("facebook.com/")[-1].split("?")[0].strip("/")
                    elem = None
                    try:
                        elem = driver.find_element(
                            By.XPATH,
                            f"//div[@role='main']//a[@role='link' and @tabindex='0' and contains(@href,'{key_part}') and .//span[@dir='auto']]"
                        )
                    except Exception:
                        try:
                            elem = driver.find_element(
                                By.XPATH,
                                f"//div[@role='main']//a[@role='link' and @tabindex='0' and .//span[@dir='auto' and normalize-space()=\"{name}\"]]"
                            )
                        except Exception:
                            elem = None

                    opened = False
                    click_scroll_y = scroll_before

                    if elem is not None:
                        # ✅ Only bring into view by scrolling DOWN; if it would require scrolling UP, skip it
                        if not bring_into_view_down_only(driver, elem):
                            continue

                        # update click_scroll_y (we may have scrolled down a bit)
                        click_scroll_y = get_scroll_y(driver)

                        opened = ctrl_click_open_new_tab(driver, elem, timeout_sec=10)

                    if not opened:
                        # fallback open in new tab without touching scroll
                        driver.execute_script("window.open(arguments[0], '_blank');", href)
                        time.sleep(0.6)
                        driver.switch_to.window(driver.window_handles[-1])

                    time.sleep(2)

                    location, phone, email, website_text, website_href = scrape_contact_info_robust(driver)

                    socials = {"facebook": "", "linkedin": "", "instagram": ""}
                    if website_href:
                        socials = scrape_external_socials(driver, website_href)

                    close_current_tab_and_back(driver, main_handle)

                    # ✅ KEY FIX YOU ASKED:
                    # After returning back, stay at the SAME place (do NOT jump up).
                    set_scroll_y(driver, click_scroll_y)
                    time.sleep(0.2)

                    if exists:
                        r = url_to_row[href]
                        sno_val = ws.cell(r, 1).value
                        sno = int(sno_val) if str(sno_val).isdigit() else next_sno
                    else:
                        sno = next_sno

                    row = [
                        sno,
                        name,
                        href,
                        location,
                        phone,
                        email,
                        website_text,
                        socials.get("facebook", ""),
                        socials.get("linkedin", ""),
                        socials.get("instagram", ""),
                    ]

                    before_exists = exists
                    upsert_row_and_save(wb, ws, OUT_XLSX, url_to_row, row)

                    did_any_work_this_round = True

                    if any(v not in (None, "", "None") for v in row[3:]):
                        processed.add(href)

                    if before_exists:
                        updated_count += 1
                        print(f"[UPDATED] record saved S.No={sno} | {name} | loc={bool(location)} phone={bool(phone)} email={bool(email)} web={bool(website_text or website_href)}")
                    else:
                        saved_count += 1
                        print(f"[SAVED] record saved S.No={sno} | {name} | loc={bool(location)} phone={bool(phone)} email={bool(email)} web={bool(website_text or website_href)}")
                        next_sno += 1

                except Exception:
                    try:
                        if driver.current_window_handle != main_handle:
                            close_current_tab_and_back(driver, main_handle)
                    except Exception:
                        pass
                    continue

            # ✅ keep moving DOWN only after finishing visible records
            driver.execute_script("window.scrollBy(0, 1400);")
            time.sleep(2)

            if not did_any_work_this_round:
                no_new_scrolls += 1
            else:
                no_new_scrolls = 0

        show_end_box(
            f"Scraping completed.\n\nNew Saved: {saved_count}\nUpdated (filled blanks): {updated_count}\nSkipped: {skipped_count}\nFile: {OUT_XLSX}"
        )

    except Exception as e:
        try:
            show_end_box(
                f"Tool stopped in mid scraping, but file is saved.\n\n"
                f"New Saved: {saved_count}\nUpdated: {updated_count}\nFile: {OUT_XLSX}\n\nError: {e}"
            )
        except Exception:
            pass
        raise
    finally:
        try:
            if wb is not None:
                wb.save(OUT_XLSX)
        except Exception:
            pass
        try:
            if driver is not None:
                driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    facebook_dealmachine_scraper()
