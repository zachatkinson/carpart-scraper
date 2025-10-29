<?php
/**
 * Validation script for testing JSON import structure.
 *
 * Run this script from command line to validate the sample import data:
 * php validate-import.php
 *
 * @package CSF_Parts_Catalog
 * @since   1.0.0
 */

// Color output helpers for CLI
function success( string $message ): void {
	echo "\033[32m✓ {$message}\033[0m\n";
}

function error( string $message ): void {
	echo "\033[31m✗ {$message}\033[0m\n";
}

function info( string $message ): void {
	echo "\033[34mℹ {$message}\033[0m\n";
}

function warning( string $message ): void {
	echo "\033[33m⚠ {$message}\033[0m\n";
}

/**
 * Validate JSON file structure and content.
 *
 * @param string $file_path Path to JSON file.
 * @return bool True if valid, false otherwise.
 */
function validate_json_file( string $file_path ): bool {
	info( "Validating JSON file: {$file_path}" );

	// Check file exists.
	if ( ! file_exists( $file_path ) ) {
		error( 'File does not exist' );
		return false;
	}
	success( 'File exists' );

	// Read file content.
	$json_content = file_get_contents( $file_path );
	if ( false === $json_content ) {
		error( 'Failed to read file' );
		return false;
	}
	success( 'File readable' );

	// Parse JSON.
	$data = json_decode( $json_content, true );
	if ( null === $data ) {
		error( 'Invalid JSON: ' . json_last_error_msg() );
		return false;
	}
	success( 'Valid JSON structure' );

	// Validate metadata section.
	if ( ! isset( $data['metadata'] ) ) {
		error( 'Missing "metadata" section' );
		return false;
	}
	success( 'Metadata section present' );

	$metadata = $data['metadata'];
	$required_metadata = array( 'export_date', 'total_parts', 'version' );
	foreach ( $required_metadata as $field ) {
		if ( ! isset( $metadata[ $field ] ) ) {
			error( "Missing metadata field: {$field}" );
			return false;
		}
	}
	success( 'All required metadata fields present' );

	// Validate export_date format (ISO 8601).
	$export_date = $metadata['export_date'];
	if ( false === strtotime( $export_date ) ) {
		error( "Invalid export_date format: {$export_date}" );
		return false;
	}
	success( 'Valid export_date format' );

	// Validate parts section.
	if ( ! isset( $data['parts'] ) || ! is_array( $data['parts'] ) ) {
		error( 'Missing or invalid "parts" array' );
		return false;
	}
	success( 'Parts array present' );

	$parts = $data['parts'];
	$parts_count = count( $parts );

	// Check parts count matches metadata.
	if ( $parts_count !== $metadata['total_parts'] ) {
		warning( "Parts count ({$parts_count}) does not match metadata total_parts ({$metadata['total_parts']})" );
	} else {
		success( "Parts count matches metadata ({$parts_count})" );
	}

	// Validate each part.
	$required_part_fields = array(
		'sku',
		'name',
		'price',
		'category',
		'manufacturer',
		'in_stock',
		'description',
	);

	$optional_part_fields = array(
		'position',
		'specifications',
		'features',
		'tech_notes',
		'images',
		'vehicles',
	);

	foreach ( $parts as $index => $part ) {
		info( "\nValidating part " . ( $index + 1 ) . "/{$parts_count}" );

		// Check required fields.
		foreach ( $required_part_fields as $field ) {
			if ( ! isset( $part[ $field ] ) ) {
				error( "Part {$index}: Missing required field '{$field}'" );
				return false;
			}
		}
		success( 'All required fields present' );

		// Validate SKU format.
		if ( ! preg_match( '/^CSF-\d+$/', $part['sku'] ) ) {
			warning( "Part {$index}: SKU '{$part['sku']}' does not match expected format (CSF-XXXXX)" );
		} else {
			success( "Valid SKU format: {$part['sku']}" );
		}

		// Validate price is numeric.
		if ( ! is_numeric( $part['price'] ) || $part['price'] < 0 ) {
			error( "Part {$index}: Invalid price '{$part['price']}'" );
			return false;
		}
		success( "Valid price: \${$part['price']}" );

		// Validate in_stock is boolean.
		if ( ! is_bool( $part['in_stock'] ) ) {
			error( "Part {$index}: in_stock must be boolean, got " . gettype( $part['in_stock'] ) );
			return false;
		}
		success( 'Valid in_stock boolean: ' . ( $part['in_stock'] ? 'true' : 'false' ) );

		// Validate specifications if present.
		if ( isset( $part['specifications'] ) ) {
			if ( ! is_array( $part['specifications'] ) ) {
				error( "Part {$index}: specifications must be an object/array" );
				return false;
			}
			success( 'Valid specifications object with ' . count( $part['specifications'] ) . ' fields' );
		}

		// Validate features if present.
		if ( isset( $part['features'] ) ) {
			if ( ! is_array( $part['features'] ) ) {
				error( "Part {$index}: features must be an array" );
				return false;
			}
			success( 'Valid features array with ' . count( $part['features'] ) . ' items' );
		}

		// Validate images if present.
		if ( isset( $part['images'] ) ) {
			if ( ! is_array( $part['images'] ) ) {
				error( "Part {$index}: images must be an array" );
				return false;
			}
			foreach ( $part['images'] as $img_index => $image ) {
				if ( ! filter_var( $image, FILTER_VALIDATE_URL ) ) {
					error( "Part {$index}: Invalid image URL at index {$img_index}: {$image}" );
					return false;
				}
			}
			success( 'Valid images array with ' . count( $part['images'] ) . ' URLs' );
		}

		// Validate vehicles if present.
		if ( isset( $part['vehicles'] ) ) {
			if ( ! is_array( $part['vehicles'] ) ) {
				error( "Part {$index}: vehicles must be an array" );
				return false;
			}

			$required_vehicle_fields = array( 'make', 'model', 'year' );
			foreach ( $part['vehicles'] as $v_index => $vehicle ) {
				foreach ( $required_vehicle_fields as $v_field ) {
					if ( ! isset( $vehicle[ $v_field ] ) ) {
						error( "Part {$index}, Vehicle {$v_index}: Missing required field '{$v_field}'" );
						return false;
					}
				}

				// Validate year is numeric and reasonable.
				$year = $vehicle['year'];
				if ( ! is_numeric( $year ) || $year < 1900 || $year > 2100 ) {
					error( "Part {$index}, Vehicle {$v_index}: Invalid year '{$year}'" );
					return false;
				}
			}
			success( 'Valid vehicles array with ' . count( $part['vehicles'] ) . ' compatibility entries' );
		}
	}

	return true;
}

/**
 * Main validation execution.
 */
function main(): void {
	echo "\n";
	info( '═══════════════════════════════════════════════════════════' );
	info( '  CSF Parts Catalog - Import JSON Validation Script' );
	info( '═══════════════════════════════════════════════════════════' );
	echo "\n";

	$json_file = __DIR__ . '/sample-import.json';

	if ( validate_json_file( $json_file ) ) {
		echo "\n";
		success( '═══════════════════════════════════════════════════════════' );
		success( '  ALL VALIDATIONS PASSED!' );
		success( '  JSON file is ready for import into WordPress.' );
		success( '═══════════════════════════════════════════════════════════' );
		echo "\n";
		exit( 0 );
	} else {
		echo "\n";
		error( '═══════════════════════════════════════════════════════════' );
		error( '  VALIDATION FAILED!' );
		error( '  Please fix the errors above before importing.' );
		error( '═══════════════════════════════════════════════════════════' );
		echo "\n";
		exit( 1 );
	}
}

// Run validation.
main();
