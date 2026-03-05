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

### 1. ETag-Based Incremental Scraping (Recommended Daily)

Only re-scrape application pages whose content has changed:

```bash
carpart scrape --incremental
```

**How it works:**
- Each application page response is hashed and stored
- On subsequent runs, the hash is compared to the stored value
- If unchanged: **skip that page entirely**
- If changed: re-scrape and process the page

**Detects ALL changes:**
- New parts added to any application
- Parts removed from an application
- Price changes, spec changes, any field changes
- New vehicles/applications added

### 2. Auto-Incremental Mode

The orchestrator auto-promotes to incremental mode when previous ETag data or exports exist. This means after your first full scrape, every subsequent `carpart scrape` automatically runs incrementally:

```bash
# First run: full scrape (no previous data)
carpart scrape

# Second run onwards: auto-incremental
carpart scrape
```

### 3. Detail Enrichment (New Parts Only)

When running the full pipeline (without `--catalog-only`), detail enrichment automatically skips already-enriched parts. Only new or changed parts get their detail pages fetched.

### 4. Full Deep Scrape

Force a full re-scrape of all application pages and detail pages:

```bash
carpart scrape --output-dir exports/
```

To force a completely fresh scrape (ignoring all previous data), clear the ETag store:

```bash
rm -f exports/etag_store.json
carpart scrape
```

**When to use:**
- Weekly maintenance
- After known price updates
- Quality assurance checks

### 5. SKU-Specific Updates

Target specific parts for quick fixes using the standalone script:

```bash
python enrich_details.py --skus CSF-3680,CSF-3981,CSF-10535
python enrich_details.py --skus-file changed_skus.txt
```

---

## Production Schedule

### Recommended Schedule

**Daily (Automated via cron):**

```bash
# 2:00 AM — Incremental scrape (only re-scrapes changed pages)
0 2 * * * cd /path/to/scraper && \
    carpart scrape --incremental \
    >> /var/log/scraper/daily.log 2>&1
```

**Weekly (Automated via cron):**

```bash
# Sunday 1:00 AM — Full scrape (re-fetches everything)
0 1 * * 0 cd /path/to/scraper && \
    rm -f exports/etag_store.json && \
    carpart scrape \
    >> /var/log/scraper/weekly.log 2>&1
```

**Monthly (Manual):**

```bash
# Full audit
carpart scrape
```

### Performance Expectations

| Scenario | Duration | Notes |
|----------|----------|-------|
| No changes detected | Minutes | ETag comparison only |
| 10 new parts | ~10 min | Changed pages + 10 detail pages |
| 100 new parts | ~20 min | Changed pages + 100 detail pages |
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
# Re-scrape all Honda applications + details
carpart scrape --make Honda
ddev wp csf-parts import exports/parts_complete.json
```

### Corrupted data needs full rescrape

```bash
rm -f exports/etag_store.json
carpart scrape
ddev wp csf-parts import exports/parts_complete.json
```

### Scrape interrupted midway

```bash
carpart scrape --resume
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

| Data Type              | Daily Incremental | Weekly Full Scrape | SKU-Specific |
|------------------------|-------------------|-------------------|--------------|
| New parts              | Yes               | Yes               | Yes          |
| Vehicle compatibility  | Yes               | Yes               | N/A          |
| Part prices            | Yes (if changed)  | Yes (all)         | Yes          |
| Part descriptions      | Yes (if changed)  | Yes (all)         | Yes          |
| Part images            | Yes (if changed)  | Yes (all)         | Yes          |
| Interchange data       | Yes (if changed)  | Yes (all)         | Yes          |

---

## Monitoring

### Check Scrape Success

```bash
# View daily log
tail -f /var/log/scraper/daily.log

# Check for errors
grep -i "error\|failed" /var/log/scraper/daily.log

# Count new parts
grep "new_parts" /var/log/scraper/daily.log | tail -1
```

### Monitor JSON Files

```bash
# Check export file timestamps
ls -lh exports/parts.json exports/parts_complete.json

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

- Run daily incremental scrapes with `carpart scrape --incremental`
- Run weekly full scrapes (clear ETag store first) to catch all changes
- Use `--skus` for emergency fixes to specific parts
- Monitor logs for errors and unexpected changes
- Keep the `checkpoints/` directory intact (enables resume)
- Test updates on staging before production import

### Don't

- Don't run full scrapes more than once per week (unnecessary server load)
- Don't skip daily incremental checks (you'll miss new parts)
- Don't delete `checkpoints/` (breaks resume capability)
- Don't run multiple scrapers concurrently (race conditions)

---

## Troubleshooting

### "Scrape stopped midway"

```bash
carpart scrape --resume
```

### "Need to update just 3 parts quickly"

```bash
python enrich_details.py --skus CSF-3680,CSF-3981,CSF-10535 --force
```

### "Price updated on website but not in WordPress"

Prices are detected on the next incremental scrape if the application page content changed:

```bash
# Quick fix for specific SKUs
python enrich_details.py --skus CSF-3680 --force

# Or run incremental scrape
carpart scrape --incremental
```

### "Want a completely fresh start"

```bash
rm -rf exports/*
rm -rf checkpoints/*
rm -rf images/avif/*
rm -f images/manifest.json
carpart scrape
```

---

## Summary

| Frequency | Command | Duration |
|-----------|---------|----------|
| **Daily** | `carpart scrape --incremental` | Minutes (if no changes) |
| **Weekly** | `rm -f exports/etag_store.json && carpart scrape` | ~12-14 hrs |
| **Emergency** | `python enrich_details.py --skus CSF-XXXX --force` | ~7 sec/SKU |

The combination of daily incremental + weekly full scrapes provides:
- Fast detection of all changes (daily, via ETag hashing)
- Comprehensive full refresh (weekly)
- Minimal server load (intelligent change detection)
- Emergency fix capability (SKU-specific)

---

**Last Updated**: 2026-03-05
