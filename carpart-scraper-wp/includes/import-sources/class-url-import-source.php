<?php
/**
 * URL Import Source Strategy.
 *
 * Fetches JSON from remote URL.
 * Single Responsibility: Only handles URL fetching logic.
 *
 * @package CSF_Parts_Catalog
 * @since   1.0.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

/**
 * Class URL_Import_Source
 *
 * @since 1.0.0
 */
class URL_Import_Source implements Import_Source_Strategy {

	/**
	 * Remote URL to fetch from.
	 *
	 * @var string
	 */
	private string $url;

	/**
	 * Timeout in seconds.
	 *
	 * @var int
	 */
	private int $timeout;

	/**
	 * Import directory path.
	 *
	 * @var string
	 */
	private string $import_directory;

	/**
	 * Constructor.
	 *
	 * @since 1.0.0
	 * @param string $url Remote URL.
	 * @param int    $timeout Timeout in seconds.
	 */
	public function __construct( string $url, int $timeout = 60 ) {
		$this->url     = $url;
		$this->timeout = $timeout;

		$upload_dir            = wp_upload_dir();
		$this->import_directory = $upload_dir['basedir'] . '/csf-parts-imports';
	}

	/**
	 * Fetch JSON from remote URL.
	 *
	 * @since 1.0.0
	 * @return string Path to downloaded file.
	 * @throws Exception If fetch fails.
	 */
	public function fetch(): string {
		$this->validate_configuration();

		$response = wp_remote_get(
			$this->url,
			array(
				'timeout' => $this->timeout,
				'headers' => array(
					'Accept' => 'application/json',
				),
			)
		);

		if ( is_wp_error( $response ) ) {
			throw new Exception(
				sprintf(
					/* translators: %s: error message */
					__( 'Failed to fetch remote URL: %s', CSF_Parts_Constants::TEXT_DOMAIN ),
					$response->get_error_message()
				)
			);
		}

		$status_code = wp_remote_retrieve_response_code( $response );
		if ( CSF_Parts_Constants::HTTP_OK !== $status_code ) {
			throw new Exception(
				sprintf(
					/* translators: %d: HTTP status code */
					__( 'HTTP error %d when fetching remote URL', CSF_Parts_Constants::TEXT_DOMAIN ),
					$status_code
				)
			);
		}

		$json_content = wp_remote_retrieve_body( $response );

		$this->validate_json( $json_content );

		return $this->save_to_file( $json_content );
	}

	/**
	 * Validate configuration.
	 *
	 * @since 1.0.0
	 * @return bool True if valid.
	 * @throws Exception If configuration invalid.
	 */
	public function validate_configuration(): bool {
		if ( empty( $this->url ) ) {
			throw new Exception(
				__( 'Remote URL is not configured', CSF_Parts_Constants::TEXT_DOMAIN )
			);
		}

		if ( ! filter_var( $this->url, FILTER_VALIDATE_URL ) ) {
			throw new Exception(
				__( 'Remote URL is not a valid URL', CSF_Parts_Constants::TEXT_DOMAIN )
			);
		}

		// Enforce HTTPS for security.
		if ( 0 !== strpos( $this->url, 'https://' ) ) {
			throw new Exception(
				__( 'Remote URL must use HTTPS', CSF_Parts_Constants::TEXT_DOMAIN )
			);
		}

		return true;
	}

	/**
	 * Get source type.
	 *
	 * @since 1.0.0
	 * @return string Source type.
	 */
	public function get_type(): string {
		return CSF_Parts_Constants::IMPORT_SOURCE_URL;
	}

	/**
	 * Validate JSON content.
	 *
	 * @since 1.0.0
	 * @param string $json_content JSON content.
	 * @throws Exception If JSON invalid.
	 */
	private function validate_json( string $json_content ): void {
		json_decode( $json_content, true );

		if ( JSON_ERROR_NONE !== json_last_error() ) {
			throw new Exception(
				sprintf(
					/* translators: %s: JSON error message */
					__( 'Invalid JSON received: %s', CSF_Parts_Constants::TEXT_DOMAIN ),
					json_last_error_msg()
				)
			);
		}
	}

	/**
	 * Save content to temporary file.
	 *
	 * @since 1.0.0
	 * @param string $content File content.
	 * @return string Path to saved file.
	 * @throws Exception If save fails.
	 */
	private function save_to_file( string $content ): string {
		if ( ! file_exists( $this->import_directory ) ) {
			wp_mkdir_p( $this->import_directory );
		}

		$filename  = 'url-import-' . time() . '.json';
		$file_path = $this->import_directory . '/' . $filename;

		$bytes_written = file_put_contents( $file_path, $content );

		if ( false === $bytes_written ) {
			throw new Exception(
				__( 'Failed to save downloaded file', CSF_Parts_Constants::TEXT_DOMAIN )
			);
		}

		return $file_path;
	}
}
