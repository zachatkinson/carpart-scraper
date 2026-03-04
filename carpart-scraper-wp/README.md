# CSF Parts Catalog - WordPress Plugin

Complete WordPress plugin for displaying and managing CSF MyCarParts automotive parts data with Gutenberg blocks, async search, and JSON import system.

## Features

- **Custom Post Type**: `csf_part` for storing parts data
- **Taxonomies**: Categories, Makes, Models, Years for filtering
- **JSON Import System**: Import parts from scraper exports
- **3 Gutenberg Blocks**:
  - Single Product Display
  - Product Grid/List
  - Vehicle Selector (Year → Make → Model → Parts)
- **Async Search**: Real-time product search with AJAX
- **REST API**: Custom endpoints for dynamic queries
- **Admin Interface**: Import management and settings

## Requirements

- **WordPress**: 6.0 or higher
- **PHP**: 8.1 or higher
- **Node.js**: 18+ (for block development)
- **MySQL**: 5.7+ or MariaDB 10.3+

## Installation

### For Production Use

1. Download or clone the plugin to your WordPress plugins directory:
   ```bash
   cd /path/to/wordpress/wp-content/plugins/
   git clone [repository-url] csf-parts-catalog
   ```

2. Install Node dependencies and build blocks:
   ```bash
   cd csf-parts-catalog
   npm install
   npm run build
   ```

3. Activate the plugin in WordPress Admin → Plugins

### For Development

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start development mode (watches for changes):
   ```bash
   npm start
   ```

3. Run linting and formatting:
   ```bash
   npm run lint:js
   npm run format
   ```

## Usage

### Importing Parts Data

1. Navigate to **CSF Parts → Import** in WordPress admin
2. Upload JSON files exported from the carpart-scraper:
   - `parts.json` - Main parts data
   - `compatibility.json` - Vehicle compatibility mappings
3. Click "Start Import" and monitor progress
4. Review import log for any errors

### Using Gutenberg Blocks

#### Single Product Block

1. Add new block and search for "CSF Product"
2. Select a product by SKU from the dropdown
3. Configure display options in the sidebar:
   - Show/hide price
   - Show/hide specifications
   - Show/hide images
   - Show/hide compatibility

#### Product Grid Block

1. Add "CSF Product Grid" block
2. Configure filters:
   - Filter by: Category, Make, Model, Year
   - Select filter values
   - Choose layout: Grid or List
   - Set columns (for grid layout)
   - Set posts per page

#### Vehicle Selector Block

1. Add "CSF Vehicle Selector" block
2. Configure options:
   - Year-first or Make-first ordering
   - Results display: Redirect or inline
   - Target page for results (if redirecting)

### Using Async Search

The async search component automatically activates on any page with the class `csf-parts-search`:

```html
<div class="csf-parts-search">
    <input type="text" class="csf-search-input" placeholder="Search parts...">
    <div class="csf-search-results"></div>
</div>
```

### REST API Endpoints

#### Get Parts
```
GET /wp-json/csf/v1/parts
Parameters:
  - search: string (search query)
  - make: string (vehicle make)
  - model: string (vehicle model)
  - year: number (vehicle year)
  - category: string (part category)
  - per_page: number (results per page, default: 20)
  - page: number (page number, default: 1)
```

#### Get Vehicle Makes
```
GET /wp-json/csf/v1/vehicles/makes
Returns: Array of available makes
```

#### Get Vehicle Models
```
GET /wp-json/csf/v1/vehicles/models
Parameters:
  - make: string (required)
  - year: number (optional)
Returns: Array of models for the given make/year
```

#### Get Compatibility
```
GET /wp-json/csf/v1/compatibility
Parameters:
  - make: string (required)
  - model: string (required)
  - year: number (required)
Returns: Array of compatible parts
```

## Data Structure

### Custom Database Table: `wp_csf_parts`

Parts data is stored in a dedicated MySQL table for performance and flexibility, NOT as WordPress custom post types.

**Table Fields:**
- `id`: Auto-increment primary key
- `sku`: Unique part SKU (varchar 50, unique index) - e.g., "3411"
- `name`: Part name (varchar 200)
- `description`: Full product description (longtext)
- `short_description`: Brief description (text)
- `category`: Part category (varchar 100, indexed) - e.g., "Radiators", "Condensers"
- `price`: Part price (decimal 10,2)
- `manufacturer`: Manufacturer name (varchar 100, indexed)
- `in_stock`: Stock status (tinyint 1, indexed)
- `position`: Part position/location (varchar 50)
- `specifications`: JSON specifications data (longtext) - e.g., `{"Core Length (in)": "14 3/4 (in)", "Tank Material": "Plastic"}`
- `features`: JSON features array (longtext)
- `tech_notes`: Technical notes (text)
- `compatibility`: JSON vehicle compatibility data (longtext)
- `images`: JSON images array (longtext)
- `interchange_numbers`: JSON interchange part numbers (longtext)
- `scraped_at`: Last scrape timestamp (varchar 50)
- `created_at`: Record creation timestamp (datetime, auto)
- `updated_at`: Last update timestamp (datetime, auto-update)

