<?php
/**
 * Import Manager.
 *
 * Handles import UI logic, file uploads, and AJAX processing for imports.
 *
 * @package CSF_Parts_Catalog
 * @since   1.0.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

/**
 * Class CSF_Parts_Import_Manager
 */
class CSF_Parts_Import_Manager {

	/**
	 * Constructor.
	 */
	public function __construct() {
		add_action( 'wp_ajax_csf_parts_upload_json', array( $this, 'ajax_upload_json' ) );
		add_action( 'wp_ajax_csf_parts_import_json', array( $this, 'ajax_import_json' ) );
		add_action( 'wp_ajax_csf_parts_get_import_status', array( $this, 'ajax_get_import_status' ) );
	}

	/**
	 * Handle JSON file upload via AJAX.
	 *
	 * @since 1.0.0
	 */
	public function ajax_upload_json(): void {
		// Verify nonce.
		check_ajax_referer( 'csf_parts_import_nonce', 'nonce' );

		// Check capabilities.
		if ( ! current_user_can( 'manage_options' ) ) {
			wp_send_json_error(
				array(
					'message' => __( 'You do not have permission to perform this action.', CSF_Parts_Constants::TEXT_DOMAIN ),
				)
			);
		}

		// Check if file was uploaded.
		if ( empty( $_FILES['file'] ) ) {
			wp_send_json_error(
				array(
					'message' => __( 'No file uploaded.', CSF_Parts_Constants::TEXT_DOMAIN ),
				)
			);
		}

		$file = $_FILES['file'];

		// Validate file type.
		$file_type = wp_check_filetype( $file['name'] );
		if ( 'json' !== $file_type['ext'] ) {
			wp_send_json_error(
				array(
					'message' => __( 'Invalid file type. Only JSON files are allowed.', CSF_Parts_Constants::TEXT_DOMAIN ),
				)
			);
		}

		// Validate file size (max 50MB).
		$max_size = CSF_Parts_Constants::UPLOAD_MAX_SIZE_BYTES;
		if ( $file['size'] > $max_size ) {
			wp_send_json_error(
				array(
					'message' => __( 'File is too large. Maximum size is 50MB.', CSF_Parts_Constants::TEXT_DOMAIN ),
				)
			);
		}

		// Move file to uploads directory.
		$upload_dir = wp_upload_dir();
		$import_dir = $upload_dir['basedir'] . '/csf-parts-imports';

		// Create directory if it doesn't exist.
		if ( ! file_exists( $import_dir ) ) {
			wp_mkdir_p( $import_dir );
		}

		$filename      = sanitize_file_name( $file['name'] );
		$timestamp     = time();
		$unique_name   = $timestamp . '-' . $filename;
		$target_path   = $import_dir . '/' . $unique_name;

		// Move uploaded file.
		if ( ! move_uploaded_file( $file['tmp_name'], $target_path ) ) {
			wp_send_json_error(
				array(
					'message' => __( 'Failed to save uploaded file.', CSF_Parts_Constants::TEXT_DOMAIN ),
				)
			);
		}

		// Validate JSON structure.
		$json_content = file_get_contents( $target_path );
		$data         = json_decode( $json_content, true );

		if ( json_last_error() !== JSON_ERROR_NONE ) {
			unlink( $target_path );
			wp_send_json_error(
				array(
					'message' => sprintf(
						/* translators: %s: JSON error message */
						__( 'Invalid JSON file: %s', CSF_Parts_Constants::TEXT_DOMAIN ),
						json_last_error_msg()
					),
				)
			);
		}

		// Count parts.
		$parts_count = count( $data['parts'] ?? array() );

		// Save file info to option for later processing.
		$file_info = array(
			'filename'    => $unique_name,
			'path'        => $target_path,
			'uploaded_at' => current_time( 'mysql' ),
			'parts_count' => $parts_count,
			'status'      => 'pending',
		);

		update_option( 'csf_parts_import_file', $file_info );

		wp_send_json_success(
			array(
				'message'     => __( 'File uploaded successfully.', CSF_Parts_Constants::TEXT_DOMAIN ),
				'filename'    => $filename,
				'parts_count' => $parts_count,
			)
		);
	}

