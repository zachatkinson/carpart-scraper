<?php
/**
 * Plugin Constants.
 *
 * Centralizes all magic strings and numbers as constants.
 * Follows DRY principle - single source of truth for all values.
 *
 * @package CSF_Parts_Catalog
 * @since   1.0.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

/**
 * Class CSF_Parts_Constants
 *
 * @since 1.0.0
 */
final class CSF_Parts_Constants {

	/**
	 * Post type slug.
	 */
	public const POST_TYPE = 'csf_part';

	/**
	 * Taxonomy slugs.
	 */
	public const TAXONOMY_CATEGORY = 'part_category';
	public const TAXONOMY_MAKE     = 'vehicle_make';
	public const TAXONOMY_MODEL    = 'vehicle_model';
	public const TAXONOMY_YEAR     = 'vehicle_year';

	/**
	 * Meta field keys.
	 */
	public const META_SKU            = '_csf_sku';
	public const META_PRICE          = '_csf_price';
	public const META_MANUFACTURER   = '_csf_manufacturer';
	public const META_IN_STOCK       = '_csf_in_stock';
	public const META_POSITION       = '_csf_position';
	public const META_SPECIFICATIONS = '_csf_specifications';
	public const META_FEATURES       = '_csf_features';
	public const META_TECH_NOTES     = '_csf_tech_notes';
	public const META_SCRAPED_AT     = '_csf_scraped_at';
	public const META_ORIGINAL_URL   = '_csf_original_url';
	public const META_COMPATIBILITY  = '_csf_compatibility';

	// Vehicle-specific meta fields (for SEO: one post per vehicle).
	public const META_VEHICLE_YEAR   = '_csf_vehicle_year';
	public const META_VEHICLE_MAKE   = '_csf_vehicle_make';
	public const META_VEHICLE_MODEL  = '_csf_vehicle_model';
	public const META_CANONICAL_POST = '_csf_canonical_post_id';

	/**
	 * REST API namespace.
	 */
	public const REST_NAMESPACE = 'csf/v1';

	/**
	 * Cache settings.
	 */
	public const CACHE_DURATION_DEFAULT = 3600; // 1 hour in seconds
	public const CACHE_DURATION_MIN     = 60;   // 1 minute
	public const CACHE_DURATION_MAX     = 86400; // 24 hours

	/**
	 * Import settings.
	 */
	public const IMPORT_BATCH_SIZE_DEFAULT = 50;
	public const IMPORT_BATCH_SIZE_MIN     = 1;
	public const IMPORT_BATCH_SIZE_MAX     = 200;

	/**
	 * File upload limits.
	 */
	public const UPLOAD_MAX_SIZE_BYTES = 52428800; // 50MB
	public const UPLOAD_ALLOWED_TYPES  = array( 'json' );

	/**
	 * Cron schedule names.
	 */
	public const CRON_SCHEDULE_15_MIN = 'csf_every_15_minutes';
	public const CRON_SCHEDULE_30_MIN = 'csf_every_30_minutes';
	public const CRON_SCHEDULE_6_HOUR = 'csf_every_6_hours';
	public const CRON_SCHEDULE_12_HOUR = 'csf_every_12_hours';

	/**
	 * Cron schedule intervals (seconds).
	 */
	public const INTERVAL_15_MINUTES = 900;   // 15 * 60
	public const INTERVAL_30_MINUTES = 1800;  // 30 * 60
	public const INTERVAL_6_HOURS    = 21600; // 6 * 60 * 60
	public const INTERVAL_12_HOURS   = 43200; // 12 * 60 * 60

	/**
	 * Import source types.
	 */
	public const IMPORT_SOURCE_URL       = 'url';
	public const IMPORT_SOURCE_DIRECTORY = 'directory';

	/**
	 * HTTP status codes.
	 */
	public const HTTP_OK                     = 200;
	public const HTTP_CREATED                = 201;
	public const HTTP_BAD_REQUEST            = 400;
	public const HTTP_UNAUTHORIZED           = 401;
	public const HTTP_FORBIDDEN              = 403;
	public const HTTP_NOT_FOUND              = 404;
	public const HTTP_TOO_MANY_REQUESTS      = 429;
	public const HTTP_INTERNAL_ERROR         = 500;
	public const HTTP_INTERNAL_SERVER_ERROR  = 500;

	/**
	 * API pagination defaults.
	 */
	public const PAGINATION_DEFAULT_PER_PAGE = 20;
	public const PAGINATION_MIN_PER_PAGE     = 1;
	public const PAGINATION_MAX_PER_PAGE     = 100;

	/**
	 * Text domain for translations.
	 */
	public const TEXT_DOMAIN = 'csf-parts';

	/**
	 * Prevent instantiation.
	 *
	 * @since 1.0.0
	 */
	private function __construct() {
		// Constants class should never be instantiated.
	}
}
