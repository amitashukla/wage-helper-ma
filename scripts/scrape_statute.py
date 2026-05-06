"""
Phase 1C — Scrape MA General Laws Chapter 149 using Playwright.

Outputs: data/statutes/chapter149_v{YYYYMMDD}.json

Each entry: {section_id, section_title, text}
"""

import json
import os
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

load_dotenv()

BASE_URL = "https://malegislature.gov/Laws/GeneralLaws/PartI/TitleXXI/Chapter149"
STATUTE_VERSION = os.getenv("STATUTE_VERSION", date.today().strftime("%Y%m%d"))
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "statutes"
OUTPUT_FILE = OUTPUT_DIR / f"chapter149_v{STATUTE_VERSION}.json"
FAILED_SECTIONS_FILE = OUTPUT_DIR / f"chapter149_failed_sections_v{STATUTE_VERSION}.txt"


def scrape_chapter_index(page):
    """Scrape the chapter TOC page to get section URLs, numbers, and titles."""
    page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60_000)

    # The chapter page lists sections as links in a list
    section_links = page.query_selector_all("ul.sections-list li a, #contentBody ul li a")
    if not section_links:
        # Try alternative selector used on malegislature.gov
        section_links = page.query_selector_all("a[href*='/Laws/GeneralLaws/PartI/TitleXXI/Chapter149/Section']")

    if not section_links:
        raise RuntimeError(
            "Could not find section links on chapter index page. "
            "The page structure may have changed. "
            f"URL: {BASE_URL}"
        )

    sections = []
    for link in section_links:
        href = link.get_attribute("href")
        text = link.inner_text().strip()
        if href and "Section" in href:
            sections.append({"href": href, "link_text": text})

    if not sections:
        raise RuntimeError("Parsed zero sections from chapter index. Selectors may be stale.")

    print(f"Found {len(sections)} sections in chapter index.")
    return sections


def scrape_section(page, section_info):
    """Navigate to a single section page and extract its content."""
    href = section_info["href"]
    url = href if href.startswith("http") else f"https://malegislature.gov{href}"

    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_selector("main .content, main", timeout=15_000)

    # Extract section number from heading or URL
    section_id = url.rstrip("/").split("/")[-1]  # e.g. "Section1"

    # Try to get section title
    title_el = page.query_selector("h2.genLawHeading, h1, h2, .title")
    section_title = title_el.inner_text().strip() if title_el else section_info["link_text"]

    # Default extraction path with graceful fallback for structure changes.
    text = None
    content_selectors = [
        "main .content .col-xs-12.col-md-8 .col-xs-12",
        "main .content",
        "main",
    ]
    for selector in content_selectors:
        content_el = page.query_selector(selector)
        if not content_el:
            continue

        paragraphs = content_el.query_selector_all("p")
        paragraph_text = [p.inner_text().strip() for p in paragraphs if p.inner_text().strip()]
        if paragraph_text:
            text = "\n\n".join(paragraph_text).strip()
            break

        candidate = content_el.inner_text().strip()
        if candidate:
            text = candidate
            break

    # Last-resort fallback to body text if all scoped selectors fail.
    if not text:
        body_text = page.inner_text("body").strip()
        if body_text:
            text = body_text

    if not text:
        raise RuntimeError(
            f"Could not extract text for section {section_id}. "
            f"URL: {url}"
        )

    return {
        "section_id": section_id,
        "section_title": section_title,
        "text": text,
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            sections_index = scrape_chapter_index(page)
        except PlaywrightTimeout:
            print("ERROR: Timed out loading chapter index page.", file=sys.stderr)
            sys.exit(1)

        results = []
        failed_sections = []
        for i, sec in enumerate(sections_index):
            print(f"  [{i+1}/{len(sections_index)}] Scraping {sec['link_text'][:60]}...")
            section_id = sec["href"].rstrip("/").split("/")[-1]
            try:
                data = scrape_section(page, sec)
                if data:
                    results.append(data)
            except PlaywrightTimeout:
                print(f"  WARNING: Timeout on {sec['href']}, skipping.")
                failed_sections.append(section_id)
            except Exception as e:
                print(f"  WARNING: Error on {sec['href']}: {e}")
                failed_sections.append(section_id)

        browser.close()

    if not results:
        print("ERROR: Scraped zero sections successfully.", file=sys.stderr)
        sys.exit(1)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    if failed_sections:
        with open(FAILED_SECTIONS_FILE, "w", encoding="utf-8") as f:
            for section_id in failed_sections:
                f.write(f"{section_id}\n")
        print(
            f"Wrote {len(failed_sections)} failed sections to {FAILED_SECTIONS_FILE}"
        )
    else:
        print("All sections scraped successfully; no failed-sections file written.")

    print(f"\nDone. Wrote {len(results)} sections to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
