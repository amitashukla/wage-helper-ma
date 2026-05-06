"""Download MA Attorney General Workplace Rights PDFs.

Saves PDFs to data/publications/ and writes a manifest.json with metadata.
Uses polite 1-2s delays between requests.
"""

import json
import time
import random
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx

# All 24 documents organized by category
DOCUMENTS = [
    # Wage & Hour
    {
        "title": "Massachusetts Wage and Hour Laws Poster",
        "category": "Wage & Hour",
        "url": "https://www.mass.gov/doc/massachusetts-wage-hour-laws-poster-english/download",
    },
    {
        "title": "Guide to Workplace Rights and Responsibilities",
        "category": "Wage & Hour",
        "url": "https://www.mass.gov/doc/guide-to-workplace-rights-and-responsibilities-0/download",
    },
    # Anti-Retaliation
    {
        "title": "Anti-Retaliation Fact Sheet",
        "category": "Anti-Retaliation",
        "url": "https://www.mass.gov/doc/anti-retaliation-fact-sheet/download",
    },
    # Earned Sick Time
    {
        "title": "Earned Sick Time Notice of Employee Rights",
        "category": "Earned Sick Time",
        "url": "https://www.mass.gov/doc/earned-sick-time-notice-of-employee-rights-english/download",
    },
    {
        "title": "Does your employer's earned sick time policy follow state law?",
        "category": "Earned Sick Time",
        "url": "https://www.mass.gov/doc/does-your-employers-earned-sick-time-policy-follow-state-law/download",
    },
    {
        "title": "Do you qualify for earned sick time?",
        "category": "Earned Sick Time",
        "url": "https://www.mass.gov/doc/do-you-qualify-for-earned-sick-time/download",
    },
    {
        "title": "Earned Sick Time FAQs",
        "category": "Earned Sick Time",
        "url": "https://www.mass.gov/doc/earned-sick-time-faqs/download",
    },
    # Child Labor
    {
        "title": "Child Labor Laws Poster",
        "category": "Child Labor",
        "url": "https://www.mass.gov/doc/child-labor-laws-poster/download",
    },
    {
        "title": "Guide for Working Teens",
        "category": "Child Labor",
        "url": "https://www.mass.gov/doc/guide-for-working-teens/download",
    },
    {
        "title": "Preventing Child Labor Exploitation Fact Sheet",
        "category": "Child Labor",
        "url": "https://www.mass.gov/doc/preventing-child-labor-exploitation-fact-sheet/download",
    },
    # Domestic Workers
    {
        "title": "Notice of Rights for Domestic Workers",
        "category": "Domestic Workers",
        "url": "https://www.mass.gov/doc/notice-of-rights-for-domestic-workers/download",
    },
    {
        "title": "Workplace Rights and Protections for Domestic Workers",
        "category": "Domestic Workers",
        "url": "https://www.mass.gov/doc/workplace-rights-and-protections-for-domestic-workers/download",
    },
    # Domestic Violence Leave
    {
        "title": "AG advisory on domestic violence leave",
        "category": "Domestic Violence Leave",
        "url": "https://www.mass.gov/doc/attorney-generals-advisory-on-domestic-violence-leave/download",
    },
    {
        "title": "Understanding domestic violence leave",
        "category": "Domestic Violence Leave",
        "url": "https://www.mass.gov/doc/understanding-domestic-violence-leave/download",
    },
    # Prevailing Wage
    {
        "title": "MA Prevailing Wage Laws: Guide for Awarding Authorities",
        "category": "Prevailing Wage",
        "url": "https://www.mass.gov/doc/massachusetts-prevailing-wage-laws-an-important-guide-for-awarding-authorities/download",
    },
    {
        "title": "MA Prevailing Wage Laws: Guide for Public Construction Contractors",
        "category": "Prevailing Wage",
        "url": "https://www.mass.gov/doc/massachusetts-prevailing-wage-laws-an-important-guide-for-public-construction-contractors/download",
    },
    {
        "title": "MA Prevailing Wage Laws: Guide for Workers",
        "category": "Prevailing Wage",
        "url": "https://www.mass.gov/doc/massachusetts-prevailing-wage-laws-an-important-guide-for-workers/download",
    },
    # Advisories
    {
        "title": "Advisory on the OSHA 10 Act",
        "category": "Advisories",
        "url": "https://www.mass.gov/doc/advisory-on-the-osha-10-act/download",
    },
    {
        "title": "Advisory on wage and hour rights of immigrant workers",
        "category": "Advisories",
        "url": "https://www.mass.gov/doc/advisory-on-the-wage-and-hour-rights-of-immigrant-workers/download",
    },
    {
        "title": "Advisory on recoupment of inadvertent wage overpayments",
        "category": "Advisories",
        "url": "https://www.mass.gov/doc/attorney-generals-advisory-on-recoupment-of-inadvertent-wage-overpayments/download",
    },
    {
        "title": "Advisory on small necessities leave",
        "category": "Advisories",
        "url": "https://www.mass.gov/doc/attorney-generals-advisory-on-small-necessities-leave/download",
    },
    {
        "title": "Advisory on the Independent Contractor Law",
        "category": "Advisories",
        "url": "https://www.mass.gov/doc/attorney-generals-advisory-on-the-independent-contractor-law/download",
    },
    {
        "title": "Advisory on tips",
        "category": "Advisories",
        "url": "https://www.mass.gov/doc/attorney-generals-advisory-on-tips/download",
    },
    {
        "title": "Advisory on vacation policies",
        "category": "Advisories",
        "url": "https://www.mass.gov/doc/attorney-generals-advisory-on-vacation-policies/download",
    },
    {
        "title": "AG Advisory: Affirming Labor Rights in Public Workplaces",
        "category": "Advisories",
        "url": "https://www.mass.gov/doc/attorney-general-advisory-affirming-labor-rights-and-obligations-in-public-workplaces-0/download",
    },
    {
        "title": "Information for Foreign Nationals on Wage and Hour Law Compliance",
        "category": "Advisories",
        "url": "https://www.mass.gov/doc/information-for-foreign-nationals-on-compliance-with-wage-and-hour-laws-in-massachusetts/download",
    },
    {
        "title": "U&T Visa Certification Guidance",
        "category": "Advisories",
        "url": "https://www.mass.gov/doc/ut-visa-certification-guidance/download",
    },
    # Labor Trafficking
    {
        "title": "Learn to Recognize the Signs of Labor Trafficking",
        "category": "Labor Trafficking",
        "url": "https://www.mass.gov/doc/learn-to-recognize-the-signs-of-labor-trafficking/download",
    },
]

