# CSF MyCarParts - Scraping Strategy Document

**Version**: 1.1
**Date**: 2025-10-27
**Status**: Prototype Validated
**Based on**: RECONNAISSANCE.md findings + Prototype results

---

## Table of Contents

- [Executive Summary](#executive-summary)
- [Scraping Approach](#scraping-approach)
- [Request Volume Estimation](#request-volume-estimation)
- [Data Flow](#data-flow)
- [Deduplication Strategy](#deduplication-strategy)
- [Prototype Validation](#prototype-validation)
- [Rate Limiting & Respectful Scraping](#rate-limiting--respectful-scraping)
- [Error Handling & Resume Strategy](#error-handling--resume-strategy)
- [Data Storage Strategy](#data-storage-strategy)
- [Export Strategy](#export-strategy)
- [Timeline & Scheduling](#timeline--scheduling)
- [Success Metrics](#success-metrics)

---

## Executive Summary

### Goal
Extract **all automotive parts data** from csf.mycarparts.com including:
- Part details (SKU, name, category, specs, images)
- Vehicle compatibility (which parts fit which vehicles)
- Technical specifications and interchange numbers

### Strategy
Use **hierarchical enumeration** through the vehicle selection flow:
```
Make (51) → Year (~30-40 each) → Model (~5-15 each) → Application Page (all parts)
```

### Key Constraints
- **No pricing data** available (outside scope)
- **No stock status** available (info catalog only)
- **No bulk export endpoint** (must enumerate through hierarchy)
- **AJAX responses return JavaScript**, not JSON (need special parser)

### Estimated Scope
- **~50,000-75,000 total HTTP requests**
- **~1,500-2,000 unique application pages**
- **Estimated 500-1,000 unique parts** (with significant overlap across vehicles)
- **~24-36 hours runtime** with 1-3 second delays

---

## Scraping Approach

### Option 1: Hierarchical Enumeration (RECOMMENDED)

**Flow**:
```
1. Fetch all 51 makes (hardcoded in HTML)
   ↓
2. For each make:
   GET /get_year_by_make/[MAKE_ID]
   → Parse JavaScript response to extract years
   ↓
3. For each year:
   GET /get_model_by_make_year/[YEAR_ID]
   → Parse JavaScript response to extract models
   ↓
4. For each model:
   Navigate to /applications/[APPLICATION_ID]
   → Parse HTML to extract all parts for this vehicle
   ↓
5. For each unique part (deduped by SKU):
   GET /items/[PART_NUMBER]
   → Parse HTML to extract full specifications
```

**Advantages**:
✅ Comprehensive - Gets all parts
✅ Respectful - Follows natural navigation flow
✅ Validates data - Ensures vehicle compatibility is correct
✅ Deduplication happens naturally (same SKU appears multiple times)

**Disadvantages**:
⚠️ Many requests (~50k-75k)
⚠️ Long runtime (~24-36 hours with delays)
⚠️ Must parse JavaScript AJAX responses

---

### Option 2: Direct SKU Enumeration (NOT RECOMMENDED)

**Flow**:
```
1. Try sequential SKU patterns:
   /items/1, /items/2, /items/3, ... /items/9999

2. Check if page exists (200 vs 404)

3. Extract part data from existing pages
```

**Advantages**:
✅ Fast - No need to traverse hierarchy
✅ Simple - Direct URL construction

**Disadvantages**:
❌ Aggressive - Looks like abuse
❌ Unknown SKU range - CSF uses 3-4 digit numbers (3951, 3985) but range is unknown
❌ Missing compatibility data - No vehicle mapping
❌ May miss parts - If SKUs aren't sequential

**Verdict**: ❌ **Do NOT use this approach**

---

### Option 3: Hybrid Approach (ALTERNATIVE)

**Flow**:
```
1. Use hierarchical enumeration to discover all unique SKUs
   → Build Set of all SKU numbers
   → Extract vehicle compatibility

2. Deduplicate SKUs

3. Fetch part detail pages only for unique SKUs
   → Reduces detail page fetches from ~50k to ~500-1k
```

**Advantages**:
✅ Efficient - Only fetch detail pages once per unique part
✅ Complete compatibility data
✅ Respectful - Still follows navigation flow

**Disadvantages**:
⚠️ Two-phase approach (more complex)

**Verdict**: ✅ **This is our chosen approach**

---

## Request Volume Estimation

### Phase 1: Hierarchy Enumeration

| Step | Count | Requests Each | Total Requests | Notes |
|------|-------|---------------|----------------|-------|
| **Makes** | 51 | 0 | 0 | Hardcoded in HTML |
| **Years per Make** | 51 | 1 | **51** | GET /get_year_by_make/[ID] |
| **Models per Year** | ~1,530* | 1 | **~1,530** | GET /get_model_by_make_year/[ID] |
| **Application Pages** | ~1,530 | 1 | **~1,530** | GET /applications/[ID] |

*Estimation: 51 makes × 30 avg years = 1,530 year/make combinations

**Phase 1 Total**: ~3,111 requests

### Phase 2: Part Detail Pages

| Step | Count | Requests Each | Total Requests |
|------|-------|---------------|----------------|
| **Unique Parts** | ~500-1,000* | 1 | **~500-1,000** |

*Estimation based on typical automotive parts catalogs

**Phase 2 Total**: ~500-1,000 requests

### Grand Total

- **Minimum**: ~3,611 requests
- **Maximum**: ~4,111 requests
- **Average**: ~3,861 requests

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    PHASE 1: Hierarchy Enumeration            │
└─────────────────────────────────────────────────────────────┘

1. Load 51 Makes (from HTML or JSON file)
   ↓
2. For each Make:
   │
   ├─→ Fetch /get_year_by_make/[MAKE_ID]
   │   ├─→ Parse JavaScript response
   │   ├─→ Extract years + year_ids
   │   └─→ Save checkpoint: makes_years.json
   │
   ├─→ For each Year:
   │   │
   │   ├─→ Fetch /get_model_by_make_year/[YEAR_ID]
   │   │   ├─→ Parse JavaScript response
   │   │   ├─→ Extract models + application_ids
   │   │   └─→ Save checkpoint: make_year_models.json
   │   │
   │   └─→ For each Model:
   │       │
   │       ├─→ Fetch /applications/[APPLICATION_ID]
   │       │   ├─→ Parse HTML for all parts
   │       │   ├─→ Extract: SKU, name, category, basic specs, image
   │       │   ├─→ Store part → vehicle mapping
   │       │   └─→ Add SKU to unique_parts Set
   │       │
   │       └─→ Save checkpoint: application_[ID].json

3. Deduplicate: unique_parts Set → unique_skus.json

┌─────────────────────────────────────────────────────────────┐
│                   PHASE 2: Part Detail Fetch                 │
└─────────────────────────────────────────────────────────────┘

4. For each unique SKU:
   │
   ├─→ Fetch /items/[SKU]
   │   ├─→ Parse HTML for full specifications
   │   ├─→ Extract: dimensions, materials, tech notes, interchanges
   │   └─→ Merge with data from Phase 1
   │
   └─→ Save checkpoint: part_details/[SKU].json

5. Build final datasets:
   ├─→ parts.json (all unique parts with full data)
   ├─→ compatibility.json (part → vehicles mapping)
   └─→ hierarchical.json (Year → Make → Model → Parts)
```

---

## Deduplication Strategy

### Problem
Parts appear multiple times across different vehicles.

**Example**: Part SKU `3951` (Radiator) fits:
- 2025 Honda Accord (1.5L Turbo)
- 2025 Honda Accord (2.0L Hybrid)
- 2024 Honda Civic
- 2023 Honda Civic
- ... etc.

### Solution: Deduplication by SKU

```python
# During Phase 1: Track unique SKUs and build compatibility
unique_parts: dict[str, dict] = {}  # SKU → Part data
vehicle_compatibility: dict[str, list[dict]] = {}  # SKU → [Vehicles]

for application_page in all_applications:
    for part in application_page.parts:
        sku = part["sku"]

        # Store part data (first occurrence)
        if sku not in unique_parts:
            unique_parts[sku] = part

        # Build compatibility list
        if sku not in vehicle_compatibility:
            vehicle_compatibility[sku] = []

        vehicle_compatibility[sku].append({
            "make": application_page.make,
            "model": application_page.model,
            "year": application_page.year,
            "engine": part.get("engine"),
            "fuel_type": part.get("fuel_type"),
        })

# After Phase 1: Dedupe vehicles per part (same vehicle may appear twice)
for sku, vehicles in vehicle_compatibility.items():
    # Remove duplicate vehicle configurations
    vehicle_compatibility[sku] = list({
        frozenset(v.items()): v for v in vehicles
    }.values())
```

### Checkpoint Files

```
checkpoints/
├── unique_skus.json           # Set of all discovered SKUs
├── parts_basic.json           # Part data from application pages
├── vehicle_compatibility.json # SKU → [Vehicles] mapping
└── processed_applications.json # List of completed application IDs
```

---

## Prototype Validation

**Date**: 2025-10-27 23:06 UTC
**Test Make**: Honda (make_id: 3)
**Status**: SUCCESSFUL - Strategy validated

### Prototype Scope

The prototype scraper was executed on a limited subset of Honda vehicles to validate the scraping strategy:

- **Years tested**: 3 (most recent years)
- **Applications tested**: 5 (first 5 Honda models)
- **Total parts found**: 12
- **Unique SKUs**: 6
- **Deduplication rate**: 50% (6 duplicate parts removed)

### Key Validations

#### 1. Playwright Requirement CONFIRMED

Application pages (`/applications/[ID]`) return JavaScript-heavy content and REQUIRE Playwright for rendering:
- httpx/BeautifulSoup: FAILED (returned JavaScript, not rendered HTML)
- Playwright: SUCCESS (rendered HTML correctly)

**Impact**: All application page scraping must use Playwright (browser automation).

#### 2. AJAX Endpoints Work with httpx

Year and model selection endpoints (`/get_year_by_make/[ID]` and `/get_model_by_make_year/[ID]`) return jQuery code that can be parsed with regex:
- httpx requests: SUCCESS (returns JavaScript with embedded HTML)
- Custom regex parser: SUCCESS (extracts HTML from jQuery responses)

**Impact**: Phase 1 (hierarchy enumeration) can use lightweight httpx for AJAX endpoints.

#### 3. Deduplication Strategy Works PERFECTLY

The deduplication approach validated successfully:
- Same SKU appears across multiple vehicles (e.g., SKU 3951 fits 5 different Honda configurations)
- 50% deduplication rate demonstrates significant part reuse across vehicles
- Vehicle compatibility mapping built correctly (SKU -> list of vehicles)

**Sample Results**:
- SKU 3951 (Radiator): Fits 2025 Honda Accord (2 variants) + 2025 Civic (3 variants) = 5 applications
- SKU 3985 (Drive Motor Inverter Cooler): Fits 2025 Accord, Civic, CR-V = 3 applications

#### 4. Part Naming and Categorization

Parts are correctly extracted with:
- SKU: Always present (e.g., "3951")
- Name: SKU + Category format (e.g., "3951- Radiator")
- Category: Extracted from panel header (e.g., "Radiator", "Drive Motor Inverter Cooler")
- Images: Successfully extracted (S3 signed URLs)
- Features: Successfully extracted (bullet points)

### Technical Findings

#### What Works
- Playwright for application pages
- httpx for AJAX endpoints (year/model selection)
- BeautifulSoup for HTML parsing
- Regex for jQuery response parsing
- Set-based SKU deduplication
- Vehicle compatibility tracking

#### Adjustments Needed
- None - The strategy works as designed

#### Performance Observations
- Average delay: 1.0-1.5 seconds (prototype setting)
- Application page load time: 2-3 seconds (Playwright rendering)
- No rate limiting encountered
- No errors or failures

### Data Quality Assessment

All prototype data passed validation:
- 100% of parts have SKU
- 100% of parts have name
- 100% of parts have category
- 100% of parts have image URLs
- 100% of parts have detail URLs
- 100% of parts have vehicle mappings

### Prototype Outputs

Generated files (saved to `/Users/zach/PycharmProjects/carpart-scraper/prototype_output/`):
- `unique_parts.json`: 6 unique parts with full data
- `vehicle_compatibility.json`: SKU -> vehicle mappings
- `summary.json`: Prototype statistics
- `honda_years.json`: All years for Honda
- `honda_models.json`: Models for tested years
- `application_[ID].json`: Individual application page data (5 files)

### Conclusion

The scraping strategy is VALIDATED and ready for production implementation:

1. Technical approach: CONFIRMED (Playwright + httpx hybrid works)
2. Deduplication strategy: CONFIRMED (50% reduction achieved)
3. Data extraction: CONFIRMED (all fields extracted successfully)
4. Vehicle compatibility: CONFIRMED (mappings built correctly)
5. Error handling: NOT TESTED (no errors encountered in prototype)

**Next Steps**: Proceed with refactoring the prototype into production-ready codebase with proper architecture, error handling, and resume capability.

---

## Rate Limiting & Respectful Scraping

### Configuration

```python
MIN_DELAY = 1.0  # seconds
MAX_DELAY = 3.0  # seconds
DELAY_BETWEEN_PHASES = 5.0  # Extra delay when switching phases

# Calculate random delay to mimic human behavior
delay = random.uniform(MIN_DELAY, MAX_DELAY)
time.sleep(delay)
```

### Request Rate Calculation

**Average delay**: 2.0 seconds
**Requests per minute**: 30
**Requests per hour**: 1,800

**Total runtime for 3,861 requests**:
- 3,861 / 30 = **128.7 minutes** = **~2.15 hours** (minimum)
- With 1-3s delays: **2-6 hours** (realistic)
- With error retries: **4-8 hours** (conservative)

### Scheduling Strategy

**Best Practice**: Run during **off-peak hours** for the target site.

CSF website likely serves:
- **Primary audience**: North America (EST/PST timezones)
- **Business hours**: 9 AM - 5 PM EST (Mon-Fri)
- **Peak traffic**: 10 AM - 4 PM EST

**Recommended Schedule**:
- ✅ **Overnight**: 2 AM - 8 AM EST (low traffic)
- ✅ **Weekends**: Saturday/Sunday (lower business traffic)
- ❌ Avoid: Weekday business hours (9 AM - 5 PM EST)

### Error Handling & Backoff

```python
@retry(
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException))
)
def fetch_with_retry(url: str) -> httpx.Response:
    response = httpx.get(url)

    # Handle rate limiting
    if response.status_code == 429:
        retry_after = int(response.headers.get("Retry-After", 60))
        logger.warning(f"Rate limited, waiting {retry_after}s")
        time.sleep(retry_after)
        raise httpx.HTTPError("Rate limited")

    response.raise_for_status()
    return response
```

**Backoff Schedule**:
- 1st retry: Wait 4 seconds
- 2nd retry: Wait 8 seconds
- 3rd retry: Wait 16 seconds (up to max 60s)

---

## Error Handling & Resume Strategy

### Checkpoint System

Save progress after each completed step to enable resume:

```python
checkpoints/
├── progress.json              # Current scraping state
│   {
│     "phase": "hierarchy",
│     "completed_makes": ["Honda", "Toyota", ...],
│     "current_make": "Ford",
│     "completed_years": [2025, 2024, ...],
│     "current_year": 2023,
│     "completed_applications": [8430, 8426, ...]
│   }
│
├── makes_years.json           # Make → Years mapping
├── make_year_models.json      # (Make, Year) → Models mapping
├── applications/              # Individual application page data
│   ├── 8430.json
│   ├── 8426.json
│   └── ...
│
└── part_details/              # Individual part detail pages
    ├── 3951.json
    ├── 3985.json
    └── ...
```

### Resume Logic

```python
def resume_scraper():
    """Resume scraping from last checkpoint."""
    progress = load_json("checkpoints/progress.json")

    if progress["phase"] == "hierarchy":
        # Resume from current make/year/model
        start_make = progress["current_make"]
        start_year = progress.get("current_year")
        completed_apps = set(progress["completed_applications"])

        # Skip completed applications
        for app_id in all_application_ids:
            if app_id in completed_apps:
                continue
            # Resume scraping...

    elif progress["phase"] == "details":
        # Resume part detail fetching
        completed_skus = set(progress["completed_skus"])
        unique_skus = load_json("checkpoints/unique_skus.json")

        for sku in unique_skus:
            if sku in completed_skus:
                continue
            # Resume scraping...
```

### Error Categories & Handling

| Error Type | Strategy | Action |
|------------|----------|--------|
| **Network Timeout** | Retry with backoff | 3 attempts, then skip and log |
| **HTTP 429 (Rate Limit)** | Respect Retry-After header | Wait specified time, then retry |
| **HTTP 404** | Skip (not an error) | Log and continue |
| **HTTP 500** | Retry with backoff | 3 attempts, then skip and log |
| **Parse Error** | Log and skip | Save raw HTML for manual review |
| **Validation Error** | Log and skip | Save invalid data for review |

---

## Data Storage Strategy

### Intermediate Storage (During Scraping)

**Checkpoint files** (JSON):
```python
checkpoints/
├── progress.json              # Resume state
├── unique_skus.json          # Set of discovered SKUs
├── applications/             # Raw application page data
│   └── [ID].json
└── part_details/             # Raw part detail page data
    └── [SKU].json
```

**Purpose**: Enable resume, track progress, debugging

### Final Storage (After Scraping)

**Export files** (JSON):
```python
exports/
├── parts.json                # All unique parts with full data
├── compatibility.json        # Part → Vehicle mappings
├── hierarchical.json         # Year → Make → Model → Parts
└── metadata.json            # Export statistics and info
```

**Purpose**: WordPress import, backup, data analysis

### File Size Estimates

| File | Estimated Size | Description |
|------|----------------|-------------|
| parts.json | 5-10 MB | 500-1,000 parts × ~10 KB each |
| compatibility.json | 2-5 MB | Part → vehicles mappings |
| hierarchical.json | 10-20 MB | Full nested structure |
| checkpoints/ | 20-50 MB | Raw intermediate data |

---

## Export Strategy

### Export Formats

#### 1. **parts.json** (Flat List)

```json
{
  "metadata": {
    "export_date": "2025-10-27T10:00:00Z",
    "total_parts": 756,
    "version": "1.0",
    "scraper_version": "1.0.0"
  },
  "parts": [
    {
      "sku": "3951",
      "name": "Radiator",
      "category": "Radiator",
      "manufacturer": "CSF",
      "description": "1 Row Plastic Tank Aluminum Core",
      "specifications": {
        "core_material": "Aluminum",
        "core_length": "15 3/4\"",
        "core_width": "29 11/16\"",
        "tank_material": "Plastic",
        "no_of_rows": "1"
      },
      "tech_notes": "O.E.M. style Plastic tank & Aluminum core. Upgraded Heavy Duty Core. 7% Thicker 30mm vs OEM 27mm",
      "images": [
        {
          "url": "https://...",
          "alt_text": "3951",
          "is_primary": true
        }
      ],
      "features": [
        "Upgraded Heavy Duty Core",
        "7% Thicker 30mm vs OEM 27mm"
      ],
      "interchange_numbers": [
        {"type": "DPI", "number": "13932"},
        {"type": "OEM", "number": "19010-64A-A01"}
      ]
    }
  ]
}
```

#### 2. **compatibility.json** (Part → Vehicles)

```json
{
  "metadata": {
    "export_date": "2025-10-27T10:00:00Z",
    "total_mappings": 1523,
    "version": "1.0"
  },
  "compatibility": [
    {
      "part_sku": "3951",
      "vehicles": [
        {
          "make": "Honda",
          "model": "Accord",
          "year": 2025,
          "engine": "1.5L L4 1497cc",
          "fuel_type": null,
          "aspiration": "Turbocharged"
        },
        {
          "make": "Honda",
          "model": "Civic",
          "year": 2024,
          "engine": "1.5L L4 1497cc",
          "fuel_type": null,
          "aspiration": "Turbocharged"
        }
      ]
    }
  ]
}
```

#### 3. **hierarchical.json** (Year → Make → Model → Parts)

```json
{
  "metadata": {
    "export_date": "2025-10-27T10:00:00Z",
    "structure": "year > make > model > parts",
    "total_years": 37,
    "version": "1.0"
  },
  "data": {
    "2025": {
      "Honda": {
        "Accord": [
          {
            "sku": "3951",
            "name": "Radiator",
            "category": "Radiator"
          },
          {
            "sku": "3985",
            "name": "Drive Motor Inverter Cooler",
            "category": "Drive Motor Inverter Cooler"
          }
        ],
        "Civic": [...]
      },
      "Toyota": {...}
    },
    "2024": {...}
  }
}
```

---

## Timeline & Scheduling

### Development Timeline

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| **Planning** | Strategy doc, prototype | 1-2 days |
| **Prototype** | Build & test on Honda only | 1 day |
| **Implementation** | Refactor codebase | 2-3 days |
| **Testing** | Unit + integration tests | 1-2 days |
| **Full Scrape** | Run production scrape | 4-8 hours |
| **Validation** | Verify data quality | 1 day |
| **Export** | Generate JSON files | 1 hour |

**Total Development Time**: ~6-9 days

### Production Scraping Schedule

**One-Time Initial Scrape**:
- **Duration**: 4-8 hours (with 1-3s delays)
- **Schedule**: Overnight (2 AM - 10 AM EST) on a weekend
- **Date**: TBD after prototype validation

**Ongoing Updates** (Optional):
- **Frequency**: Weekly or monthly (TBD)
- **Duration**: Incremental (only new vehicles/parts) - 1-2 hours
- **Schedule**: Same overnight window

---

## Success Metrics

### Scraping Success

- ✅ **Completion Rate**: ≥99% of application pages successfully scraped
- ✅ **Data Quality**: ≥95% of parts pass Pydantic validation
- ✅ **Deduplication**: No duplicate SKUs in final parts.json
- ✅ **Compatibility**: Every part has ≥1 vehicle mapping
- ✅ **Error Rate**: <1% of requests result in unrecoverable errors

### Data Completeness

- ✅ **SKU**: 100% of parts have SKU
- ✅ **Name**: 100% of parts have name
- ✅ **Category**: ≥95% of parts have category
- ✅ **Images**: ≥90% of parts have ≥1 image
- ✅ **Specifications**: ≥80% of parts have ≥3 spec fields
- ✅ **Vehicles**: 100% of parts have ≥1 vehicle mapping

### Performance

- ✅ **Runtime**: Complete within 8 hours (with delays)
- ✅ **Resume**: Can resume from any checkpoint after failure
- ✅ **Memory**: Peak memory usage <2 GB
- ✅ **Export Size**: Final JSON exports <50 MB total

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Rate limiting / blocking** | Medium | High | 1-3s delays, polite user-agent, off-peak scheduling |
| **Site structure changes** | Low | High | Comprehensive tests, reconnaissance updates |
| **Partial scrape failure** | Medium | Medium | Checkpoint system, resume capability |
| **Invalid data** | Low | Medium | Pydantic validation, skip invalid parts |
| **Memory overflow** | Low | Medium | Stream processing, checkpoint cleanup |
| **Network issues** | Medium | Low | Retry with exponential backoff |

---

## Next Steps

1. ✅ **Review this strategy** with stakeholders
2. ✅ **Build prototype** (Honda only, 5 applications)
3. ✅ **Validate prototype** results - SUCCESSFUL (50% deduplication, all validations passed)
4. ⏳ **Refactor codebase** based on prototype learnings
5. ⏳ **Write tests** for all components
6. ⏳ **Run production scrape** (overnight, weekend)
7. ⏳ **Validate data quality** and export

---

**Document Version**: 1.1
**Last Updated**: 2025-10-27
**Status**: Prototype Validated - Ready for Production Implementation
**Next Review**: After production scraper implementation
