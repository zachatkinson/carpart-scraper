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
	 * Register REST API endpoint for push imports.
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
