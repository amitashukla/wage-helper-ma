"""Download MA Attorney General Workplace Rights PDFs.

Saves PDFs to data/publications/ and writes a manifest.json with metadata.
Uses polite 1-2s delays between requests.
"""

import json
import time
import random
from datetime import datetime, timezone
from pathlib import Path

import httpx

# All 24 documents organized by category
DOCUMENTS = [
    # Wage & Hour
    {
        "title": "Massachusetts Wage & Hour Laws Poster",
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

    headers = {
        "User-Agent": "MA-Wage-Helper-Research/1.0 (academic research project)"
    }

    with httpx.Client(headers=headers, follow_redirects=True, timeout=60.0) as client:
        for i, doc in enumerate(DOCUMENTS):
            slug = title_to_slug(doc["title"])
            pdf_path = output_dir / f"{slug}.pdf"

            print(f"[{i + 1}/{len(DOCUMENTS)}] Downloading: {doc['title']}")
            print(f"  URL: {doc['url']}")

            resp = client.get(doc["url"])

            if resp.status_code != 200:
                raise RuntimeError(
                    f"FAILED: {doc['title']} returned HTTP {resp.status_code}"
                )

            file_size_kb = len(resp.content) / 1024
            if file_size_kb < MIN_FILE_SIZE_KB:
                raise RuntimeError(
                    f"FAILED: {doc['title']} is only {file_size_kb:.1f} KB "
                    f"(minimum {MIN_FILE_SIZE_KB} KB). Possibly not a valid PDF."
                )

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


if __name__ == "__main__":
    download_all()
