# Production Update Strategy

How to keep your WordPress catalog in sync with the CSF MyCarParts website.

## Table of Contents

- [Update Mechanisms](#update-mechanisms)
- [Production Schedule](#production-schedule)
- [Emergency Updates](#emergency-updates)
- [How Updates Work](#how-updates-work)
- [Monitoring](#monitoring)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

---

## Update Mechanisms

### 1. Change Detection (MD5 Fingerprinting)

Check if the catalog hierarchy changed before scraping:

```bash
python scrape_catalog.py --check-changes
```

**How it works:**
- MD5 hash of: makes, years, models, application IDs
- Compares with previous run's fingerprint
- If unchanged: **skips entire scrape**
- If changed: proceeds with scrape

**Detects:**
- New vehicles added
- New compatibility added
- Vehicles removed

**Does NOT detect:**
- Part detail changes (price, description, images)

### 2. Incremental Scraping

Only process changed parts by comparing content hashes:

```bash
python scrape_catalog.py --incremental
```

**How it works:**
- Loads previous `parts.json` and computes MD5 hash per part
- During scraping, compares each part's hash to the baseline
- Only flags parts with changed content (SKU, name, price, specs, etc.)
- Excludes volatile fields (`scraped_at`) and enrichment fields from hash

### 3. Detail Enrichment (New Parts Only)

Enrich only parts that haven't been enriched yet:

```bash
python enrich_details.py
```

Already-enriched parts are skipped automatically. Use `--force` to re-enrich everything.

### 4. Full Deep Scrape

Re-fetch all application pages and detail pages:

```bash
python scrape_catalog.py --output-dir exports/
python enrich_details.py --force
```

**When to use:**
- Weekly maintenance
- After known price updates
- Quality assurance checks

### 5. SKU-Specific Updates

Target specific parts for quick fixes:

```bash
python enrich_details.py --skus CSF-3680,CSF-3981,CSF-10535
python enrich_details.py --skus-file changed_skus.txt
```

---

## Production Schedule

### Recommended Schedule

**Daily (Automated via cron):**

```bash
# 2:00 AM — Quick catalog check + enrich new parts (~45 min if unchanged)
0 2 * * * cd /path/to/scraper && \
    python scrape_catalog.py --check-changes --incremental \
    >> /var/log/scraper/daily.log 2>&1
```

**Weekly (Automated via cron):**

```bash
# Sunday 1:00 AM — Full catalog scrape + re-enrich all (~12-14 hours)
0 1 * * 0 cd /path/to/scraper && \
    python scrape_catalog.py --output-dir exports/ && \
    python enrich_details.py --force \
    >> /var/log/scraper/weekly.log 2>&1
```

**Monthly (Manual):**

```bash
# Full audit with verbose logging
python scrape_catalog.py --output-dir exports/ --verbose
python enrich_details.py --force --verbose
```

### Performance Expectations

| Scenario | Duration | Notes |
|----------|----------|-------|
| No changes detected | ~45 min | Hierarchy check only |
| 10 new parts | ~50 min | Hierarchy + 10 detail pages |
| 100 new parts | ~60 min | Hierarchy + 100 detail pages |
| Full catalog scrape | ~8-10 hours | 8,764 application pages |
| Full detail enrichment | ~3-4 hours | 1,728 detail pages |
| Specific 5 SKUs | ~35 sec | 5 detail pages |

---

## Emergency Updates

### Image failed for specific part

```bash
python enrich_details.py --skus CSF-3680,CSF-3981 --force
```

### Price update for specific make

```bash
# Re-scrape all Honda applications + re-enrich
python scrape_catalog.py --make Honda
python enrich_details.py --force
```

### Corrupted data needs full rescrape

```bash
python scrape_catalog.py --output-dir exports/
python enrich_details.py --force
python merge_for_import.py
ddev wp csf-parts import exports/parts_complete.json
```

### Scrape interrupted midway

```bash
python scrape_catalog.py --resume
python enrich_details.py
```

---

## How Updates Work

### Last-Write-Wins Strategy

The scraper always uses the latest data from the website:

```
Day 1:
  CSF-3680:
    price: $299.99
    description: "High performance radiator"

Day 2 (price updated on website):
  CSF-3680:
    price: $319.99          <-- UPDATED
    description: "High performance radiator"

WordPress import overwrites existing parts with same SKU.
```

### What Gets Updated Per Strategy

| Data Type              | Daily Check | Weekly Deep Scrape | SKU-Specific |
|------------------------|-------------|-------------------|--------------|
| New parts              | Yes         | Yes               | Yes          |
| Vehicle compatibility  | Yes (if changed) | Yes          | N/A          |
| Part prices            | No (new only) | Yes (all)       | Yes          |
| Part descriptions      | No (new only) | Yes (all)       | Yes          |
| Part images            | No (new only) | Yes (all)       | Yes          |
| Interchange data       | No (new only) | Yes (all)       | Yes          |

---

## Monitoring

### Check Scrape Success

```bash
# View daily log
tail -f /var/log/scraper/daily.log

# Check if catalog changed
grep "catalog_unchanged" /var/log/scraper/daily.log

# Check for errors
grep -i "error\|failed" /var/log/scraper/daily.log

# Count new parts
grep "new_parts" /var/log/scraper/daily.log | tail -1
```

### Monitor JSON Files

```bash
# Check export file timestamps
ls -lh exports/parts.json exports/parts_with_details.json

# Count parts in export
python3 -c "import json; d=json.load(open('exports/parts.json')); print(len(d['parts']))"

# Find specific SKU
python3 -c "
import json
parts = json.load(open('exports/parts.json'))['parts']
match = [p for p in parts if p['sku'] == 'CSF-3680']
print(json.dumps(match[0], indent=2) if match else 'Not found')
"
```

### Alert Thresholds

| Condition | Severity | Action |
|-----------|----------|--------|
| Scrape failed (exit code != 0) | Critical | Investigate logs |
| No exports updated in >24 hours | Warning | Check cron job |
| Parts count decreased | Critical | Check for data loss |
| Scrape took >15 hours | Warning | Check for rate limiting |
| >100 new parts in single day | Info | Verify legitimacy |

### Health Check Script

```bash
#!/bin/bash
# health_check.sh

LAST_EXPORT=$(stat -f %m exports/parts.json)
NOW=$(date +%s)
AGE=$((NOW - LAST_EXPORT))

if [ $AGE -gt 86400 ]; then
    echo "WARNING: parts.json not updated in >24 hours"
    exit 1
fi

PARTS_COUNT=$(python3 -c "import json; print(len(json.load(open('exports/parts.json'))['parts']))")

if [ "$PARTS_COUNT" -lt 1700 ]; then
    echo "ERROR: Only $PARTS_COUNT parts (expected ~1,728)"
    exit 1
fi

echo "OK: $PARTS_COUNT parts, last updated $(($AGE / 3600)) hours ago"
```

---

## Best Practices

### Do

- Run daily checks with `--check-changes` to detect catalog updates
- Run weekly deep scrapes with `--force` enrichment to catch all changes
- Use `--skus` for emergency fixes to specific parts
- Monitor logs for errors and unexpected changes
- Keep the `checkpoints/` directory intact (enables resume)
- Test updates on staging before production import

### Don't

- Don't run full scrapes more than once per week (unnecessary server load)
- Don't skip nightly checks (you'll miss new parts)
- Don't delete `checkpoints/` (breaks resume capability)
- Don't run multiple scrapers concurrently (race conditions)
- Don't ignore "no changes detected" — that's a good result

---

## Troubleshooting

### "No changes detected but I know there are updates"

```bash
# Clear fingerprint cache and force rescrape
rm checkpoints/hierarchy_fingerprint_*.txt
python scrape_catalog.py --output-dir exports/
```

### "Scrape stopped midway"

```bash
python scrape_catalog.py --resume
```

### "Need to update just 3 parts quickly"

```bash
python enrich_details.py --skus CSF-3680,CSF-3981,CSF-10535 --force
```

### "Price updated on website but not in WordPress"

Prices are only updated during:
- Weekly deep scrapes (full enrichment with `--force`)
- SKU-specific updates

```bash
# Quick fix for specific SKUs
python enrich_details.py --skus CSF-3680 --force

# Or wait for weekly deep scrape
```

---

## Summary

| Frequency | Command | Duration |
|-----------|---------|----------|
| **Daily** | `python scrape_catalog.py --check-changes --incremental` | ~45 min |
| **Weekly** | `python scrape_catalog.py && python enrich_details.py --force` | ~12-14 hrs |
| **Emergency** | `python enrich_details.py --skus CSF-XXXX --force` | ~7 sec/SKU |

The combination of daily checks + weekly deep scrapes provides:
- Fast detection of new parts (daily)
- Comprehensive updates of existing parts (weekly)
- Minimal server load (intelligent change detection)
- Emergency fix capability (SKU-specific)

---

**Last Updated**: 2026-03-04