MIN_FILE_SIZE_KB = 10
RETRY_STATUS_CODES = {403, 429, 500, 502, 503, 504}
MAX_DOWNLOAD_ATTEMPTS = 3
PLAYWRIGHT_UNAVAILABLE_ERROR = (
    "Playwright fallback unavailable. Install with "
    "`pip install playwright && playwright install chromium`."
)
MASS_GOV_COOKIE_ENV = "MASS_GOV_COOKIE"
MASS_GOV_EXTRA_HEADERS_ENV = "MASS_GOV_EXTRA_HEADERS_JSON"


def build_browser_headers(referer: str | None = None) -> dict[str, str]:
    """Build browser-like headers to reduce false-positive bot blocking."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/pdf,application/octet-stream,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
    }
    if referer:
        headers["Referer"] = referer
    return headers


def parse_extra_headers_from_env() -> dict[str, str]:
    """Parse optional JSON headers from env for manual anti-bot bypass."""
    raw = os.getenv(MASS_GOV_EXTRA_HEADERS_ENV, "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        print(
            f"WARNING: Ignoring invalid {MASS_GOV_EXTRA_HEADERS_ENV}; "
            "expected JSON object."
        )
        return {}
    if not isinstance(parsed, dict):
        print(
            f"WARNING: Ignoring invalid {MASS_GOV_EXTRA_HEADERS_ENV}; "
            "expected JSON object."
        )
        return {}
    out: dict[str, str] = {}
    for key, value in parsed.items():
        out[str(key)] = str(value)
    return out


def build_manual_override_headers(referer: str | None = None) -> dict[str, str]:
    """Build optional operator-provided headers/cookies from env."""
    headers: dict[str, str] = {}
    cookie = os.getenv(MASS_GOV_COOKIE_ENV, "").strip()
    if cookie:
        headers["Cookie"] = cookie
    headers.update(parse_extra_headers_from_env())
    if referer and "Referer" not in headers:
        headers["Referer"] = referer
    return headers


def derive_landing_page_url(download_url: str) -> str:
    """Convert `/download` URLs to the document landing page URL."""
    parsed = urlparse(download_url)
    path = parsed.path
    if path.endswith("/download"):
        path = path[: -len("/download")]
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def try_download_with_fallback(client: httpx.Client, url: str) -> httpx.Response:
    """Download a document with retry and anti-bot fallback handling."""
    last_response: httpx.Response | None = None
    landing_page_url = derive_landing_page_url(url)

    for attempt in range(1, MAX_DOWNLOAD_ATTEMPTS + 1):
        resp = client.get(url)
        last_response = resp
        if resp.status_code == 200:
            return resp

        if resp.status_code == 403:
            # Common mitigation: retry with browser-like headers and referer.
            browser_resp = client.get(
                url,
                headers=build_browser_headers(referer=landing_page_url),
            )
            last_response = browser_resp
            if browser_resp.status_code == 200:
                return browser_resp

            # Operator fallback: allow manual cookie/headers from env.
            manual_headers = build_manual_override_headers(referer=landing_page_url)
            if manual_headers:
                manual_resp = client.get(url, headers=manual_headers)
                last_response = manual_resp
                if manual_resp.status_code == 200:
                    return manual_resp

        if resp.status_code not in RETRY_STATUS_CODES:
            break

        if attempt < MAX_DOWNLOAD_ATTEMPTS:
            backoff_seconds = 1.0 * attempt
            time.sleep(backoff_seconds)

    if last_response is None:
        raise RuntimeError(f"FAILED: request did not return a response for {url}")
    return last_response


def try_download_with_playwright(url: str) -> tuple[bytes | None, str | None]:
    """Attempt download via browser session to bypass anti-bot protections."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None, PLAYWRIGHT_UNAVAILABLE_ERROR

    landing_page_url = derive_landing_page_url(url)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=build_browser_headers()["User-Agent"])
            page = context.new_page()

            # Warm up session and challenge cookies on landing page first.
            page.goto(landing_page_url, wait_until="domcontentloaded", timeout=60_000)

            # Use browser-context request API with warmed session cookies.
            # Avoid waiting for "networkidle" on download endpoints, which can hang.
            req_headers = {
                "Referer": landing_page_url,
                "Accept": "application/pdf,application/octet-stream,*/*",
            }
            req_headers.update(build_manual_override_headers(referer=landing_page_url))
            api_response = context.request.get(
                url,
                headers=req_headers,
                timeout=60_000,
            )
            if api_response.status == 200:
                body = api_response.body()
                browser.close()
                return body, None

            status = api_response.status if api_response else "unknown"
            browser.close()
            return None, f"Playwright HTTP {status}"
    except Exception as exc:
        return None, f"Playwright error: {exc}"


