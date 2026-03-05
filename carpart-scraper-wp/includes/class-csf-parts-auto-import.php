<?php
/**
 * Automatic Import Handler.
 *
 * Handles automated importing from remote sources and scheduled imports.
 *
 * @package CSF_Parts_Catalog
 * @since   1.0.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

/**
 * Class CSF_Parts_Auto_Import
 */
class CSF_Parts_Auto_Import {

	/**
	 * Constructor.
	 */
	public function __construct() {
		// Register WordPress cron schedules.
		add_filter( 'cron_schedules', array( $this, 'add_cron_schedules' ) );

		// Schedule automatic import if enabled.
		add_action( 'csf_parts_scheduled_import', array( $this, 'run_scheduled_import' ) );

		// Register REST API endpoint for push imports.
		add_action( 'rest_api_init', array( $this, 'register_push_endpoint' ) );

		// Admin notices for auto-import status.
		add_action( 'admin_notices', array( $this, 'display_auto_import_notices' ) );
	}

	/**
	 * Add custom cron schedules.
	 *
	 * @since 1.0.0
	 * @param array $schedules Existing schedules.
	 * @return array Modified schedules.
	 */
	public function add_cron_schedules( array $schedules ): array {
		$schedules['csf_every_15_minutes'] = array(
			'interval' => 15 * MINUTE_IN_SECONDS,
			'display'  => __( 'Every 15 Minutes', 'csf-parts' ),
		);

		$schedules['csf_every_30_minutes'] = array(
			'interval' => 30 * MINUTE_IN_SECONDS,
			'display'  => __( 'Every 30 Minutes', 'csf-parts' ),
		);

		$schedules['csf_every_6_hours'] = array(
			'interval' => 6 * HOUR_IN_SECONDS,
			'display'  => __( 'Every 6 Hours', 'csf-parts' ),
		);

		$schedules['csf_every_12_hours'] = array(
			'interval' => 12 * HOUR_IN_SECONDS,
			'display'  => __( 'Every 12 Hours', 'csf-parts' ),
		);

		return $schedules;
	}

	/**
	 * Schedule automatic import.
	 *
	 * @since 1.0.0
	 * @param string $frequency Cron schedule frequency.
	 */
	public static function schedule_import( string $frequency ): void {
		// Clear any existing schedule.
		$timestamp = wp_next_scheduled( 'csf_parts_scheduled_import' );
		if ( $timestamp ) {
			wp_unschedule_event( $timestamp, 'csf_parts_scheduled_import' );
		}

		// Schedule new import.
		if ( 'disabled' !== $frequency ) {
			wp_schedule_event( time(), $frequency, 'csf_parts_scheduled_import' );
		}
	}

	/**
	 * Run scheduled import.
	 *
	 * Uses Strategy Pattern - delegates to appropriate source strategy.
	 *
	 * @since 1.0.0
	 */
	public function run_scheduled_import(): void {
		$auto_import_enabled = get_option( 'csf_parts_auto_import_enabled', 0 );

		if ( ! $auto_import_enabled ) {
			return;
		}

		try {
			// Use factory to get appropriate strategy (Open/Closed Principle).
			$source_strategy = Import_Source_Factory::create_from_options();

			// Fetch file using strategy.
			$file_path = $source_strategy->fetch();

			// Run import.
			$this->run_import( $file_path );

		} catch ( Exception $e ) {
			// Log error.
			error_log( 'CSF Parts Auto Import Error: ' . $e->getMessage() );

			// Save error for admin notice.
			update_option( 'csf_parts_auto_import_last_error', $e->getMessage() );
		}
	}

	/**
	 * Run import from file.
	 *
	 * @since 1.0.0
	 * @param string $file_path Path to JSON file.
	 * @throws Exception If import fails.
	 */
	private function run_import( string $file_path ): void {
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-json-importer.php';

		$importer = new CSF_Parts_JSON_Importer();
		$results  = $importer->import_from_file( $file_path );

		// Save results.
		update_option( 'csf_parts_last_auto_import', current_time( 'mysql' ) );
		update_option( 'csf_parts_last_auto_import_results', $results );
		update_option( 'csf_parts_last_imported_file', $file_path );

		// Clear any previous errors.
		delete_option( 'csf_parts_auto_import_last_error' );

		// Log success.
		error_log(
			sprintf(
				'CSF Parts Auto Import Success: Created %d, Updated %d, Skipped %d',
				$results['created'],
				$results['updated'],
				$results['skipped']
			)
		);
	}

