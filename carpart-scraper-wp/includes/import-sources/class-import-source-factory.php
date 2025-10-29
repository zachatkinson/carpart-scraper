<?php
/**
 * Import Source Factory.
 *
 * Creates appropriate import source strategy based on configuration.
 * Follows Factory Pattern and Open/Closed Principle.
 *
 * @package CSF_Parts_Catalog
 * @since   1.0.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

/**
 * Class Import_Source_Factory
 *
 * @since 1.0.0
 */
class Import_Source_Factory {

	/**
	 * Create import source strategy from WordPress options.
	 *
	 * @since 1.0.0
	 * @return Import_Source_Strategy Configured strategy instance.
	 * @throws Exception If source type unknown or configuration invalid.
	 */
	public static function create_from_options(): Import_Source_Strategy {
		$source_type = get_option( 'csf_parts_import_source', CSF_Parts_Constants::IMPORT_SOURCE_URL );

		return self::create( $source_type );
	}

	/**
	 * Create import source strategy.
	 *
	 * @since 1.0.0
	 * @param string $source_type Source type identifier.
	 * @return Import_Source_Strategy Strategy instance.
	 * @throws Exception If source type unknown.
	 */
	public static function create( string $source_type ): Import_Source_Strategy {
		switch ( $source_type ) {
			case CSF_Parts_Constants::IMPORT_SOURCE_URL:
				return self::create_url_source();

			case CSF_Parts_Constants::IMPORT_SOURCE_DIRECTORY:
				return self::create_directory_source();

			default:
				throw new Exception(
					sprintf(
						/* translators: %s: source type */
						__( 'Unknown import source type: %s', CSF_Parts_Constants::TEXT_DOMAIN ),
						$source_type
					)
				);
		}
	}

	/**
	 * Create URL import source.
	 *
	 * @since 1.0.0
	 * @return URL_Import_Source Configured URL source.
	 */
	private static function create_url_source(): URL_Import_Source {
		$url = get_option( 'csf_parts_remote_url', '' );

		return new URL_Import_Source( $url );
	}

	/**
	 * Create directory import source.
	 *
	 * @since 1.0.0
	 * @return Directory_Import_Source Configured directory source.
	 */
	private static function create_directory_source(): Directory_Import_Source {
		$directory = get_option( 'csf_parts_import_directory', '' );

		return new Directory_Import_Source( $directory );
	}

	/**
	 * Get available source types.
	 *
	 * @since 1.0.0
	 * @return array Array of available source types with labels.
	 */
	public static function get_available_types(): array {
		return array(
			CSF_Parts_Constants::IMPORT_SOURCE_URL       => __( 'Remote URL', CSF_Parts_Constants::TEXT_DOMAIN ),
			CSF_Parts_Constants::IMPORT_SOURCE_DIRECTORY => __( 'Local Directory', CSF_Parts_Constants::TEXT_DOMAIN ),
		);
	}
}