def title_to_slug(title: str) -> str:
    """Convert a document title to a filesystem-safe slug."""
    slug = title.lower()
    # Replace special characters with hyphens
    for ch in ["&", ":", "'", "’", ",", ".", "?", "/"]:
        slug = slug.replace(ch, "")
    # Replace spaces and multiple hyphens
    slug = slug.replace(" ", "-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


def download_all() -> None:
    """Download all publications and write manifest."""
    output_dir = Path(__file__).resolve().parent.parent / "data" / "publications"
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest: list[dict] = []
    failures: list[dict] = []

    headers = build_browser_headers()
    if os.getenv(MASS_GOV_COOKIE_ENV, "").strip():
        print(f"Manual cookie override detected via {MASS_GOV_COOKIE_ENV}.")
        headers.update(build_manual_override_headers())
    extra_headers = parse_extra_headers_from_env()
    if extra_headers:
        print(f"Manual header overrides detected via {MASS_GOV_EXTRA_HEADERS_ENV}.")
        headers.update(extra_headers)

    with httpx.Client(headers=headers, follow_redirects=True, timeout=60.0) as client:
        for i, doc in enumerate(DOCUMENTS):
            slug = title_to_slug(doc["title"])
            pdf_path = output_dir / f"{slug}.pdf"

            print(f"[{i + 1}/{len(DOCUMENTS)}] Downloading: {doc['title']}")
            print(f"  URL: {doc['url']}")

            resp = try_download_with_fallback(client, doc["url"])

            if resp.status_code != 200:
                error_msg = f"HTTP {resp.status_code}"
                if resp.status_code == 403:
                    print("  HTTP blocked. Trying Playwright browser fallback...")
                    playwright_bytes, playwright_error = try_download_with_playwright(
                        doc["url"]
                    )
                    if playwright_bytes:
                        file_size_kb = len(playwright_bytes) / 1024
                        if file_size_kb >= MIN_FILE_SIZE_KB:
                            pdf_path.write_bytes(playwright_bytes)
                            print(
                                "  Saved via Playwright fallback: "
                                f"{pdf_path.name} ({file_size_kb:.1f} KB)"
                            )
                            manifest.append(
                                {
                                    "slug": slug,
                                    "title": doc["title"],
                                    "category": doc["category"],
                                    "url": doc["url"],
                                    "downloaded_at": datetime.now(
                                        timezone.utc
                                    ).isoformat(),
                                    "file_size_kb": round(file_size_kb, 1),
                                }
                            )
                            if i < len(DOCUMENTS) - 1:
                                delay = random.uniform(1.0, 2.0)
                                time.sleep(delay)
                            continue
                        error_msg = (
                            f"Playwright file too small: {file_size_kb:.1f} KB "
                            f"(minimum {MIN_FILE_SIZE_KB} KB)"
                        )
                    elif playwright_error:
                        error_msg = f"{error_msg}; {playwright_error}"
                print(
                    f"  WARNING: Could not download '{doc['title']}' ({error_msg}). "
                    "Skipping and continuing."
                )
                failures.append(
                    {
                        "title": doc["title"],
                        "category": doc["category"],
                        "url": doc["url"],
                        "error": error_msg,
                        "failed_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                if i < len(DOCUMENTS) - 1:
                    delay = random.uniform(1.0, 2.0)
                    time.sleep(delay)
                continue

            file_size_kb = len(resp.content) / 1024
            if file_size_kb < MIN_FILE_SIZE_KB:
                error_msg = (
                    f"File too small: {file_size_kb:.1f} KB "
                    f"(minimum {MIN_FILE_SIZE_KB} KB)"
                )
                print(
                    f"  WARNING: '{doc['title']}' looks invalid ({error_msg}). "
                    "Skipping and continuing."
                )
                failures.append(
                    {
                        "title": doc["title"],
                        "category": doc["category"],
                        "url": doc["url"],
                        "error": error_msg,
                        "failed_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                if i < len(DOCUMENTS) - 1:
                    delay = random.uniform(1.0, 2.0)
                    time.sleep(delay)
                continue

            pdf_path.write_bytes(resp.content)
            print(f"  Saved: {pdf_path.name} ({file_size_kb:.1f} KB)")

            manifest.append(
                {
                    "slug": slug,
                    "title": doc["title"],
                    "category": doc["category"],
                    "url": doc["url"],
                    "downloaded_at": datetime.now(timezone.utc).isoformat(),
                    "file_size_kb": round(file_size_kb, 1),
                }
            )

            # Polite delay (1-2 seconds) between requests
            if i < len(DOCUMENTS) - 1:
                delay = random.uniform(1.0, 2.0)
                time.sleep(delay)

    # Write manifest
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\nManifest written to {manifest_path}")
    print(f"Total documents downloaded: {len(manifest)}")
    if failures:
        print(f"Total documents skipped: {len(failures)}")
        failures_path = output_dir / "manifest_failures.json"
        failures_path.write_text(json.dumps(failures, indent=2))
        print(f"Failures written to {failures_path}")


if __name__ == "__main__":
    download_all()
