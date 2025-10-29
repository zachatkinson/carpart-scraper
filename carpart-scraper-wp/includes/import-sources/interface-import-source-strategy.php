<?php
/**
 * Import Source Strategy Interface.
 *
 * Defines contract for different import source strategies.
 * Follows Open/Closed Principle - new sources can be added without modifying existing code.
 *
 * @package CSF_Parts_Catalog
 * @since   1.0.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

/**
 * Interface Import_Source_Strategy
 *
 * @since 1.0.0
 */
interface Import_Source_Strategy {

	/**
	 * Fetch JSON content from source.
	 *
	 * @since 1.0.0
	 * @return string Path to local JSON file.
	 * @throws Exception If fetch fails.
	 */
	public function fetch(): string;

	/**
	 * Validate configuration for this source.
	 *
	 * @since 1.0.0
	 * @return bool True if configuration is valid.
	 * @throws Exception If configuration is invalid.
	 */
	public function validate_configuration(): bool;

	/**
	 * Get source type identifier.
	 *
	 * @since 1.0.0
	 * @return string Source type (e.g., 'url', 'directory').
	 */
	public function get_type(): string;
}
