<?php
/**
 * JSON Importer for CSF Parts.
 *
 * Handles importing parts data from JSON files exported by the Python scraper.
 * Validates structure, creates/updates posts, handles images, and assigns taxonomies.
 *
 * @package CSF_Parts_Catalog
 * @since   1.0.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

/**
 * Class CSF_Parts_JSON_Importer
 *
 * V2 Architecture: Imports directly into custom database table.
 * Much simpler than previous approach - no posts, no taxonomies, no meta.
 */
class CSF_Parts_JSON_Importer {

	/**
	 * Import results.
	 *
	 * @var array
	 */
	private $results = array(
		'created'  => 0,
		'updated'  => 0,
		'skipped'  => 0,
		'errors'   => array(),
		'warnings' => array(),
	);

	/**
	 * Batch size for processing.
	 *
	 * @var int
	 */
	private $batch_size = 50;

	/**
	 * Database instance.
	 *
	 * @var CSF_Parts_Database
	 */
	private $database;

	/**
	 * Constructor.
	 */
	public function __construct() {
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-database.php';
		$this->database = new CSF_Parts_Database();
	}

	/**
	 * Import parts from JSON file.
	 *
	 * V2: Directly inserts into custom table (much simpler!).
	 *
	 * @since 1.0.0
	 * @param string $file_path Path to JSON file.
	 * @return array Import results.
	 */
	public function import_from_file( string $file_path ): array {
		// Validate file exists.
		if ( ! file_exists( $file_path ) ) {
			$this->results['errors'][] = 'File not found.';
			return $this->results;
		}

		// Read and decode JSON.
		$json_content = file_get_contents( $file_path );
		if ( false === $json_content ) {
			$this->results['errors'][] = 'Failed to read file.';
			return $this->results;
		}

		$data = json_decode( $json_content, true );
		if ( json_last_error() !== JSON_ERROR_NONE ) {
			$this->results['errors'][] = sprintf(
				/* translators: %s: JSON error message */
				'Invalid JSON: %s',
				json_last_error_msg()
			);
			return $this->results;
		}

		// Validate structure.
		$validation_result = $this->validate_json_structure( $data );
		if ( ! $validation_result['valid'] ) {
			$this->results['errors'] = array_merge(
				$this->results['errors'],
				$validation_result['errors']
			);
			return $this->results;
		}

		// Process parts in batches.
		$parts = $data['parts'] ?? array();
		$this->import_parts( $parts );

		return $this->results;
	}

	/**
	 * Validate JSON structure.
	 *
	 * @since 1.0.0
	 * @param array $data Decoded JSON data.
	 * @return array Validation result with 'valid' and 'errors' keys.
	 */
	private function validate_json_structure( array $data ): array {
		$errors = array();

		// Check for required top-level keys.
		if ( ! isset( $data['parts'] ) || ! is_array( $data['parts'] ) ) {
			$errors[] = 'Missing or invalid "parts" array.';
		}

		// Validate metadata if present.
		if ( isset( $data['metadata'] ) ) {
			if ( ! is_array( $data['metadata'] ) ) {
				$errors[] = 'Invalid "metadata" structure.';
			}
		}

		// Validate at least one part exists.
		if ( empty( $data['parts'] ) ) {
			$errors[] = 'No parts found in JSON file.';
		}

		return array(
			'valid'  => empty( $errors ),
			'errors' => $errors,
		);
	}

	/**
	 * Import parts array.
	 *
	 * @since 1.0.0
	 * @param array $parts Array of part data.
	 */
	private function import_parts( array $parts ): void {
		$batch_count = ceil( count( $parts ) / $this->batch_size );

		for ( $batch = 0; $batch < $batch_count; $batch++ ) {
			$batch_parts = array_slice(
				$parts,
				$batch * $this->batch_size,
				$this->batch_size
			);

			foreach ( $batch_parts as $part_data ) {
				$this->import_single_part( $part_data );
			}

			// Allow for memory cleanup between batches.
			if ( function_exists( 'wp_cache_flush' ) ) {
				wp_cache_flush();
			}
		}
	}

