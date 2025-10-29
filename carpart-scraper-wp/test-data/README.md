# Test Data for CSF Parts WordPress Plugin

This directory contains test JSON files for validating the import functionality.

## Files

### `sample-import.json`

Sample JSON with 3 automotive parts:
- **CSF-12345**: Honda Accord Radiator (in stock, 3 year compatibility)
- **CSF-67890**: Toyota Camry A/C Condenser (in stock, 3 year compatibility)
- **CSF-11111**: Ford Focus Intercooler (out of stock, 3 year compatibility)

**Coverage:**
- ✅ 3 different categories (Radiators, Condensers, Intercoolers)
- ✅ 3 different makes (Honda, Toyota, Ford)
- ✅ Multiple year compatibility
- ✅ Rich HTML descriptions
- ✅ Specifications (JSON object)
- ✅ Features (JSON array)
- ✅ Technical notes
- ✅ Multiple images (placeholder URLs)
- ✅ Stock status variations (in stock / out of stock)

## How to Test Import

### Option 1: Manual Upload (Easiest)

1. Install and activate the plugin in WordPress
2. Navigate to **CSF Parts → Import**
3. Click "Choose File" and select `sample-import.json`
4. Click "Upload File"
5. Click "Start Import"
6. Verify results:
   - Created: 3
   - Updated: 0
   - Skipped: 0
   - Errors: 0

### Option 2: Automatic URL Fetch

1. Host `sample-import.json` on a public HTTPS URL
2. Go to **CSF Parts → Settings**
3. Enable "Auto-Import"
4. Select "Remote URL"
5. Enter your URL (e.g., `https://example.com/sample-import.json`)
6. Set frequency to "Every 15 Minutes" (for testing)
7. Click "Save Settings"
8. Wait or trigger WordPress cron: `wp cron event run csf_parts_scheduled_import`

### Option 3: Push API

```bash
# Generate API key in Settings first
curl -X POST \
  https://your-site.com/wp-json/csf/v1/import \
  -H "X-CSF-API-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d @sample-import.json
```

### Option 4: Local Directory

1. Copy `sample-import.json` to a directory accessible by WordPress
2. Go to **CSF Parts → Settings**
3. Enable "Auto-Import"
4. Select "Local Directory"
5. Enter directory path (e.g., `/var/www/imports/`)
6. Set frequency
7. Save settings

## What to Verify After Import

### 1. Posts Created
Navigate to **CSF Parts → All Parts** - should see 3 parts:
- High Performance Aluminum Radiator
- A/C Condenser with Parallel Flow Technology
- Performance Intercooler - Direct Fit

### 2. Meta Fields Saved
Edit any part and verify:
- SKU populated (e.g., CSF-12345)
- Price shown
- Manufacturer: CSF
- Stock status correct
- Specifications saved (view in Custom Fields)

### 3. Taxonomies Assigned
Check that terms were created:
- **Categories**: Radiators, Condensers, Intercoolers
- **Makes**: Honda, Toyota, Ford
- **Models**: Accord, Camry, Focus
- **Years**: 2016-2022 (various)

### 4. REST API Works
Test endpoints:

```bash
# Get all parts
curl https://your-site.com/wp-json/csf/v1/parts

# Get part by SKU
curl https://your-site.com/wp-json/csf/v1/parts/CSF-12345

# Get makes
curl https://your-site.com/wp-json/csf/v1/vehicles/makes

# Get models for Honda
curl https://your-site.com/wp-json/csf/v1/vehicles/models?make=honda

# Get compatible parts
curl "https://your-site.com/wp-json/csf/v1/compatibility?make=honda&model=accord&year=2020"
```

### 5. Images Downloaded
Check that featured images were downloaded from placeholder URLs.

## Expected Import Results

```
Import completed successfully!

Created: 3
Updated: 0
Skipped: 0
Errors: 0
Warnings: 0
```

## Testing Duplicate Detection

Run the import twice. Second time should show:
```
Created: 0
Updated: 3  ← Parts updated based on SKU
Skipped: 0
```

## Testing Error Handling

### Test Invalid JSON
Create a file with invalid JSON:
```json
{ "parts": [ invalid json }
```
Expected: "Invalid JSON" error

### Test Missing Required Fields
Remove SKU from a part:
```json
{ "name": "Test Part", "price": 100 }
```
Expected: "Missing required field: sku" warning, part skipped

### Test Invalid Category
The import should create categories that don't exist automatically.

## Performance Testing

For large dataset testing, duplicate the parts array:
```python
# Generate 100 parts for testing
import json

with open('sample-import.json') as f:
    data = json.load(f)

# Duplicate parts with unique SKUs
original_parts = data['parts']
for i in range(100):
    for part in original_parts:
        new_part = part.copy()
        new_part['sku'] = f"CSF-{10000 + i * 3 + original_parts.index(part)}"
        data['parts'].append(new_part)

data['metadata']['total_parts'] = len(data['parts'])

with open('large-import.json', 'w') as f:
    json.dump(data, f, indent=2)
```

This generates 303 parts for stress testing.

## Cleanup

To remove test data:
```sql
-- Delete test parts
DELETE FROM wp_posts WHERE post_type = 'csf_part';
DELETE FROM wp_postmeta WHERE post_id NOT IN (SELECT ID FROM wp_posts);

-- Delete test terms (optional)
-- Be careful if you have real data!
```

Or use WordPress admin: **CSF Parts → All Parts** → Bulk Actions → Move to Trash