	/**
	 * Register REST API endpoints for push imports and image uploads.
	 *
	 * @since 1.0.0
	 */
	public function register_push_endpoint(): void {
		register_rest_route(
			'csf/v1',
			'/import',
			array(
				'methods'             => 'POST',
				'callback'            => array( $this, 'handle_push_import' ),
				'permission_callback' => array( $this, 'check_push_import_permission' ),
			)
		);

		register_rest_route(
			'csf/v1',
			'/images/upload',
			array(
				'methods'             => 'POST',
				'callback'            => array( $this, 'handle_image_upload' ),
				'permission_callback' => array( $this, 'check_push_import_permission' ),
			)
		);

		register_rest_route(
			'csf/v1',
			'/scraper-state/(?P<key>[a-z_]+)',
			array(
				array(
					'methods'             => 'GET',
					'callback'            => array( $this, 'handle_get_scraper_state' ),
					'permission_callback' => array( $this, 'check_push_import_permission' ),
					'args'                => array(
						'key' => array(
							'required'          => true,
							'validate_callback' => array( $this, 'validate_state_key' ),
						),
					),
				),
				array(
					'methods'             => 'POST',
					'callback'            => array( $this, 'handle_set_scraper_state' ),
					'permission_callback' => array( $this, 'check_push_import_permission' ),
					'args'                => array(
						'key' => array(
							'required'          => true,
							'validate_callback' => array( $this, 'validate_state_key' ),
						),
					),
				),
			)
		);
	}

	/**
	 * Check permission for push import.
	 *
	 * @since 1.0.0
	 * @param WP_REST_Request $request Request object.
	 * @return bool|WP_Error True if allowed, error otherwise.
	 */
	public function check_push_import_permission( WP_REST_Request $request ) {
		$api_key = $request->get_header( 'X-CSF-API-Key' );

		if ( empty( $api_key ) ) {
			return new WP_Error(
				'missing_api_key',
				__( 'API key is required.', 'csf-parts' ),
				array( 'status' => 401 )
			);
		}

		$configured_key = get_option( 'csf_parts_api_key', '' );

		if ( empty( $configured_key ) ) {
			return new WP_Error(
				'api_not_configured',
				__( 'API key not configured. Please configure in settings.', 'csf-parts' ),
				array( 'status' => 403 )
			);
		}

		if ( ! hash_equals( $configured_key, $api_key ) ) {
			return new WP_Error(
				'invalid_api_key',
				__( 'Invalid API key.', 'csf-parts' ),
				array( 'status' => 403 )
			);
		}

		return true;
	}

	/**
	 * Handle push import from REST API.
	 *
	 * @since 1.0.0
	 * @param WP_REST_Request $request Request object.
	 * @return WP_REST_Response|WP_Error Response or error.
	 */
	public function handle_push_import( WP_REST_Request $request ) {
		$json_data = $request->get_json_params();

		if ( empty( $json_data ) ) {
			return new WP_Error(
				'invalid_data',
				__( 'Invalid or empty JSON data.', 'csf-parts' ),
				array( 'status' => 400 )
			);
		}

		try {
			// Save to temporary file.
			$upload_dir = wp_upload_dir();
			$import_dir = $upload_dir['basedir'] . '/csf-parts-imports';

			if ( ! file_exists( $import_dir ) ) {
				wp_mkdir_p( $import_dir );
			}

			$temp_file = $import_dir . '/push-import-' . time() . '.json';
			file_put_contents( $temp_file, wp_json_encode( $json_data ) );

			// Run import.
			$this->run_import( $temp_file );

			$results = get_option( 'csf_parts_last_auto_import_results', array() );

			return rest_ensure_response(
				array(
					'success' => true,
					'message' => __( 'Import completed successfully.', 'csf-parts' ),
					'results' => $results,
				)
			);

		} catch ( Exception $e ) {
			return new WP_Error(
				'import_failed',
				$e->getMessage(),
				array( 'status' => 500 )
			);
		}
	}

