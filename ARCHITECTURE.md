# CSF MyCarParts Scraper - Architecture

## DRY Principle: Single Source of Truth

This document defines the **single source of truth** for each scraping operation to maintain DRY (Don't Repeat Yourself) principles.

---

## Pipeline Overview

```
scrape_catalog.py          enrich_details.py          merge_for_import.py
     Phase 1                    Phase 2                    Phase 3
 ┌─────────────┐          ┌─────────────────┐        ┌──────────────┐
 │ Hierarchy    │          │ Detail pages    │        │ Merge compat │
 │ Applications │──parts──→│ Descriptions    │──parts─→│ into parts   │
 │ Basic parts  │  .json   │ Specs, images   │  _with  │              │
 │ Compat data  │          │ Interchange     │ details │              │
 └─────────────┘          └─────────────────┘  .json  └──────┬───────┘
       │                                                      │
       └── compatibility.json                    parts_complete.json
```

`run_scrape.py` orchestrates all three phases when using `--catalog --details`.

---

## Phase 1: Catalog Scraping

**Single Source:** `scrape_catalog.py` (delegates to `src/scraper/orchestrator.py`)

**Responsibilities:**
- Build vehicle hierarchy (makes, years, models, applications)
- Fetch application pages for each vehicle configuration
- Extract basic part data: SKU, name, category, manufacturer, stock status, specs
- Deduplicate parts across application pages
- Track vehicle compatibility per part
- Save checkpoints for resume capability

**Output:**
- `exports/parts.json` — Part catalog with basic info
- `exports/compatibility.json` — Vehicle compatibility data

**Never duplicated elsewhere.**

---

## Phase 2: Detail Page Enrichment

**Single Source:** `enrich_details.py`

**Responsibilities:**
- Fetch detail pages (one per part SKU) from `csf.autocaredata.com`
- Extract complete product data using `parser.extract_detail_page_data()`:
  - Full product descriptions (HTML)
  - Detailed specifications (~22 fields)
  - Technical notes
  - Interchange data (competitor part numbers)
  - Gallery images (large images only)
- Download images and convert to AVIF format
- Merge detail data into catalog data
- Skip already-enriched parts (unless `--force`)

**Output:**
- `exports/parts_with_details.json` — Complete enriched data

**This is the ONLY script that fetches detail pages. Never duplicated elsewhere.**

---

## Phase 3: Auto-Merge

**Single Source:** `merge_for_import.py` (also built into `run_scrape.py`)

**Responsibilities:**
- Merge `compatibility.json` into `parts_with_details.json`
- Produce the final import-ready file

**Output:**
- `exports/parts_complete.json` — Final merged data for WordPress import

---

## Change Detection

### Tier 1: Hierarchy Fingerprint

**File:** `src/scraper/orchestrator.py` (`_get_hierarchy_fingerprint`)

MD5 hash of the entire vehicle hierarchy structure (makes, years, models, application IDs). Stored in `checkpoints/hierarchy_fingerprint_*.txt`.

```bash
python scrape_catalog.py --check-changes
```

- If fingerprint matches previous run: **skip entire scrape**
- If fingerprint differs: proceed with scrape
- Detects: new vehicles, removed vehicles, new applications
- Does NOT detect: part detail changes (price, description, images)

### Tier 2: Part Content Hashing

**File:** `src/scraper/orchestrator.py` (`_content_hash`)

MD5 hash of content-relevant fields per part:

```python
content = {
    "sku", "name", "price", "category",
    "specifications", "images", "manufacturer",
    "in_stock", "features", "position"
}
```

**Excluded from hash** (to prevent false positives):
- `scraped_at` — Volatile timestamp
- `description`, `tech_notes`, `interchange_numbers` — Enrichment-only fields

```bash
python scrape_catalog.py --incremental
```

Loads previous `parts.json`, computes hashes, compares during deduplication. Only changed parts are flagged.

---

## Checkpoint/Resume

**File:** `src/scraper/orchestrator.py` (`_save_checkpoint`, `_load_checkpoint`)

Checkpoints save every 10 applications and include:
- All scraped parts data
- Vehicle compatibility data
- Set of processed application IDs
- Make/year filter context

```bash
# Resume from latest checkpoint
python scrape_catalog.py --resume
```

Failed applications are **not** added to `processed_application_ids`, so they are automatically retried on resume.

---

## Core Modules

### Parser (`src/scraper/parser.py`)

| Method | Purpose | Called By |
|--------|---------|-----------|
| `extract_all_parts_from_application_page()` | Extract all parts from an application page | `orchestrator.py` |
| `extract_detail_page_data()` | Extract complete detail page data | `enrich_details.py` |
| `_extract_vehicle_qualifiers()` | Parse engine, aspiration, transmission from HTML table | Internal |
| `_extract_gallery_images()` | Extract large S3 images from detail page | Internal |
| `_extract_clean_engine_spec()` | Clean engine strings, remove non-engine data | Internal |

### Orchestrator (`src/scraper/orchestrator.py`)

| Method | Purpose |
|--------|---------|
| `scrape_all()` | Main entry point for catalog scraping |
| `_deduplicate_and_track()` | Deduplicate parts, track compatibility, detect changes |
| `_content_hash()` | MD5 hash of part content for change detection |
| `_get_hierarchy_fingerprint()` | MD5 hash of hierarchy for change detection |
| `_save_checkpoint()` / `_load_checkpoint()` | Checkpoint persistence |
| `export_data()` | Export parts and compatibility to JSON |

### Fetcher (`src/scraper/fetcher.py`)

| Feature | Implementation |
|---------|---------------|
| Rate limiting | 1-3 second random delay between requests |
| Retry | Exponential backoff (3 attempts) |
| Rendering | Playwright for JS-rendered pages |
| Fallback | httpx for simple API/AJAX calls |
| User-agent | Descriptive with contact info |

### Image Processor (`src/scraper/image_processor.py`)

| Feature | Implementation |
|---------|---------------|
| Download | Fetches gallery images from S3 URLs |
| Conversion | Converts to AVIF (quality 85) |
| Naming | `CSF-{sku}_{index}.avif` |
| Dedup | Skips already-downloaded images |

---

## Anti-Patterns to Avoid

### Do NOT create multiple scripts for the same task

```
# BAD                          # GOOD
enrich_images.py               enrich_details.py
enrich_specs.py                (extracts ALL detail page data)
enrich_interchange.py
```

### Do NOT duplicate parser logic

```python
# BAD — parsing HTML directly in a script
soup = BeautifulSoup(html, "html.parser")
images = soup.find_all("img")

# GOOD — use the parser's public API
detail_data = parser.extract_detail_page_data(soup, sku)
images = detail_data["additional_images"]
```

### Do NOT call private parser methods from scripts

```python
# BAD
images = parser._extract_gallery_images(soup)

# GOOD
detail_data = parser.extract_detail_page_data(soup, sku)
images = detail_data["additional_images"]
```

---

## Refactoring Checklist

Before adding new functionality:

- [ ] Does this duplicate existing functionality?
- [ ] Can I extend an existing script instead of creating a new one?
- [ ] Am I calling the correct single source of truth?
- [ ] Does this violate DRY principles?
- [ ] Have I updated this architecture document?

---

## Summary

| Task | Single Source | Never Use |
|------|-------------|-----------|
| Catalog scraping | `scrape_catalog.py` | Direct parser calls |
| Detail enrichment | `enrich_details.py` | Separate image/spec scripts |
| Orchestration | `run_scrape.py` | Manual subprocess calls |
| Image extraction | `parser.extract_detail_page_data()` | `parser._extract_gallery_images()` |
| Spec extraction | `parser.extract_detail_page_data()` | Custom parsing logic |
| Change detection | `orchestrator._content_hash()` | Manual file diffing |

**Golden Rule:** One task, one script, one method. No exceptions.

---

**Last Updated**: 2026-03-04