**Why Custom Table:**
- Better performance for large datasets (10k+ parts)
- Flexible JSON storage for specifications without meta table overhead
- Direct SQL queries without WordPress post system complexity
- Easier data import/export from Python scraper

## Integration with Python Scraper

### Workflow

1. **Run Scraper** (Python):
   ```bash
   carpart scrape --all --check-changes
   carpart export --format json --output /path/to/exports/
   ```

2. **Upload to WordPress**:
   - Manual: Upload via admin interface
   - Automated: Copy to WordPress uploads directory
   - API: POST to WordPress REST endpoint (requires auth)

3. **Import in WordPress**:
   - Navigate to CSF Parts → Import
   - Select uploaded JSON file
   - Click "Start Import"
   - Monitor progress and review log

### Export File Structure

**parts.json:**
```json
{
  "metadata": {
    "export_date": "2025-01-15T10:30:00Z",
    "total_parts": 1523,
    "version": "1.0"
  },
  "parts": [
    {
      "sku": "CSF-12345",
      "name": "High Performance Radiator",
      "price": "299.99",
      "category": "Radiators",
      "manufacturer": "CSF",
      "in_stock": true,
      "description": "...",
      "specifications": {...},
      "features": [...],
      "images": [...]
    }
  ]
}
```

**compatibility.json:**
```json
[
  {
    "part_sku": "CSF-12345",
    "vehicles": [
      {
        "make": "Honda",
        "model": "Accord",
        "year": 2020,
        "submodel": "Sport",
        "engine": "2.0L Turbo"
      }
    ]
  }
]
```

## Development

### File Structure

```
csf-parts-catalog/
├── csf-parts-catalog.php       # Main plugin file
├── includes/                   # PHP backend
│   ├── class-csf-parts-plugin.php
│   ├── class-csf-parts-post-types.php
│   ├── class-csf-parts-taxonomies.php
│   ├── class-csf-parts-json-importer.php
│   ├── class-csf-parts-ajax-handler.php
│   └── class-csf-parts-rest-api.php
├── admin/                      # Admin interface
│   ├── class-csf-parts-admin-menu.php
│   ├── class-csf-parts-import-manager.php
│   └── views/
│       └── import-page.php
├── blocks/src/                 # Gutenberg blocks (React)
│   ├── single-product/
│   ├── product-grid/
│   └── vehicle-selector/
├── public/                     # Frontend assets
│   ├── js/
│   │   └── search-async.js
│   └── css/
│       └── frontend-styles.css
└── tests/                      # PHPUnit tests
```

### Coding Standards

- **PHP**: WordPress Coding Standards
- **JavaScript**: ESLint (via @wordpress/scripts)
- **CSS**: BEM methodology
- **Documentation**: PHPDoc and JSDoc

### Testing

Run PHP tests:
```bash
phpunit
```

Run JavaScript tests:
```bash
npm test
```

## Troubleshooting

### Import Fails

1. Check JSON file format matches expected structure
2. Verify file upload size limits (PHP `upload_max_filesize`)
3. Check error logs in WP Admin → CSF Parts → Import Log
4. Ensure write permissions on uploads directory

### Blocks Not Appearing

1. Verify blocks are built: `npm run build`
2. Check `blocks/build/` directory exists and contains block.json files
3. Clear WordPress cache
4. Re-save permalinks: Settings → Permalinks → Save

### Search Not Working

1. Check REST API is accessible: `/wp-json/csf/v1/parts`
2. Verify JavaScript is loaded (check browser console)
3. Check for JavaScript errors in console
4. Ensure parts exist in database

## Support

For issues related to:
- **Plugin**: Open issue on GitHub repository
- **Scraper**: See main carpart-scraper documentation
- **WordPress**: WordPress.org support forums

## License

MIT License - see LICENSE file for details

## Credits

Developed as part of the CSF MyCarParts scraper project.

---

**Plugin Version**: 1.0.0
**WordPress Tested**: 6.4
**Last Updated**: 2025-01-15
