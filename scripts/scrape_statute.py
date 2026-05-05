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

    # Extract section number from heading or URL
    section_id = url.rstrip("/").split("/")[-1]  # e.g. "Section1"

    # Try to get section title
    title_el = page.query_selector("h1, h2, .title, #contentBody h1")
    section_title = title_el.inner_text().strip() if title_el else section_info["link_text"]

    # Extract statutory text from the main content area
    content_el = page.query_selector(
        "#contentBody .content, "
        "#contentBody .sectionBody, "
        "#contentBody .law-content, "
        "#contentBody"
    )

    if not content_el:
        raise RuntimeError(
            f"Could not find content element for section {section_id}. "
            f"URL: {url}"
        )

    # Get text content, stripping navigation/chrome
    text = content_el.inner_text().strip()

    if not text:
        print(f"  WARNING: Empty text for {section_id}, skipping.")
        return None

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
        for i, sec in enumerate(sections_index):
            print(f"  [{i+1}/{len(sections_index)}] Scraping {sec['link_text'][:60]}...")
            try:
                data = scrape_section(page, sec)
                if data:
                    results.append(data)
            except PlaywrightTimeout:
                print(f"  WARNING: Timeout on {sec['href']}, skipping.")
            except Exception as e:
                print(f"  WARNING: Error on {sec['href']}: {e}")

        browser.close()

    if not results:
        print("ERROR: Scraped zero sections successfully.", file=sys.stderr)
        sys.exit(1)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nDone. Wrote {len(results)} sections to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
