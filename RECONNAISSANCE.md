# CSF MyCarParts Website Reconnaissance Report

**Date**: 2025-10-27
**Site**: https://csf.mycarparts.com
**Status**: Complete

---

## Executive Summary

CSF MyCarParts uses a JavaScript-heavy, AJAX-driven interface with custom Bootstrap dropdowns (not standard `<select>` elements). The site follows a hierarchical vehicle selection pattern: **Make → Year → Model → Applications Page** with parts displayed by category.

### Key Findings

1. **NOT using standard HTML forms** - Custom dropdown buttons with AJAX population
2. **Vehicle hierarchy**: Make (ID) → Year (ID) → Model → Application (ID)
3. **AJAX responses return jQuery code** that manipulates DOM (not JSON)
4. **Direct URL patterns** can bypass dropdown navigation
5. **Parts organized by category** on applications pages (Radiator, Condenser, etc.)

---

## URL Patterns

### Discovered Endpoints

```
Base URL: https://csf.mycarparts.com

# Homepage / Vehicle Finder
GET /home

# AJAX Endpoints (return JavaScript/jQuery code)
GET /get_year_by_make/[MAKE_ID]
    → Returns: jQuery code to populate year dropdown
    → Example: /get_year_by_make/3 (Honda)

GET /get_model_by_make_year/[YEAR_ID]
    → Returns: jQuery code to populate model dropdown
    → Example: /get_model_by_make_year/192 (2025)

GET /items/[PART_NUMBER]/get_primary_image/
    → Returns: JSON with image URL
    → Example: /items/3985/get_primary_image/

GET /applications/search_vehicle?q=[SEARCH_TERM]
    → Returns: JSON with vehicle search results

# Application/Part Listing Pages
GET /applications/[APPLICATION_ID]
    → Shows all parts for a specific vehicle (Make/Year/Model)
    → Example: /applications/8430 (2025 Honda Accord)

# Part Detail Pages
GET /items/[PART_NUMBER]
    → Shows detailed information for a specific part
    → Example: /items/3985

# Part Number Search
POST /search_pn
    → Searches by part number, OE number, or industry number
    → Returns: AJAX response with results
```

---

## Data Hierarchy

### Vehicle Selection Flow

```
1. User selects MAKE from hardcoded list (51 makes)
   ↓
2. AJAX call: /get_year_by_make/[MAKE_ID]
   Response: JavaScript that populates year dropdown
   ↓
3. User selects YEAR from populated dropdown
   ↓
4. AJAX call: /get_model_by_make_year/[YEAR_ID]
   Response: JavaScript that populates model dropdown
   ↓
5. User selects MODEL from populated dropdown
   ↓
6. Navigate to: /applications/[APPLICATION_ID]
   Shows: All parts compatible with that vehicle
```

### Make List (All 51 Makes)

```json
{
  "1": "Nissan",
  "2": "Ford",
  "3": "Honda",
  "4": "Toyota",
  "5": "Scion",
  "6": "Mazda",
  "7": "Lexus",
  "8": "Kia",
  "9": "Hyundai",
  "10": "Dodge",
  "11": "Chevrolet",
  "12": "GMC",
  "13": "Buick",
  "14": "Peterbilt",
  "15": "Kenworth",
  "16": "International",
  "17": "Freightliner",
  "18": "Lincoln",
  "19": "Ram",
  "20": "Mercury",
  "21": "Volvo",
  "22": "Subaru",
  "23": "Jeep",
  "24": "Volkswagen",
  "25": "Mercedes-Benz",
  "26": "Mitsubishi",
  "27": "INFINITI",
  "28": "Land Rover",
  "29": "Chrysler",
  "30": "Pontiac",
  "31": "Saturn",
  "32": "BMW",
  "33": "Audi",
  "34": "Cadillac",
  "35": "Fiat",
  "36": "Acura",
  "37": "Hummer",
  "38": "Isuzu",
  "39": "Mack",
  "40": "Sterling Truck",
  "41": "Suzuki",
  "42": "Porsche",
  "43": "Jaguar",
  "44": "Mini",
  "45": "Oldsmobile",
  "46": "Plymouth",
  "47": "Saab",
  "48": "Geo",
  "49": "Daewoo",
  "50": "Eagle",
  "51": "Tesla"
}
```

---

## HTML Structure & Selectors

### Homepage / Vehicle Finder

