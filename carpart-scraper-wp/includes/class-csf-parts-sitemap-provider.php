<?php
/**
 * Sitemap Provider for Virtual Part Pages.
 *
 * Integrates with WordPress native sitemap system (5.5+) to include
 * all virtual part URLs (canonical + vehicle-specific).
 *
 * @package CSF_Parts_Catalog
 * @since   2.0.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

/**
 * Class CSF_Parts_Sitemap_Provider
 *
 * Extends WordPress core sitemap provider to add virtual part URLs.
 */
class CSF_Parts_Sitemap_Provider extends WP_Sitemaps_Provider {

	/**
	 * URL handler instance.
	 *
	 * @var CSF_Parts_URL_Handler
	 */
	private $url_handler;

	/**
	 * Database instance.
	 *
	 * @var CSF_Parts_Database
	 */
	private $database;

	/**
	 * Maximum URLs per sitemap page.
	 *
	 * WordPress recommends 2000, we'll use a conservative 2000.
	 *
	 * @var int
	 */
	private const MAX_URLS_PER_PAGE = 2000;

	/**
	 * Constructor.
	 */
	public function __construct() {
		$this->name        = 'csfparts';
		$this->object_type = 'csf_part';

		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-url-handler.php';
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-database.php';

		$this->url_handler = new CSF_Parts_URL_Handler();
		$this->database    = new CSF_Parts_Database();
	}

	/**
	 * Get object subtypes.
	 *
	 * Returns the list of subtypes for this provider.
	 * We use a single 'part' subtype for all CSF parts.
	 *
	 * @since 2.0.0
	 * @return array Array of subtype objects.
	 */
	public function get_object_subtypes(): array {
		return array(
			'part' => (object) array(
				'name'  => 'part',
				'label' => 'CSF Parts',
			),
		);
	}

	/**
	 * Get total URL count.
	 *
	 * @since 2.0.0
	 * @return int Total number of URLs.
	 */
	private function get_total_url_count(): int {
		global $wpdb;
		$table = $wpdb->prefix . 'csf_parts';

		// Get part count.
		$part_count = (int) $wpdb->get_var( "SELECT COUNT(*) FROM {$table}" );

		if ( $part_count === 0 ) {
			return 0;
		}

		// Get total vehicle compatibility count.
		$vehicle_count = (int) $wpdb->get_var(
			"SELECT SUM(JSON_LENGTH(compatibility))
			FROM {$table}
			WHERE compatibility IS NOT NULL
			AND compatibility != ''"
		);

		// Total = canonical URLs + vehicle-specific URLs.
		return $part_count + $vehicle_count;
	}

	/**
	 * Get sitemap entries for a specific page.
	 *
	 * @since 2.0.0
	 * @param int    $page_num        Page number (1-indexed).
	 * @param string $object_subtype  Object subtype (not used, we have single 'part' type).
	 * @return array Array of sitemap entries.
	 */
	public function get_url_list( $page_num, $object_subtype = '' ): array {
		global $wpdb;
		$table = $wpdb->prefix . 'csf_parts';

		// Calculate offset.
		$offset = ( $page_num - 1 ) * self::MAX_URLS_PER_PAGE;

		// Get all URLs (we'll need to paginate manually).
		$all_urls = $this->url_handler->get_all_virtual_urls();

		// Slice for current page.
		$page_urls = array_slice( $all_urls, $offset, self::MAX_URLS_PER_PAGE );

		// Convert to WordPress sitemap format.
		$sitemap_entries = array();

		foreach ( $page_urls as $url ) {
			$sitemap_entries[] = array(
				'loc'     => esc_url( $url ),
				'lastmod' => $this->get_last_modified_date(),
			);
		}

		return $sitemap_entries;
	}

	/**
	 * Get maximum number of pages.
	 *
	 * @since 2.0.0
	 * @return int Number of pages.
	 */
	public function get_max_num_pages( $object_subtype = '' ): int {
		$total_urls = $this->get_total_url_count();

		if ( $total_urls === 0 ) {
			return 0;
		}

		return (int) ceil( $total_urls / self::MAX_URLS_PER_PAGE );
	}

	/**
	 * Get last modified date for parts.
	 *
	 * @since 2.0.0
	 * @return string Last modified date in W3C format.
	 */
	private function get_last_modified_date(): string {
		global $wpdb;
		$table = $wpdb->prefix . 'csf_parts';

		// Get most recent updated_at timestamp.
		$last_modified = $wpdb->get_var( "SELECT MAX(updated_at) FROM {$table}" );

		if ( ! $last_modified ) {
			$last_modified = current_time( 'mysql' );
		}

		// Convert to W3C format (ISO 8601).
		return mysql2date( 'c', $last_modified, false );
	}
}
