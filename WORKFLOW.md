# Complete End-to-End Workflow

## TL;DR

```bash
# Option A: Unified orchestrator (recommended)
python run_scrape.py --catalog --details

# Option B: Run phases separately
python scrape_catalog.py                # Phase 1: catalog + compatibility
python enrich_details.py                # Phase 2: descriptions, specs, images

# Import to WordPress
ddev wp csf-parts import exports/parts_complete.json
```

---

## What Gets Scraped

### Phase 1: Catalog Scraping (`scrape_catalog.py`)

Builds the full vehicle hierarchy and fetches every application page:

- Vehicle hierarchy (51 makes, 56+ years, all models)
- Basic part data: SKU, name, category, manufacturer, stock status
- Basic specifications
- Vehicle compatibility data

**Outputs:** `exports/parts.json` + `exports/compatibility.json`

### Phase 2: Detail Enrichment (`enrich_details.py`)

Fetches each part's detail page for complete product data:

- Full product descriptions
- Detailed specifications (~22 fields)
- Technical notes
- Interchange data (competitor part numbers)
- Gallery images (large images, converted to AVIF)

**Output:** `exports/parts_with_details.json`

### Phase 3: Auto-Merge (via `run_scrape.py`)

When using the unified orchestrator, compatibility data is automatically merged into the final output:

**Output:** `exports/parts_complete.json`

---

## Complete Data After Scraping

| Category | Details |
|----------|---------|
| **Parts** | 1,728 unique parts with complete information |
| **Vehicle Compatibility** | 51 makes, 56+ years, 32,500+ vehicle configurations |
| **Interchange Data** | Competitor part numbers and cross-references |
| **Images** | Gallery images converted to AVIF format |
| **Specifications** | ~22 detailed spec fields per part |

---

## Before You Start

### Copy AVIF Images to WordPress Plugin

The scraper saves images to `images/avif/`. Copy them to the WordPress plugin:

```bash
cp -r images/avif/* carpart-scraper-wp/public/images/avif/
```

This only needs to be done once (or when images change).

### Clear Existing Data (Optional)

For a completely fresh start:

```bash
# Clear WordPress database
ddev wp csf-parts clear --yes

# Delete scraper outputs
rm -rf exports/*
rm -rf images/avif/*
```

---

## Workflow Options

### Option A: Full Scrape with Unified Orchestrator (Recommended)

```bash
cd /Users/zach/PycharmProjects/carpart-scraper

# Run complete pipeline (catalog + details + auto-merge)
python run_scrape.py --catalog --details

# Copy images to WordPress plugin
cp -r images/avif/* carpart-scraper-wp/public/images/avif/

# Import to WordPress
ddev wp csf-parts import exports/parts_complete.json

# Verify
ddev wp csf-parts stats
```

### Option B: Run Phases Separately

```bash
# Phase 1: Catalog only
python scrape_catalog.py --output-dir exports/

# Phase 2: Detail enrichment (requires exports/parts.json)
python enrich_details.py

# Merge compatibility into enriched data
python merge_for_import.py

# Import
ddev wp csf-parts import exports/parts_complete.json
```

### Option C: Incremental Update

```bash
# Catalog with change detection (skips if unchanged)
python scrape_catalog.py --check-changes --incremental

# Enrich only new/changed parts (skips already-enriched)
python enrich_details.py

# Or force re-enrichment of everything
python enrich_details.py --force
```

### Option D: Target Specific SKUs

```bash
# Re-enrich specific parts
python enrich_details.py --skus CSF-3680,CSF-3981,CSF-10535

# Or from a file (one SKU per line)
python enrich_details.py --skus-file changed_skus.txt
```

### Option E: Filter by Make/Year

```bash
# Scrape only Nissan parts
python run_scrape.py --catalog --details --make Nissan

# Scrape only 2023 parts
python run_scrape.py --catalog --details --year 2023
```

---

## Resume After Interruption