```html
<!-- Custom Bootstrap Dropdowns (NOT standard <select>) -->
<div class="btn-group col">
    <a class="btn btn-secondary dropdown-toggle col" href="javascript:" id="btnMake">
        -- Choose Make --
    </a>
    <div class="dropdown-menu col">
        <ul>
            <li><a data-remote="true" href="remote:/get_year_by_make/3">Honda</a></li>
            <!-- More makes... -->
        </ul>
    </div>
</div>

<div class="btn-group col">
    <a class="btn btn-secondary dropdown-toggle col disabled" href="javascript:" id="btnYear">
        -- Choose Year --
    </a>
    <div class="dropdown-menu col"></div> <!-- Populated by AJAX -->
</div>

<div class="btn-group col">
    <a class="btn btn-secondary dropdown-toggle col disabled" href="javascript:" id="btnModel">
        -- Choose Model --
    </a>
    <div class="dropdown-menu col"></div> <!-- Populated by AJAX -->
</div>
```

#### Key Selectors:
- Make dropdown button: `#btnMake`
- Make dropdown links: `#btnMake + .dropdown-menu a[data-remote='true']`
- Year dropdown button: `#btnYear`
- Year dropdown links: `#btnYear + .dropdown-menu a`
- Model dropdown button: `#btnModel`
- Model dropdown links: `#btnModel + .dropdown-menu a`

### Applications Page (Vehicle Parts Listing)

**URL Example**: `/applications/8430` (2025 Honda Accord)

```html
<div class="panel" id="panel-top">
    <div class="panel-header">Fitment For</div>
    <div class="panel-body">
        <div class="row">
            <div class="col">
                <h2 class="font-weight-light">2025 Honda Accord</h2>
            </div>
            <div class="col-4">
                <!-- Jump to category dropdown -->
                <select name="part_type" id="part_type" class="form-control">
                    <option value="">-- Go to Purpose/Part Type --</option>
                    <option value="Drive Motor Inverter Cooler">Drive Motor Inverter Cooler</option>
                    <option value="Radiator">Radiator</option>
                </select>
            </div>
        </div>
    </div>
</div>

<!-- Parts grouped by category -->
<div class="applications">
    <!-- Category: Radiator -->
    <div class="panel result" id="radiator">
        <div class="panel-header">
            <div class="row">
                <div class="col">
                    <h4 class="font-weight-bold">Radiator</h4>
                </div>
                <div class="col text-right">
                    <a class="go_top" href="javascript:">Top</a>
                </div>
            </div>
        </div>
        <div class="panel-body">
            <!-- Individual Part -->
            <div class="row app" id="a3f2046e42b2218457e214415b347696">
                <div class="col-2 pl-0 image_3951">
                    <img class="img-thumbnail primary-image"
                         alt="3951"
                         src="https://illumaware-digital-assets.s3.us-east-2.amazonaws.com/...">
                </div>
                <div class="col-8 p-0">
                    <h4>
                        <a href="/items/3951">3951</a> - Radiator
                    </h4>
                    Position: <b>Not Applicable</b><br>
                    <table class="table table-borderless table-ssm">
                        <tbody>
                            <tr>
                                <td width="50%">Eng. Base: <b>1.5L L4 1497cc</b></td>
                                <td width="50%">Aspiration: <b>Turbocharged</b></td>
                            </tr>
                        </tbody>
                    </table>
                    <ul class="no-padding">
                        <li>Upgraded Heavy Duty Core. 7% Thicker 30mm vs OEM 27mm</li>
                    </ul>
                </div>
                <div class="col pr-0">
                    <p><a class="btn btn-secondary col" href="/items/3951">Item Detail</a></p>
                </div>
            </div>
            <!-- More parts in this category... -->
        </div>
    </div>
    <!-- More categories... -->
</div>
```

#### Key Selectors for Applications Page:

```
Vehicle Information:
  - Vehicle name: .panel-header h2.font-weight-light
  - Example: "2025 Honda Accord"

Part Categories:
  - Category panels: .panel.result
  - Category name: .panel-header h4.font-weight-bold
  - Category jump dropdown: select#part_type option

Individual Parts (within .panel-body):
  - Part container: .row.app
  - Part number/SKU: .row.app h4 a (first link's text)
  - Part name: .row.app h4 (text after SKU link)
  - Part image: .row.app img.img-thumbnail.primary-image (src attribute)
  - Position: .row.app (text after "Position: ")
  - Specifications table: .row.app table.table-borderless tbody tr td
  - Features/Notes: .row.app ul.no-padding li
  - Item detail link: .row.app a[href^="/items/"]
```

### Part Detail Page

**URL Pattern**: `/items/{SKU}`
**Example**: `/items/3951`

**Validated**: 2025-10-28 (Prototype tested on 5 parts: 3985, 3951, 3963, 3984, 3883)

#### Page Structure

