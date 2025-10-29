# Archived V1 Tests

This directory contains tests for the V1 architecture that was superseded by V2 in October 2025.

## Why Archived?

The V2 architecture introduced a fundamental shift:
- **V1:** Used WordPress post types and taxonomies
- **V2:** Uses custom database tables with JSON columns for vehicle compatibility

These tests are preserved for historical reference but are no longer relevant to the current codebase.

## Archived Tests

- `TaxonomiesTest.php` - Tested WordPress taxonomy label generation (replaced by JSON storage)

## V2 Test Coverage

See `/tests/unit/` for current V2 architecture tests:
- `DatabaseTest.php` - Custom table operations
- `URLHandlerTest.php` - Virtual URL routing
- `RESTAPITest.php` - REST API endpoints
- `JSONImporterTest.php` - JSON import functionality