	/**
	 * Handle JSON import via AJAX.
	 *
	 * @since 1.0.0
	 */
	public function ajax_import_json(): void {
		// Verify nonce.
		check_ajax_referer( 'csf_parts_import_nonce', 'nonce' );

		// Check capabilities.
		if ( ! current_user_can( 'manage_options' ) ) {
			wp_send_json_error(
				array(
					'message' => __( 'You do not have permission to perform this action.', CSF_Parts_Constants::TEXT_DOMAIN ),
				)
			);
		}

		// Get file info from option.
		$file_info = get_option( 'csf_parts_import_file' );

		if ( ! $file_info || ! file_exists( $file_info['path'] ) ) {
			wp_send_json_error(
				array(
					'message' => __( 'No file available for import.', CSF_Parts_Constants::TEXT_DOMAIN ),
				)
			);
		}

		// Update status to processing.
		$file_info['status']      = 'processing';
		$file_info['started_at']  = current_time( 'mysql' );
		update_option( 'csf_parts_import_file', $file_info );

		// Create importer instance.
		$importer = new CSF_Parts_JSON_Importer();

		// Set batch size from request or use default.
		$batch_size = isset( $_POST['batch_size'] ) ? intval( $_POST['batch_size'] ) : 50;
		$importer->set_batch_size( $batch_size );

		// Perform import.
		$results = $importer->import_from_file( $file_info['path'] );

		// Update status.
		$file_info['status']      = 'completed';
		$file_info['completed_at'] = current_time( 'mysql' );
		$file_info['results']     = $results;
		update_option( 'csf_parts_import_file', $file_info );

		// Save to import log.
		$this->save_import_log( $file_info );

		wp_send_json_success(
			array(
				'message' => __( 'Import completed successfully.', CSF_Parts_Constants::TEXT_DOMAIN ),
				'results' => $results,
			)
		);
	}

	/**
	 * Get import status via AJAX.
	 *
	 * @since 1.0.0
	 */
	public function ajax_get_import_status(): void {
		// Verify nonce.
		check_ajax_referer( 'csf_parts_import_nonce', 'nonce' );

		// Check capabilities.
		if ( ! current_user_can( 'manage_options' ) ) {
			wp_send_json_error(
				array(
					'message' => __( 'You do not have permission to perform this action.', CSF_Parts_Constants::TEXT_DOMAIN ),
				)
			);
		}

		// Get file info.
		$file_info = get_option( 'csf_parts_import_file' );

		if ( ! $file_info ) {
			wp_send_json_success(
				array(
					'status' => 'none',
				)
			);
		}

		wp_send_json_success(
			array(
				'status'      => $file_info['status'],
				'filename'    => $file_info['filename'] ?? '',
				'parts_count' => $file_info['parts_count'] ?? 0,
				'results'     => $file_info['results'] ?? null,
			)
		);
	}

	/**
	 * Save import log entry.
	 *
	 * @since 1.0.0
	 * @param array $file_info File info with results.
	 */
	private function save_import_log( array $file_info ): void {
		$logs = get_option( 'csf_parts_import_logs', array() );

		// Add new log entry.
		$logs[] = array(
			'filename'     => $file_info['filename'],
			'uploaded_at'  => $file_info['uploaded_at'],
			'started_at'   => $file_info['started_at'] ?? null,
			'completed_at' => $file_info['completed_at'] ?? null,
			'parts_count'  => $file_info['parts_count'],
			'results'      => $file_info['results'],
		);

		// Keep only last 50 logs.
		if ( count( $logs ) > 50 ) {
			$logs = array_slice( $logs, -50 );
		}

		update_option( 'csf_parts_import_logs', $logs );
	}

	/**
	 * Get import logs.
	 *
	 * @since 1.0.0
	 * @return array Import logs.
	 */
	public static function get_import_logs(): array {
		return get_option( 'csf_parts_import_logs', array() );
	}

	/**
	 * Clear import logs.
	 *
	 * @since 1.0.0
	 */
	public static function clear_import_logs(): void {
		delete_option( 'csf_parts_import_logs' );
	}

	/**
	 * Delete uploaded file and reset import state.
	 *
	 * @since 1.0.0
	 */
	public static function reset_import(): void {
		$file_info = get_option( 'csf_parts_import_file' );

		if ( $file_info && isset( $file_info['path'] ) && file_exists( $file_info['path'] ) ) {
			unlink( $file_info['path'] );
		}

		delete_option( 'csf_parts_import_file' );
	}
}