**Full Product Description** (Optional - only ~20% of parts have this):
- **Selector**: `h5` (first on page)
- **Example**: "1 Row Plastic Tank Aluminum Core"
- **Note**: Many parts have empty h5 elements - handle gracefully

**Specification Tables** (~25 tables per page):
- **Count**: 25 tables total per detail page
- **Raw Specs**: ~35-36 specifications extracted (with duplicates)
- **Clean Specs**: 22 specifications after normalization
- **Format Issues Found**: Tables have **multiple inconsistent formats** requiring complex normalization

**Table Format Variations**:
```html
<!-- Format 1: Two cells (label with colon, value) -->
<tr>
  <td>Core Thickness (in):</td>
  <th class="text-left">7/8 (in)</th>
</tr>

<!-- Format 2: Single cell with colon-separated key:value -->
<tr>
  <td>Box Length (in):32 1/4</td>
</tr>

<!-- Format 3: Multi-column triplet pattern (6 cells = 2 specs) -->
<tr>
  <td>Bottom Hose Fitting (in):13/16 Left (in)</td>  <!-- Display cell (skip) -->
  <td>Bottom Hose Fitting (in):</td>                  <!-- Label -->
  <th class="text-left">13/16 Left (in)</th>          <!-- Value -->
  <td>Box Height (in):4 11/16</td>                    <!-- Display cell (skip) -->
  <td>Box Height (in):</td>                           <!-- Label -->
  <th class="text-left">4 11/16</th>                  <!-- Value -->
</tr>

<!-- Format 4: Vehicle compatibility table (skip entirely) -->
<tr>
  <th>Make</th>
  <th>Model</th>
</tr>
<tr>
  <td>Honda</td>
  <td>Civic</td>
</tr>
```

**Normalization Strategy** (implemented in `detail_page_prototype.py`):
1. **Handle 3-cell triplets**: Process rows with 6+ cells in groups of 3, skip display cell (index 0, 3, 6...), extract from cells 1-2, 4-5, 7-8...
2. **Handle 2-cell rows**: Extract label from cell 0, value from cell 1
3. **Handle single-cell rows**: Split on first colon if present
4. **Normalize keys**: Remove trailing colons from all labels
5. **Prevent duplicates**: Check if key already exists before adding
6. **Skip vehicle tables**: Detect by headers "Make" and "Model"
7. **Skip interchange tables**: Detect by headers "Reference Number" and "Reference Name"

**Tech Notes**:
- **Location**: Embedded in specification tables, NOT a separate div
- **Key**: Look for `"Tech Note:"` in specifications dict
- **Example**: "O.E.M. style Plastic tank & Aluminum core"
- **Selector**: Part of table parsing (key = "Tech Note:")

