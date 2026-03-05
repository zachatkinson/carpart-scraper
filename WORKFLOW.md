# Complete End-to-End Workflow

## TL;DR

```bash
# Full scrape (catalog + details + merged export)
carpart scrape

# Scrape + streaming image sync to local WordPress (DDEV)
carpart scrape --sync-images --wp-url /path/to/wp-content/uploads

# Scrape + streaming sync to remote WordPress (GitHub Actions cron)
carpart scrape --sync-images --wp-url https://yoursite.com --wp-api-key KEY

# Catalog only (no detail pages)
carpart scrape --catalog-only

# Incremental (skip unchanged pages)
carpart scrape --incremental

# Import to WordPress
ddev wp csf-parts import exports/parts_complete.json
```

---

## What Gets Scraped

### Catalog (Steps 1-2)

Builds the full vehicle hierarchy and fetches every application page:

- Vehicle hierarchy (51 makes, 56+ years, all models)
- Basic part data: SKU, name, category, manufacturer, stock status
- Basic specifications
- Vehicle compatibility data

### Detail Enrichment (Step 3)

Fetches each part's detail page for complete product data:

- Full product descriptions
- Detailed specifications (~22 fields)
- Technical notes
- Interchange data (competitor part numbers)
- Gallery images (large images, converted to AVIF)

### Merged Export (Step 4)

Produces a single `parts_complete.json` with parts + inline vehicle compatibility.

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

### Sync AVIF Images to WordPress

The scraper saves images to `images/avif/` as a staging area. Use `--sync-images` to enable **streaming sync** — images are synced and deleted per-SKU during detail enrichment, keeping disk usage minimal:

```bash
# Streaming sync during scrape (images synced + deleted as each SKU completes)
carpart scrape --sync-images --wp-url /path/to/wp-content/uploads

# Remote WordPress (production / GitHub Actions cron)
carpart scrape --sync-images --wp-url https://yoursite.com --wp-api-key YOUR_KEY

# Standalone batch sync (for ad-hoc use after a previous scrape)
carpart sync-images --wp-url /path/to/wp-content/uploads

# Remote standalone batch sync
carpart sync-images --wp-url https://yoursite.com --wp-api-key YOUR_KEY
```

**Streaming vs Batch:**
- **Streaming** (`--sync-images` during `scrape`): Images are synced and deleted per-SKU during step 3. Disk stays nearly empty.
- **Batch** (`carpart sync-images`): Syncs all unsynced images at once. Useful for retrying failed syncs.

### State Persistence (Remote / CI Mode)

When `--wp-url` is an HTTP(S) URL and `--wp-api-key` is provided, state files are automatically persisted to WordPress:

- **Before scrape**: pulls `checkpoints/etags.json` and `images/manifest.json` from WordPress
- **After scrape** (in `finally` block): pushes both files back to WordPress

This enables ephemeral CI runners (e.g., GitHub Actions cron) to benefit from incremental scraping and ETag-based image dedup across runs.

For local mode (`--wp-url /path/...`), state files persist on disk automatically — no sync needed.

**Legacy method** (still works but not recommended):
```bash
cp -r images/avif/* carpart-scraper-wp/public/images/avif/
```

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

### Option A: Full Scrape (Recommended)

```bash
cd /Users/zach/PycharmProjects/carpart-scraper

# Run complete pipeline with automatic image sync
carpart scrape --sync-images --wp-url /path/to/wp-content/uploads

# Import to WordPress
ddev wp csf-parts import exports/parts_complete.json

# Verify
ddev wp csf-parts stats
```

### Option B: Catalog Only

```bash
# Catalog only (no detail pages, no merged export)
carpart scrape --catalog-only

# Later, run full scrape to get details
carpart scrape
```

### Option C: Incremental Update

```bash
# Only re-scrape changed application pages (via ETag hashing)
carpart scrape --incremental

# Import updated data
ddev wp csf-parts import exports/parts_complete.json
```

### Option D: Filter by Make/Year

```bash
# Scrape only Honda parts
carpart scrape --make Honda

# Scrape only 2025 parts
carpart scrape --year 2025

# Combine filters
carpart scrape --make Honda --year 2025
```

### Option E: Target Specific SKUs (Standalone Scripts)

```bash
# Re-enrich specific parts using standalone script
python enrich_details.py --skus CSF-3680,CSF-3981,CSF-10535

# Or from a file (one SKU per line)
python enrich_details.py --skus-file changed_skus.txt
```

---

## Resume After Interruption

If a scrape gets interrupted (Ctrl-C, network error, etc.), resume from the last checkpoint:

```bash
# Resume from latest checkpoint
carpart scrape --resume
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
# Run image sync to push any unsynced images
carpart sync-images --wp-url /path/to/wp-content/uploads --dry-run

# Actually sync
carpart sync-images --wp-url /path/to/wp-content/uploads

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
carpart scrape --resume
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
├── parts.json                # Basic catalog data (SKU, name, price, specs)
├── compatibility.json        # Vehicle fitment data
└── parts_complete.json       # Merged data — parts + inline compatibility (use this for import)

images/
├── manifest.json             # Tracks source hashes, ETags, and sync status
└── avif/                     # Staging area (streaming sync keeps this nearly empty)
    ├── CSF-3680_0.avif       # Only present during processing if streaming sync is off
    └── ...

checkpoints/
├── etags.json                # Application page content hashes (persisted to WP in remote mode)
└── checkpoint_all_*.json     # Resume points for catalog scrape
```

---

## Performance Estimates

| Scenario | Duration | Notes |
|----------|----------|-------|
| Full scrape (catalog + details) | ~12-14 hours | 8,764 pages at 1-3s delay + 1,728 detail pages |
| Incremental (no changes) | Minutes | ETag comparison only, skips unchanged pages |
| Incremental (some changes) | Varies | Only re-scrapes changed application pages |
| Catalog only | ~8-10 hours | 8,764 application pages at 1-3s delay |
| WordPress import | ~30 seconds | |

---

## CLI Reference

### `carpart scrape`

```
--make TEXT         Filter by vehicle make (e.g., 'Honda', 'Toyota')
--year INTEGER      Filter by model year (e.g., 2025, 2024)
--output-dir PATH   Export directory path (default: exports/)
--catalog-only      Only scrape catalog data (skip detail pages and merged export)
--incremental       Skip unchanged pages via ETag content hashing
--resume            Resume from the latest checkpoint
--sync-images       Sync AVIF images to WordPress after scraping
--wp-url TEXT       WordPress URL or local uploads path (env: CSF_WP_URL)
--wp-api-key TEXT   WordPress API key for remote sync (env: CSF_WP_API_KEY)
```

### `carpart sync-images`

Standalone command for syncing AVIF images outside the scrape pipeline.

```
--wp-url TEXT       WordPress URL or local uploads path (required, env: CSF_WP_URL)
--wp-api-key TEXT   WordPress API key (env: CSF_WP_API_KEY)
--images-dir PATH   Image directory (default: images)
--no-cleanup        Skip deleting synced files
--dry-run           Show what would be synced
```

### Standalone Scripts (Advanced)

These scripts are kept for targeted operations but are not needed for normal workflows:

```
scrape_catalog.py             Standalone catalog scraper with extra options
enrich_details.py             Re-enrich specific SKUs (--skus, --force)
merge_for_import.py           Manually merge compatibility into parts
```

---

**Last Updated**: 2026-03-05
