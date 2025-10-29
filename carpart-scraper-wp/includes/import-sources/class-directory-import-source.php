<?php
/**
 * Directory Import Source Strategy.
 *
 * Fetches latest JSON from local directory.
 * Single Responsibility: Only handles directory monitoring logic.
 *
 * @package CSF_Parts_Catalog
 * @since   1.0.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

/**
 * Class Directory_Import_Source
 *
 * @since 1.0.0
 */
class Directory_Import_Source implements Import_Source_Strategy {

	/**
	 * Directory path to monitor.
	 *
	 * @var string
	 */
	private string $directory_path;

	/**
	 * Constructor.
	 *
	 * @since 1.0.0
	 * @param string $directory_path Path to directory containing JSON files.
	 */
	public function __construct( string $directory_path ) {
		$this->directory_path = $directory_path;
	}

	/**
	 * Fetch latest JSON file from directory.
	 *
	 * @since 1.0.0
	 * @return string Path to latest JSON file.
	 * @throws Exception If no files found or access fails.
	 */
	public function fetch(): string {
		$this->validate_configuration();

		$files = $this->find_json_files();

		if ( empty( $files ) ) {
			throw new Exception(
				__( 'No JSON files found in import directory', CSF_Parts_Constants::TEXT_DOMAIN )
			);
		}

		$latest_file = $this->get_latest_file( $files );

		$this->validate_file_not_imported( $latest_file );

		return $latest_file;
	}

	/**
	 * Validate configuration.
	 *
	 * @since 1.0.0
	 * @return bool True if valid.
	 * @throws Exception If configuration invalid.
	 */
	public function validate_configuration(): bool {
		if ( empty( $this->directory_path ) ) {
			throw new Exception(
				__( 'Import directory is not configured', CSF_Parts_Constants::TEXT_DOMAIN )
			);
		}

		if ( ! file_exists( $this->directory_path ) ) {
			throw new Exception(
				sprintf(
					/* translators: %s: directory path */
					__( 'Import directory does not exist: %s', CSF_Parts_Constants::TEXT_DOMAIN ),
					$this->directory_path
				)
			);
		}

		if ( ! is_dir( $this->directory_path ) ) {
			throw new Exception(
				__( 'Import path is not a directory', CSF_Parts_Constants::TEXT_DOMAIN )
			);
		}

		if ( ! is_readable( $this->directory_path ) ) {
			throw new Exception(
				__( 'Import directory is not readable', CSF_Parts_Constants::TEXT_DOMAIN )
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
		return CSF_Parts_Constants::IMPORT_SOURCE_DIRECTORY;
	}

	/**
	 * Find all JSON files in directory.
	 *
	 * @since 1.0.0
	 * @return array Array of file paths.
	 */
	private function find_json_files(): array {
		$pattern = rtrim( $this->directory_path, '/' ) . '/*.json';
		$files   = glob( $pattern );

		return is_array( $files ) ? $files : array();
	}

	/**
	 * Get latest file by modification time.
	 *
	 * @since 1.0.0
	 * @param array $files Array of file paths.
	 * @return string Path to latest file.
	 */
	private function get_latest_file( array $files ): string {
		usort(
			$files,
			function ( string $a, string $b ): int {
				return filemtime( $b ) - filemtime( $a );
			}
		);

		return $files[0];
	}

	/**
	 * Validate file has not already been imported.
	 *
	 * @since 1.0.0
	 * @param string $file_path File path to check.
	 * @throws Exception If file already imported.
	 */
	private function validate_file_not_imported( string $file_path ): void {
		$last_imported_file = get_option( 'csf_parts_last_imported_file', '' );

		if ( $file_path === $last_imported_file ) {
			throw new Exception(
				__( 'Latest file has already been imported', CSF_Parts_Constants::TEXT_DOMAIN )
			);
		}
	}
}
