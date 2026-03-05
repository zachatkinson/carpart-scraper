# CSF MyCarParts Scraper - Architecture

## DRY Principle: Single Source of Truth

This document defines the **single source of truth** for each scraping operation to maintain DRY (Don't Repeat Yourself) principles.

---

## Pipeline Overview

```
                        carpart scrape
            (single command, calls orchestrator directly)

 ┌──────────────────────────────────────────────────────────────────────────────┐
 │  [State Pull]          ScraperOrchestrator              [State Push]         │
 │  etags.json ←─WP                                        etags.json ─→WP     │
 │  manifest.json←WP                                       manifest.json─→WP   │
 │                                                                              │
 │  1. Hierarchy    2. Application   3. Detail + Stream  4. Export              │
 │     (AJAX)          Scraping         Enrichment + Sync                       │
 │  ┌────────────┐  ┌─────────────┐  ┌────────────────┐  ┌─────────┐          │
 │  │Makes/Years │  │ Fetch pages │  │Descriptions    │  │parts.   │          │
 │  │Models/Apps │─→│ Extract     │─→│Specs, images   │─→│json     │          │
 │  │via AJAX    │  │ Dedup+track │  │AVIF+ETag       │  │compat.  │          │
 │  │            │  │ ETag hashing│  │Stream sync/del │  │complete │          │
 │  └────────────┘  └─────────────┘  └────────────────┘  └─────────┘          │
 └──────────────────────────────────────────────────────────────────────────────┘
```

`carpart scrape` invokes the orchestrator directly — no subprocess delegation.

- `--catalog-only` stops after step 2 (skips detail enrichment and merged export)
- Default (no flag) runs steps 1-4, producing `parts_complete.json`
- `--sync-images` enables streaming sync: images are synced and deleted per-SKU during step 3
- Remote mode (`--wp-url https://...`) auto-pulls state before scraping and pushes after

---

## Step 1: Hierarchy Enumeration (AJAX)

**Single Source:** `src/scraper/orchestrator.py` (`_build_hierarchy`)

**Responsibilities:**
- Enumerate makes, years, models, and application IDs via AJAX endpoints
- Build the full vehicle hierarchy tree

---

## Step 2: Application Scraping

**Single Source:** `src/scraper/orchestrator.py` (`_scrape_applications`)

**Responsibilities:**
- Fetch application pages for each vehicle configuration
- Extract basic part data: SKU, name, category, manufacturer, stock status, specs
- Deduplicate parts across application pages
- Track vehicle compatibility per part
- Save checkpoints for resume capability
- ETag-based content hashing for incremental mode

**Output (via export):**
- `exports/parts.json` — Part catalog with basic info
- `exports/compatibility.json` — Vehicle compatibility data

---

## Step 3: Detail Page Enrichment

**Single Source:** `src/scraper/orchestrator.py` (`_fetch_detail_pages`)

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

---

## Step 4: Export

**Single Source:** `src/exporters/json_exporter.py`

**Responsibilities:**
- `export_data()` — Write `parts.json` + `compatibility.json`
- `export_complete()` — Write merged `parts_complete.json` with parts + inline compatibility

**Output:**
- `exports/parts.json` — Basic catalog data
- `exports/compatibility.json` — Vehicle fitment data
- `exports/parts_complete.json` — Final merged data for WordPress import

---

## Change Detection

### ETag-Based Content Hashing

**File:** `src/scraper/etag_store.py`

Per-application-page content hashing that detects ALL changes:

- New parts added to an application
- Parts removed from an application
- Price changes, spec changes, any field changes

```bash
# Auto-detects previous data and runs incrementally
carpart scrape

# Explicit incremental mode
carpart scrape --incremental
```

**How it works:**
1. Each application page response is hashed
2. On subsequent runs, the hash is compared to the stored value
3. If unchanged: **skip that page entirely**
4. If changed: re-scrape and process the page

The orchestrator auto-promotes to incremental mode when previous ETag data or exports exist.

### Part Content Hashing

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

Used during deduplication to flag which specific parts changed between runs.

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
carpart scrape --resume
```

Failed applications are **not** added to `processed_application_ids`, so they are automatically retried on resume.

---

## Core Modules

### Parser (`src/scraper/parser.py`)

| Method | Purpose | Called By |
|--------|---------|-----------|
| `extract_all_parts_from_application_page()` | Extract all parts from an application page | `orchestrator.py` |
| `extract_detail_page_data()` | Extract complete detail page data | `orchestrator.py` |
| `_extract_vehicle_qualifiers()` | Parse engine, aspiration, transmission from HTML table | Internal |
| `_extract_gallery_images()` | Extract large S3 images from detail page | Internal |
| `_extract_clean_engine_spec()` | Clean engine strings, remove non-engine data | Internal |

### Orchestrator (`src/scraper/orchestrator.py`)

| Method | Purpose |
|--------|---------|
| `scrape_all()` | Main entry point — runs full pipeline |
| `_deduplicate_and_track()` | Deduplicate parts, track compatibility, detect changes |
| `_content_hash()` | MD5 hash of part content for change detection |
| `_save_checkpoint()` / `_load_checkpoint()` | Checkpoint persistence |
| `export_data()` | Export parts and compatibility to JSON |
| `export_complete()` | Export merged parts + compatibility to single JSON |

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
| ETag conditionals | Sends `If-None-Match` header; skips download on 304 Not Modified |
| Conversion | Converts to AVIF (quality 85) |
| Naming | `CSF-{sku}_{index}.avif` |
| Dedup | Content hash + ETag-based staleness detection |
| Manifest | `images/manifest.json` tracks source_hash, etag, and sync status |
| Sync tracking | `mark_synced()`, `get_unsynced_files()`, `get_synced_files()` |

### Image Syncer (`src/scraper/image_syncer.py`)

| Feature | Implementation |
|---------|---------------|
| Strategy pattern | `ImageSyncStrategy` ABC with two backends |
| Local sync | `LocalFileSyncer` — copies AVIFs to WordPress uploads directory |
| Remote sync | `RemoteAPISyncer` — uploads via `POST /wp-json/csf/v1/images/upload` |
| Batch sync | `ImageSyncer.sync()` — syncs all unsynced files at once |
| Streaming sync | `ImageSyncer.sync_and_cleanup_for_sku()` — syncs per-SKU during detail enrichment |
| Cumulative tracking | `cumulative_result` attribute aggregates totals across streaming calls |
| Cleanup | Streaming: deletes per-SKU after sync. Batch: `cleanup()` for synced=True files |

### State Syncer (`src/scraper/state_syncer.py`)

| Feature | Implementation |
|---------|---------------|
| Purpose | Persist state files across ephemeral CI runs |
| Pull | `StateSyncer.pull()` — downloads etags.json/manifest.json from WordPress |
| Push | `StateSyncer.push()` — uploads state files to WordPress |
| Endpoint | `GET/POST /wp-json/csf/v1/scraper-state/{key}` |
| Key allowlist | Only `etags` and `manifest` keys are permitted |
| Auto-trigger | Activated when `--wp-url` is an HTTP URL with `--wp-api-key` |

### ETag Store (`src/scraper/etag_store.py`)

| Feature | Implementation |
|---------|---------------|
| Storage | JSON file mapping URLs to content hashes |
| Comparison | Compares current page hash to stored hash |
| Scope | Per-application-page granularity |

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
- [ ] Can I extend an existing module instead of creating a new one?
- [ ] Am I calling the correct single source of truth?
- [ ] Does this violate DRY principles?
- [ ] Have I updated this architecture document?

---

## Summary

| Task | Single Source | Never Use |
|------|-------------|-----------|
| Full pipeline | `carpart scrape` (CLI) | Subprocess chains |
| Catalog scraping | `ScraperOrchestrator.scrape_all()` | Direct parser calls |
| Detail enrichment | `ScraperOrchestrator._fetch_detail_pages()` | Separate image/spec scripts |
| Merged export | `JSONExporter.export_complete()` | Manual merge scripts |
| Image extraction | `parser.extract_detail_page_data()` | `parser._extract_gallery_images()` |
| Spec extraction | `parser.extract_detail_page_data()` | Custom parsing logic |
| Change detection | ETag store + `_content_hash()` | Manual file diffing |
| Streaming image sync | `ImageSyncer.sync_and_cleanup_for_sku()` via orchestrator | Batch-at-end sync |
| Batch image sync | `ImageSyncer.sync()` + `cleanup()` | Manual `cp -r` |
| Standalone image sync | `carpart sync-images` | Manual file copying |
| State persistence | `StateSyncer.pull()` / `push()` | Manual file management |

**Golden Rule:** One task, one module, one method. No exceptions.

---

**Last Updated**: 2026-03-05