If a scrape gets interrupted (Ctrl-C, network error, etc.), resume from the last checkpoint:

```bash
# Resume catalog scrape
python scrape_catalog.py --resume

# Detail enrichment automatically skips already-enriched parts
python enrich_details.py
```

Checkpoints are saved to `checkpoints/` every 10 applications.

---

## Verification

```bash
# Check WordPress statistics
ddev wp csf-parts stats

# Expected output:
# Total Parts: 1,728
# Vehicle Makes: 51

# Check a specific part
ddev wp db query "SELECT sku, name FROM wp_csf_parts WHERE sku = 'CSF-3680' LIMIT 1"

# Validate JSON
python -m json.tool exports/parts_complete.json > /dev/null && echo "Valid JSON"
```

---

## Troubleshooting

### Images Not Showing

```bash
# Check if images were copied to WordPress plugin
ls carpart-scraper-wp/public/images/avif/ | wc -l

# Manually update image URLs if needed
ddev wp csf-parts update-image-urls
```

### No Compatibility Data

```bash
# Make sure you used parts_complete.json (not parts.json)
# parts_complete.json includes merged compatibility data

# Verify compatibility in database
ddev wp db query "SELECT sku, compatibility FROM wp_csf_parts WHERE sku = 'CSF-3680'"
```

### Scrape Stopped Midway

```bash
# Resume from checkpoint
python scrape_catalog.py --resume

# Detail enrichment auto-skips completed parts
python enrich_details.py
```

### Import Failed

```bash
# Check file exists and is valid
ls -la exports/parts_complete.json
python -m json.tool exports/parts_complete.json > /dev/null
```

---

## Output Files

```
exports/
├── parts.json                # Phase 1: Basic catalog data
├── compatibility.json        # Phase 1: Vehicle fitment data
├── parts_with_details.json   # Phase 2: Enriched with detail page data
└── parts_complete.json       # Final merged data (use this for import)

images/
└── avif/
    ├── CSF-3680_0.avif
    ├── CSF-3680_1.avif
    └── ...

checkpoints/
├── checkpoint_all_*.json     # Resume points for catalog scrape
└── hierarchy_fingerprint_*.txt  # Change detection fingerprints
```

---

## Performance Estimates

| Phase | Duration | Notes |
|-------|----------|-------|
| Catalog scrape (full) | ~8-10 hours | 8,764 application pages at ~1-3s delay |
| Catalog scrape (incremental, no changes) | ~45 minutes | Hierarchy check only |
| Detail enrichment (full) | ~3-4 hours | 1,728 parts at ~7s/part |
| Detail enrichment (skip enriched) | Seconds | Only processes new parts |
| WordPress import | ~30 seconds | |
| **Total fresh scrape** | **~12-14 hours** | Run overnight |

---

## CLI Reference

### `run_scrape.py` (Unified Orchestrator)

```
--catalog          Run catalog scraping (hierarchy + applications)
--details          Run detail enrichment (descriptions, specs, images)
--make TEXT        Filter by make (catalog only)
--year INTEGER     Filter by year (catalog only)
--output-dir PATH  Output directory (default: exports/)
--skus TEXT        Target specific SKUs (details only)
--skus-file PATH   SKUs from file (details only)
--force            Force re-enrichment (details only)
--push             Push to WordPress via REST API after scraping
--wp-url TEXT      WordPress site URL
--wp-api-key TEXT  WordPress API key
```

### `scrape_catalog.py`

```
--make TEXT         Filter by make
--year INTEGER      Filter by year
--output-dir PATH   Output directory (default: exports/)
--incremental       Only process changes vs previous export
--check-changes     Check hierarchy fingerprint, skip if unchanged
--resume            Resume from latest checkpoint
--fetch-details     Also fetch detail pages during catalog scrape
```

### `enrich_details.py`

```
--skus TEXT        Target specific SKUs
--skus-file PATH   SKUs from file
--force            Force re-enrichment
```