	/**
	 * Handle image upload via REST API.
	 *
	 * Accepts multipart file uploads of AVIF images and saves them to
	 * wp-content/uploads/csf-parts/images/avif/. Validates filenames
	 * match the expected CSF pattern and skips files that already exist
	 * with the same size.
	 *
	 * @since 1.1.0
	 * @param WP_REST_Request $request Request object with file uploads.
	 * @return WP_REST_Response|WP_Error Response or error.
	 */
	public function handle_image_upload( WP_REST_Request $request ) {
		$files = $request->get_file_params();

		if ( empty( $files ) || empty( $files['files'] ) ) {
			return new WP_Error(
				'no_files',
				__( 'No files provided.', 'csf-parts' ),
				array( 'status' => 400 )
			);
		}

		// Set up target directory.
		$upload_dir = wp_upload_dir();
		$target_dir = $upload_dir['basedir'] . '/csf-parts/images/avif';

		if ( ! file_exists( $target_dir ) ) {
			wp_mkdir_p( $target_dir );
		}

		$uploaded = 0;
		$skipped  = 0;
		$errors   = array();

		// Normalize file data — handle both single and multi-file uploads.
		$file_names = (array) $files['files']['name'];
		$file_tmps  = (array) $files['files']['tmp_name'];
		$file_sizes = (array) $files['files']['size'];
		$file_count = count( $file_names );

		for ( $i = 0; $i < $file_count; $i++ ) {
			$name     = sanitize_file_name( $file_names[ $i ] );
			$tmp_name = $file_tmps[ $i ];
			$size     = intval( $file_sizes[ $i ] );

			// Validate filename pattern: CSF-DIGITS_DIGITS.avif
			if ( ! preg_match( '/^CSF-\d+_\d+\.avif$/', $name ) ) {
				$errors[] = sprintf(
					/* translators: %s: filename */
					__( 'Invalid filename: %s', 'csf-parts' ),
					$name
				);
				continue;
			}

			$dest_path = $target_dir . '/' . $name;

			// Skip if file exists with same size.
			if ( file_exists( $dest_path ) && filesize( $dest_path ) === $size ) {
				$skipped++;
				continue;
			}

			// Move uploaded file to target directory.
			if ( move_uploaded_file( $tmp_name, $dest_path ) ) {
				$uploaded++;
			} else {
				$errors[] = sprintf(
					/* translators: %s: filename */
					__( 'Failed to save: %s', 'csf-parts' ),
					$name
				);
			}
		}

		return rest_ensure_response(
			array(
				'success' => true,
				'results' => array(
					'uploaded' => $uploaded,
					'skipped'  => $skipped,
					'errors'   => $errors,
				),
			)
		);
	}

	/**
	 * Validate that a scraper-state key is in the allowlist.
	 *
	 * @since 1.2.0
	 * @param string $key The state key to validate.
	 * @return bool True if key is allowed.
	 */
	public function validate_state_key( string $key ): bool {
		$allowed = array( 'etags', 'manifest' );
		return in_array( $key, $allowed, true );
	}

	/**
	 * Get the filesystem path for a scraper state file.
	 *
	 * @since 1.2.0
	 * @param string $key The state key.
	 * @return string Absolute filesystem path.
	 */
	private function get_state_file_path( string $key ): string {
		$upload_dir = wp_upload_dir();
		$state_dir  = $upload_dir['basedir'] . '/csf-parts/state';

		if ( ! file_exists( $state_dir ) ) {
			wp_mkdir_p( $state_dir );
		}

		return $state_dir . '/' . $key . '.json';
	}