	/**
	 * Import single part.
	 *
	 * V2: Simply upserts into database table. SO MUCH SIMPLER!
	 *
	 * @since 1.0.0
	 * @param array $part_data Part data from JSON.
	 */
	private function import_single_part( array $part_data ): void {
		// Validate required fields.
		$validation = $this->validate_part_data( $part_data );
		if ( ! $validation['valid'] ) {
			$this->results['skipped']++;
			$this->results['warnings'][] = sprintf(
				/* translators: %s: validation errors */
				'Skipped invalid part: %s',
				implode( ', ', $validation['errors'] )
			);
			return;
		}

		// Check if part exists.
		$existing = $this->database->get_part_by_sku( $part_data['sku'] );

		// Clean up data before saving.
		$part_data = $this->cleanup_part_data( $part_data );

		// Upsert into database (handles both insert and update).
		$result = $this->database->upsert_part( $part_data );

		if ( false === $result ) {
			$this->results['errors'][] = sprintf(
				/* translators: %s: SKU */
				'Failed to import part: %s',
				$part_data['sku']
			);
			return;
		}

		// Track results.
		if ( $existing ) {
			$this->results['updated']++;
		} else {
			$this->results['created']++;
		}
	}

	/**
	 * Clean up part data before saving.
	 *
	 * Removes trash data like " Eng." suffix from engine strings and fixes duplicate CSF prefixes in names.
	 *
	 * @since 2.0.0
	 * @param array $part_data Part data to clean.
	 * @return array Cleaned part data.
	 */
	private function cleanup_part_data( array $part_data ): array {
		// Normalize verbose CSF category names to cleaner display names.
		if ( isset( $part_data['category'] ) && is_string( $part_data['category'] ) ) {
			$category_map = array(
				'Drive Motor Inverter Cooler' => 'Inverter Cooler',
			);

			if ( isset( $category_map[ $part_data['category'] ] ) ) {
				$part_data['category'] = $category_map[ $part_data['category'] ];
			}
		}

		// Map 'full_description' to 'description' if present (Python enrichment uses this key).
		if ( empty( $part_data['description'] ) && ! empty( $part_data['full_description'] ) ) {
			$part_data['description'] = $part_data['full_description'];
		}

		// Clean up name - fix duplicate CSF prefix (CSFCSF-3764 -> CSF3764).
		if ( isset( $part_data['name'] ) && is_string( $part_data['name'] ) ) {
			// Remove duplicate CSF prefix if present (CSFCSF-3764 -> CSF-3764).
			$part_data['name'] = preg_replace( '/^CSFCSF-/', 'CSF-', $part_data['name'] );

			// Remove hyphens from SKU format in name (CSF-3764 -> CSF3764).
			$part_data['name'] = str_replace( array( 'CSF-', '-' ), array( 'CSF', '' ), $part_data['name'] );
		}

		// Clean up compatibility data - remove " Eng." suffix from engine strings.
		if ( isset( $part_data['compatibility'] ) && is_array( $part_data['compatibility'] ) ) {
			foreach ( $part_data['compatibility'] as &$vehicle ) {
				if ( isset( $vehicle['engine'] ) && is_string( $vehicle['engine'] ) ) {
					// Remove " Eng." suffix (with leading space).
					$vehicle['engine'] = preg_replace( '/ Eng\.$/', '', $vehicle['engine'] );
				}
			}
			unset( $vehicle ); // Break reference.
		}

		return $part_data;
	}

	/**
	 * Validate part data.
	 *
	 * V2 Note: Name is optional because real CSF data only has names for radiators,
	 * not for condensers or intercoolers.
	 *
	 * @since 1.0.0
	 * @param array $part_data Part data to validate.
	 * @return array Validation result.
	 */
	private function validate_part_data( array $part_data ): array {
		$errors = array();

		// Required fields: Only SKU is truly required (name is optional).
		if ( empty( $part_data['sku'] ) ) {
			$errors[] = 'Missing required field: sku';
		}

		// Price validation removed - this is a catalog system, price is informational only

		return array(
			'valid'  => empty( $errors ),
			'errors' => $errors,
		);
	}



	/**
	 * Get import results.
	 *
	 * @since 1.0.0
	 * @return array Import results.
	 */
	public function get_results(): array {
		return $this->results;
	}

	/**
	 * Set batch size for processing.
	 *
	 * @since 1.0.0
	 * @param int $size Batch size.
	 */
	public function set_batch_size( int $size ): void {
		$this->batch_size = max( 1, $size );
	}
}
