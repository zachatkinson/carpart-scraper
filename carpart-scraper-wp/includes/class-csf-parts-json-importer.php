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
			$this->results['errors'][] = __( 'File not found.', CSF_Parts_Constants::TEXT_DOMAIN );
			return $this->results;
		}

		// Read and decode JSON.
		$json_content = file_get_contents( $file_path );
		if ( false === $json_content ) {
			$this->results['errors'][] = __( 'Failed to read file.', CSF_Parts_Constants::TEXT_DOMAIN );
			return $this->results;
		}

		$data = json_decode( $json_content, true );
		if ( json_last_error() !== JSON_ERROR_NONE ) {
			$this->results['errors'][] = sprintf(
				/* translators: %s: JSON error message */
				__( 'Invalid JSON: %s', CSF_Parts_Constants::TEXT_DOMAIN ),
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
			$errors[] = __( 'Missing or invalid "parts" array.', CSF_Parts_Constants::TEXT_DOMAIN );
		}

		// Validate metadata if present.
		if ( isset( $data['metadata'] ) ) {
			if ( ! is_array( $data['metadata'] ) ) {
				$errors[] = __( 'Invalid "metadata" structure.', CSF_Parts_Constants::TEXT_DOMAIN );
			}
		}

		// Validate at least one part exists.
		if ( empty( $data['parts'] ) ) {
			$errors[] = __( 'No parts found in JSON file.', CSF_Parts_Constants::TEXT_DOMAIN );
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
				__( 'Skipped invalid part: %s', CSF_Parts_Constants::TEXT_DOMAIN ),
				implode( ', ', $validation['errors'] )
			);
			return;
		}

		// Check if part exists.
		$existing = $this->database->get_part_by_sku( $part_data['sku'] );

		// Upsert into database (handles both insert and update).
		$result = $this->database->upsert_part( $part_data );

		if ( false === $result ) {
			$this->results['errors'][] = sprintf(
				/* translators: %s: SKU */
				__( 'Failed to import part: %s', CSF_Parts_Constants::TEXT_DOMAIN ),
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
			$errors[] = __( 'Missing required field: sku', CSF_Parts_Constants::TEXT_DOMAIN );
		}

		// Validate price if present (NULL is allowed for parts without pricing).
		if ( isset( $part_data['price'] ) && ! is_null( $part_data['price'] ) && ! is_numeric( $part_data['price'] ) ) {
			$errors[] = __( 'Invalid price value.', CSF_Parts_Constants::TEXT_DOMAIN );
		}

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