**Interchange/Reference Numbers Table**:
- **Selector**: `table` with headers `<th>Reference Number</th>` and `<th>Reference Name</th>`
- **Location**: Always the last table (table index 24 in 25 total tables)
- **Reference Types**: "OEM", "Partslink", "DPI", etc.
- **Count per Part**: 1-5 reference numbers
- **Skip Logic**: Ignore this table when extracting specifications (it's handled separately)

**Example Interchange Data**:
```json
[
  {"reference_number": "19010-64A-A01", "reference_type": "OEM"},
  {"reference_number": "HO3010256", "reference_type": "Partslink"}
]
```

#### Key Selectors for Detail Page:

```
Description:
  - Full description: h5 (first element, may be empty)

Specifications:
  - All tables: table
  - Table rows: tr
  - Cells: td, th
  - Skip: Tables with headers "Reference Number" and "Reference Name"
  - Normalization: Split colon-separated values, deduplicate keys

Tech Notes:
  - Embedded in specs: Look for key "Tech Note:" in parsed specifications

Interchange Data:
  - Table: table (last table with specific headers)
  - Headers: th containing "Reference Number" and "Reference Name"
  - Rows: tr (skip first header row)
  - Cells: td (first = number, second = type)
```

#### Data Quality Findings

**From 5-part prototype test** (SKUs: 3985, 3951, 3963, 3984, 3883):

| Field | Success Rate | Notes |
|-------|-------------|-------|
| Full Description | 20% (1/5) | Optional - most parts have empty `<h5>` elements |
| Specifications (raw) | 100% (5/5) | 35-36 specs per part before normalization (with duplicates) |
| Specifications (clean) | 100% (5/5) | **22 clean specs per part after normalization** |
| Tech Notes | 100% (5/5) | Found in spec tables with key "Tech Note" |
| Interchange Data | 100% (5/5) | 1-5 OEM/Partslink/DPI references per part |

**Normalization Results**:
- **Before**: 33-36 specifications with duplicate keys and inconsistent formatting
- **After**: 22 clean, deduplicated specifications with normalized keys
- **Improvement**: ~33% reduction in duplicate/malformed data

**Common Specifications Found**:
- Dimensions: Core Length/Width/Thickness, Box Height/Length/Width
- Materials: Core Material, Tank Material
- Configuration: No. Of Rows, Cross-flow/Down-flow
- Fittings: Top/Bottom Hose Fitting dimensions and positions
- Shipping: Box Weight, Hazardous Material status
- Features: Oil Cooler, Radiator Cap Supplied
- Tech Notes: Installation notes, compatibility warnings

---

## AJAX Response Formats

### /get_year_by_make/[MAKE_ID]

**Returns**: JavaScript/jQuery code (NOT JSON)

```javascript
$("#btnMake").text("Honda")
$("#btnMake").next().hide()
$("#btnYear").next().html("<ul><li><a href=\"remote:/get_model_by_make_year/192\">2025</a></li>...</ul>")
$("#btnYear").next().show()
$("#btnYear").removeClass("disabled")
$("#btnModel").text("-- Choose Model --")
$("#btnYear").text("-- Choose Year --")
$("#btnModel").addClass("disabled")
```

**To Parse**:
- Extract HTML from `.html("...")` call
- Parse extracted HTML to get year links
- Extract year number and endpoint from each `<a>` tag

### /get_model_by_make_year/[YEAR_ID]

**Returns**: JavaScript/jQuery code (NOT JSON)

```javascript
$("#btnYear").text("2025")
$("#btnYear").next().hide()
$("#btnModel").next().html("<ul><li><a href=\"/applications/8430\">Accord</a></li>...</ul>")
$("#btnModel").next().show()
$("#btnModel").removeClass("disabled")
```

**To Parse**:
- Extract HTML from `.html("...")` call
- Parse extracted HTML to get model links
- Extract model name and application ID from each `<a href="/applications/[ID]">` tag

---

## Scraping Strategy

### Recommended Approach

1. **Use Direct API Calls** (faster, more efficient than Playwright)
   - Fetch `/get_year_by_make/[MAKE_ID]` for all 51 makes
   - Parse JavaScript responses to extract year endpoints
   - Fetch each year endpoint to get models
   - Parse to extract application IDs

2. **Visit Application Pages** (`/applications/[ID]`)
   - Use httpx or Playwright (if JavaScript rendering needed)
   - Parse HTML to extract all parts for that vehicle
   - Extract: SKU, name, category, image, specs, features

3. **Visit Part Detail Pages** (`/items/[PART_NUMBER]`)
   - Get full part details, additional images, pricing
   - May contain more comprehensive specifications

### Alternative: Direct URL Construction

If application IDs follow a pattern, we might be able to:
- Generate application URLs directly without AJAX calls
- This would be much faster but needs validation

### Respectful Scraping Implementation

```python
# REQUIRED: Implement in all scrapers
MIN_DELAY = 1.0  # seconds
MAX_DELAY = 3.0  # seconds
USER_AGENT = "CSF-Parts-Scraper/1.0 (contact@example.com; +https://github.com/your/repo)"
MAX_RETRIES = 3
TIMEOUT = 30  # seconds

# Random delay between requests
time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

# Exponential backoff on errors
# Handle HTTP 429 (rate limiting)
# Respect robots.txt (already checked - no restrictions)
```

---

## Data Models Assessment

### Current Models vs Actual Site Data

#### ✅ Part Model - **MATCHES WELL**
```python
class Part:
    sku: str  # Matches: Part number (e.g., "3951")
    name: str  # Matches: Part name (e.g., "Radiator")
    price: Decimal  # NOT YET FOUND - may be on detail page
    description: str | None  # NOT YET FOUND - may be on detail page
    category: str  # Matches: Category (e.g., "Radiator", "Drive Motor Inverter Cooler")
    specifications: dict[str, Any]  # Matches: Table data (Eng. Base, Aspiration, Fuel Type, etc.)
    images: list[PartImage]  # Matches: Images with S3 URLs
    manufacturer: str  # Default: "CSF" (correct)
    in_stock: bool  # NOT YET FOUND - may be on detail page
```

**Potential Additions Needed**:
- `position: str | None` (e.g., "Not Applicable", "Front", "Rear")
- `features: list[str]` (bullet points from `<ul>` on applications page)
- `application_ids: list[int]` (which vehicles this part fits)

#### ✅ Vehicle Model - **MATCHES WELL**
```python
class Vehicle:
    make: str  # Matches: Honda, Ford, etc.
    model: str  # Matches: Accord, Civic, etc.
    year: int  # Matches: 2025, 2024, etc.
    submodel: str | None  # May exist in specs (e.g., "EX", "LX")
```

**Potential Additions Needed**:
- `engine: str | None` (e.g., "1.5L L4 1497cc")
- `fuel_type: str | None` (e.g., "FULL HYBRID EV-GAS (FHEV)")
- `aspiration: str | None` (e.g., "Turbocharged")

#### ✅ VehicleCompatibility Model - **MATCHES CONCEPT**
```python
class VehicleCompatibility:
    part_sku: str  # Matches
    vehicles: list[Vehicle]  # Matches concept
    notes: str | None  # Could use for features/specs
```

This model works, but we'll need to build it by:
1. Scraping application pages (one per vehicle config)
2. Extracting all parts for that vehicle
3. Creating VehicleCompatibility entries mapping parts to vehicles

---

## Parser Updates Needed

### CSFParser Class

The current `CSFParser` has placeholder selectors marked as TODO. Based on reconnaissance, here are the **actual selectors**:

```python
# src/scraper/parser.py - CSFParser class

def extract_part_data_from_application_page(self, soup: BeautifulSoup, vehicle_info: dict) -> list[dict[str, Any]]:
    """Extract all parts from an applications page (/applications/[ID])."""
    parts = []

    # Find all part containers
    part_rows = soup.select(".applications .row.app")

    for row in part_rows:
        # Extract part number/SKU
        sku_link = row.select_one("h4 a")
        if not sku_link:
            continue
        sku = sku_link.get_text(strip=True)

        # Extract part name (text after SKU in h4)
        h4 = row.select_one("h4")
        full_text = h4.get_text(strip=True)
        # Format: "3951 - Radiator"
        name = full_text.split(" - ", 1)[1] if " - " in full_text else full_text

        # Extract category from parent panel
        category_header = row.find_parent("div", class_="panel").select_one(".panel-header h4")
        category = category_header.get_text(strip=True) if category_header else None

        # Extract image
        img = row.select_one("img.primary-image")
        image_url = img.get("src") if img else None

        # Extract specifications from table
        specs = {}
        spec_rows = row.select("table.table-borderless tbody tr")
        for spec_row in spec_rows:
            cells = spec_row.select("td")
            for cell in cells:
                text = cell.get_text(strip=True)
                if ": " in text:
                    key, value = text.split(": ", 1)
                    # Remove <b> tags from value
                    value = value.replace("<b>", "").replace("</b>", "")
                    specs[key] = value

        # Extract features
        features = [li.get_text(strip=True) for li in row.select("ul.no-padding li")]

        # Extract item detail link
        detail_link = row.select_one("a[href^='/items/']")
        detail_url = detail_link.get("href") if detail_link else None

        parts.append({
            "sku": sku,
            "name": name,
            "category": category,
            "images": [{"url": image_url, "alt_text": sku, "is_primary": True}] if image_url else [],
            "specifications": specs,
            "features": features,
            "detail_url": detail_url,
            "vehicle": vehicle_info,  # Pass through vehicle info
        })

    return parts
```

---

## Next Steps

1. ✅ **Update Parser** (`src/scraper/parser.py`)
   - Implement actual selectors for applications pages
   - Add method to parse AJAX JavaScript responses
   - Create method for part detail pages (after visiting one)

2. ✅ **Update Models** (`src/models/part.py`, `src/models/vehicle.py`)
   - Add `position`, `features`, `application_ids` to Part
   - Add `engine`, `fuel_type`, `aspiration` to Vehicle
   - Ensure models can handle all discovered data

3. ✅ **Update Validator** (`src/scraper/validator.py`)
   - Adjust preprocessing for new fields
   - Handle missing price gracefully (may be on detail page only)

4. **Test End-to-End Flow**
   - Fetch makes → years → models → applications
   - Parse application page
   - Validate data with updated models
   - Export to JSON

5. **Reconnaissance Part 2**
   - Visit actual part detail page (`/items/3951`)
   - Document pricing, full description, additional specs
   - Update parser for detail pages

---

## Questions for Further Investigation

1. **Pricing**: Where is pricing displayed? Part detail page only?
2. **Stock Status**: Is stock status shown anywhere?
3. **Part Detail Pages**: What additional information is available?
4. **Category Listing**: Is there a way to list all categories without going through vehicles?
5. **All Parts Listing**: Can we get a complete list of all parts directly?
6. **Search Functionality**: Can `/search_pn` be used to enumerate parts?

---

**Report Generated**: 2025-10-27
**Next Update**: After visiting part detail pages