	/**
	 * Handle GET request for scraper state.
	 *
	 * Downloads a state file (etags.json or manifest.json) from the server.
	 * Returns 404 if the file does not exist yet.
	 *
	 * @since 1.2.0
	 * @param WP_REST_Request $request Request object.
	 * @return WP_REST_Response|WP_Error Response or error.
	 */
	public function handle_get_scraper_state( WP_REST_Request $request ) {
		$key       = $request->get_param( 'key' );
		$file_path = $this->get_state_file_path( $key );

		if ( ! file_exists( $file_path ) ) {
			return new WP_Error(
				'state_not_found',
				/* translators: %s: state key name */
				sprintf( __( 'State file not found: %s', 'csf-parts' ), $key ),
				array( 'status' => 404 )
			);
		}

		$contents = file_get_contents( $file_path );

		if ( false === $contents ) {
			return new WP_Error(
				'state_read_error',
				__( 'Failed to read state file.', 'csf-parts' ),
				array( 'status' => 500 )
			);
		}

		// Validate JSON without decoding to avoid PHP array/object coercion
		if ( null === json_decode( $contents ) ) {
			return new WP_Error(
				'state_parse_error',
				__( 'State file contains invalid JSON.', 'csf-parts' ),
				array( 'status' => 500 )
			);
		}

		// Return raw JSON to preserve exact format (avoids PHP {} -> [] coercion)
		$response = new WP_REST_Response();
		$response->set_data( json_decode( $contents ) );

		return $response;
	}

	/**
	 * Handle POST request to upload scraper state.
	 *
	 * Saves a JSON state file to wp-content/uploads/csf-parts/state/.
	 *
	 * @since 1.2.0
	 * @param WP_REST_Request $request Request object with JSON body.
	 * @return WP_REST_Response|WP_Error Response or error.
	 */
	public function handle_set_scraper_state( WP_REST_Request $request ) {
		$key  = $request->get_param( 'key' );
		$body = $request->get_body();

		if ( empty( $body ) ) {
			return new WP_Error(
				'empty_body',
				__( 'Request body is empty.', 'csf-parts' ),
				array( 'status' => 400 )
			);
		}

		// Validate JSON without decoding (avoids PHP type coercion)
		if ( null === json_decode( $body ) ) {
			return new WP_Error(
				'invalid_json',
				__( 'Request body is not valid JSON.', 'csf-parts' ),
				array( 'status' => 400 )
			);
		}

		$file_path = $this->get_state_file_path( $key );

		// Save raw body to preserve exact JSON format (avoids PHP {} -> [] coercion)
		$written = file_put_contents( $file_path, $body );

		if ( false === $written ) {
			return new WP_Error(
				'state_write_error',
				__( 'Failed to write state file.', 'csf-parts' ),
				array( 'status' => 500 )
			);
		}

		return rest_ensure_response(
			array(
				'success' => true,
				'key'     => $key,
				'size'    => $written,
			)
		);
	}

	/**
	 * Display admin notices for auto-import status.
	 *
	 * @since 1.0.0
	 */
	public function display_auto_import_notices(): void {
		$screen = get_current_screen();

		if ( ! $screen || strpos( $screen->id, 'csf-parts' ) === false ) {
			return;
		}

		// Check for recent import errors.
		$last_error = get_option( 'csf_parts_auto_import_last_error', '' );

		if ( ! empty( $last_error ) ) {
			printf(
				'<div class="notice notice-error is-dismissible"><p><strong>%s:</strong> %s</p></div>',
				esc_html__( 'Auto Import Error', 'csf-parts' ),
				esc_html( $last_error )
			);
		}

		// Display last successful import info.
		$last_import = get_option( 'csf_parts_last_auto_import', '' );
		$results     = get_option( 'csf_parts_last_auto_import_results', array() );

		if ( ! empty( $last_import ) && ! empty( $results ) ) {
			$time_ago = human_time_diff( strtotime( $last_import ), current_time( 'timestamp' ) );

			printf(
				'<div class="notice notice-info"><p><strong>%s:</strong> %s (%s: %d, %s: %d, %s: %d)</p></div>',
				esc_html__( 'Last Auto Import', 'csf-parts' ),
				/* translators: %s: time ago */
				sprintf( esc_html__( '%s ago', 'csf-parts' ), $time_ago ),
				esc_html__( 'Created', 'csf-parts' ),
				intval( $results['created'] ?? 0 ),
				esc_html__( 'Updated', 'csf-parts' ),
				intval( $results['updated'] ?? 0 ),
				esc_html__( 'Skipped', 'csf-parts' ),
				intval( $results['skipped'] ?? 0 )
			);
		}
	}

	/**
	 * Generate API key.
	 *
	 * @since 1.0.0
	 * @return string Generated API key.
	 */
	public static function generate_api_key(): string {
		return bin2hex( random_bytes( 32 ) );
	}
}
