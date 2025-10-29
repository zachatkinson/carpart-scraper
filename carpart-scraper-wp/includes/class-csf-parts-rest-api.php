<?php
/**
 * REST API Endpoints (V2 Architecture).
 *
 * Registers custom REST API endpoints for parts and vehicle data.
 * Uses custom database tables instead of WordPress post types.
 *
 * @package CSF_Parts_Catalog
 * @since   2.0.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

/**
 * Class CSF_Parts_REST_API
 *
 * Provides REST API endpoints for querying parts data from custom database tables.
 */
class CSF_Parts_REST_API {

	/**
	 * API namespace.
	 *
	 * @var string
	 */
	private string $namespace = CSF_Parts_Constants::REST_NAMESPACE;

	/**
	 * Database instance.
	 *
	 * @var CSF_Parts_Database
	 */
	private CSF_Parts_Database $database;

	/**
	 * Constructor.
	 */
	public function __construct() {
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-database.php';
		$this->database = new CSF_Parts_Database();

		add_action( 'rest_api_init', array( $this, 'register_routes' ) );
	}

	/**
	 * Register REST API routes.
	 *
	 * @since 2.0.0
	 */
	public function register_routes(): void {
		// Get parts with filters.
		register_rest_route(
			$this->namespace,
			'/parts',
			array(
				'methods'             => 'GET',
				'callback'            => array( $this, 'get_parts' ),
				'permission_callback' => '__return_true',
				'args'                => $this->get_parts_query_params(),
			)
		);

		// Get single part by SKU.
		register_rest_route(
			$this->namespace,
			'/parts/(?P<sku>[a-zA-Z0-9\-]+)',
			array(
				'methods'             => 'GET',
				'callback'            => array( $this, 'get_part_by_sku' ),
				'permission_callback' => '__return_true',
			)
		);

		// Get all vehicle makes.
		register_rest_route(
			$this->namespace,
			'/vehicles/makes',
			array(
				'methods'             => 'GET',
				'callback'            => array( $this, 'get_vehicle_makes' ),
				'permission_callback' => '__return_true',
			)
		);

		// Get vehicle models.
		register_rest_route(
			$this->namespace,
			'/vehicles/models',
			array(
				'methods'             => 'GET',
				'callback'            => array( $this, 'get_vehicle_models' ),
				'permission_callback' => '__return_true',
				'args'                => array(
					'make' => array(
						'required'          => true,
						'validate_callback' => function ( $param ) {
							return ! empty( $param );
						},
					),
					'year' => array(
						'required'          => false,
						'validate_callback' => function ( $param ) {
							return is_numeric( $param );
						},
					),
				),
			)
		);

		// Get all vehicle years.
		register_rest_route(
			$this->namespace,
			'/vehicles/years',
			array(
				'methods'             => 'GET',
				'callback'            => array( $this, 'get_vehicle_years' ),
				'permission_callback' => '__return_true',
			)
		);

		// Get compatible parts for vehicle.
		register_rest_route(
			$this->namespace,
			'/compatibility',
			array(
				'methods'             => 'GET',
				'callback'            => array( $this, 'get_compatibility' ),
				'permission_callback' => '__return_true',
				'args'                => array(
					'make'  => array(
						'required'          => true,
						'validate_callback' => function ( $param ) {
							return ! empty( $param );
						},
					),
					'model' => array(
						'required'          => true,
						'validate_callback' => function ( $param ) {
							return ! empty( $param );
						},
					),
					'year'  => array(
						'required'          => true,
						'validate_callback' => function ( $param ) {
							return is_numeric( $param );
						},
					),
				),
			)
		);
	}

	/**
	 * Get parts query parameters.
	 *
	 * @since 2.0.0
	 * @return array Query parameters.
	 */
	private function get_parts_query_params(): array {
		return array(
			'search'   => array(
				'description' => __( 'Search query for part name or SKU.', CSF_Parts_Constants::TEXT_DOMAIN ),
				'type'        => 'string',
			),
			'category' => array(
				'description' => __( 'Filter by category name.', CSF_Parts_Constants::TEXT_DOMAIN ),
				'type'        => 'string',
			),
			'make'     => array(
				'description' => __( 'Filter by vehicle make.', CSF_Parts_Constants::TEXT_DOMAIN ),
				'type'        => 'string',
			),
			'model'    => array(
				'description' => __( 'Filter by vehicle model.', CSF_Parts_Constants::TEXT_DOMAIN ),
				'type'        => 'string',
			),
			'year'     => array(
				'description' => __( 'Filter by vehicle year.', CSF_Parts_Constants::TEXT_DOMAIN ),
				'type'        => 'integer',
			),
			'per_page' => array(
				'description' => __( 'Number of results per page.', CSF_Parts_Constants::TEXT_DOMAIN ),
				'type'        => 'integer',
				'default'     => 20,
			),
			'page'     => array(
				'description' => __( 'Page number.', CSF_Parts_Constants::TEXT_DOMAIN ),
				'type'        => 'integer',
				'default'     => 1,
			),
		);
	}

	/**
	 * Get parts endpoint.
	 *
	 * @since 2.0.0
	 * @param WP_REST_Request $request Request object.
	 * @return WP_REST_Response|WP_Error Response object or error.
	 */
	public function get_parts( WP_REST_Request $request ) {
		$params = $request->get_params();

		// Build filter array for database query.
		$filters = array(
			'search'   => sanitize_text_field( $params['search'] ?? '' ),
			'category' => sanitize_text_field( $params['category'] ?? '' ),
			'make'     => sanitize_text_field( $params['make'] ?? '' ),
			'model'    => sanitize_text_field( $params['model'] ?? '' ),
			'year'     => intval( $params['year'] ?? 0 ),
			'per_page' => intval( $params['per_page'] ?? 20 ),
			'page'     => intval( $params['page'] ?? 1 ),
		);

		// Check cache.
		$cache_key = 'csf_parts_' . md5( wp_json_encode( $filters ) );
		$cached    = $this->get_cached_response( $cache_key );

		if ( false !== $cached ) {
			return rest_ensure_response( $cached );
		}

		// Execute query via database class.
		$result = $this->database->query_parts( $filters );

		// Format parts for API response.
		$parts = array_map( array( $this, 'format_part' ), $result['parts'] );

		// Calculate total pages.
		$total_pages = $filters['per_page'] > 0 ? ceil( $result['total'] / $filters['per_page'] ) : 1;

		$response = array(
			'parts'       => $parts,
			'total'       => $result['total'],
			'page'        => $filters['page'],
			'per_page'    => $filters['per_page'],
			'total_pages' => $total_pages,
		);

		// Cache response.
		$this->cache_response( $cache_key, $response );

		return rest_ensure_response( $response );
	}

	/**
	 * Get single part by SKU.
	 *
	 * @since 2.0.0
	 * @param WP_REST_Request $request Request object.
	 * @return WP_REST_Response|WP_Error Response object or error.
	 */
	public function get_part_by_sku( WP_REST_Request $request ) {
		$sku = sanitize_text_field( $request->get_param( 'sku' ) );

		// Check cache.
		$cache_key = 'csf_part_sku_' . $sku;
		$cached    = $this->get_cached_response( $cache_key );

		if ( false !== $cached ) {
			return rest_ensure_response( $cached );
		}

		// Query database.
		$part = $this->database->get_part_by_sku( $sku );

		if ( ! $part ) {
			return new WP_Error(
				'part_not_found',
				__( 'Part not found.', CSF_Parts_Constants::TEXT_DOMAIN ),
				array( 'status' => 404 )
			);
		}

		$formatted_part = $this->format_part( $part, true );

		// Cache response.
		$this->cache_response( $cache_key, $formatted_part );

		return rest_ensure_response( $formatted_part );
	}

	/**
	 * Get vehicle makes.
	 *
	 * @since 2.0.0
	 * @param WP_REST_Request $request Request object.
	 * @return WP_REST_Response Response object.
	 */
	public function get_vehicle_makes( WP_REST_Request $request ) {
		$cache_key = 'csf_vehicle_makes';
		$cached    = $this->get_cached_response( $cache_key );

		if ( false !== $cached ) {
			return rest_ensure_response( $cached );
		}

		$makes_data = $this->database->get_vehicle_makes();

		// Format response.
		$makes = array_map(
			function ( $item ) {
				return array(
					'name'  => $item->make,
					'slug'  => sanitize_title( $item->make ),
					'count' => intval( $item->count ),
				);
			},
			$makes_data
		);

		$this->cache_response( $cache_key, $makes );

		return rest_ensure_response( $makes );
	}

	/**
	 * Get vehicle models.
	 *
	 * @since 2.0.0
	 * @param WP_REST_Request $request Request object.
	 * @return WP_REST_Response Response object.
	 */
	public function get_vehicle_models( WP_REST_Request $request ) {
		$make = sanitize_text_field( $request->get_param( 'make' ) );
		$year = $request->get_param( 'year' ) ? intval( $request->get_param( 'year' ) ) : null;

		$cache_key = 'csf_vehicle_models_' . $make . ( $year ? '_' . $year : '' );
		$cached    = $this->get_cached_response( $cache_key );

		if ( false !== $cached ) {
			return rest_ensure_response( $cached );
		}

		$models_data = $this->database->get_vehicle_models( $make, $year );

		// Format response.
		$models = array_map(
			function ( $model ) {
				return array(
					'name' => $model,
					'slug' => sanitize_title( $model ),
				);
			},
			$models_data
		);

		$this->cache_response( $cache_key, $models );

		return rest_ensure_response( $models );
	}

	/**
	 * Get vehicle years.
	 *
	 * @since 2.0.0
	 * @param WP_REST_Request $request Request object.
	 * @return WP_REST_Response Response object.
	 */
	public function get_vehicle_years( WP_REST_Request $request ) {
		$cache_key = 'csf_vehicle_years';
		$cached    = $this->get_cached_response( $cache_key );

		if ( false !== $cached ) {
			return rest_ensure_response( $cached );
		}

		$years_data = $this->database->get_vehicle_years();

		// Format response.
		$years = array_map(
			function ( $item ) {
				return array(
					'year'  => intval( $item->year ),
					'count' => intval( $item->count ),
				);
			},
			$years_data
		);

		$this->cache_response( $cache_key, $years );

		return rest_ensure_response( $years );
	}

	/**
	 * Get compatible parts for vehicle.
	 *
	 * @since 2.0.0
	 * @param WP_REST_Request $request Request object.
	 * @return WP_REST_Response Response object.
	 */
	public function get_compatibility( WP_REST_Request $request ) {
		$make  = sanitize_text_field( $request->get_param( 'make' ) );
		$model = sanitize_text_field( $request->get_param( 'model' ) );
		$year  = intval( $request->get_param( 'year' ) );

		$cache_key = 'csf_compat_' . $make . '_' . $model . '_' . $year;
		$cached    = $this->get_cached_response( $cache_key );

		if ( false !== $cached ) {
			return rest_ensure_response( $cached );
		}

		$parts_data = $this->database->get_parts_by_vehicle( $make, $model, $year );

		// Format parts.
		$parts = array_map( array( $this, 'format_part' ), $parts_data );

		$response = array(
			'vehicle' => array(
				'make'  => $make,
				'model' => $model,
				'year'  => $year,
			),
			'parts'   => $parts,
			'total'   => count( $parts ),
		);

		$this->cache_response( $cache_key, $response );

		return rest_ensure_response( $response );
	}

	/**
	 * Format part data for API response.
	 *
	 * @since 2.0.0
	 * @param object $part             Part object from database.
	 * @param bool   $include_details  Whether to include full details.
	 * @return array Formatted part data.
	 */
	private function format_part( object $part, bool $include_details = false ): array {
		// Decode JSON fields.
		$images = ! empty( $part->images ) ? json_decode( $part->images, true ) : array();

		// Build basic part data.
		$formatted = array(
			'id'           => intval( $part->id ),
			'sku'          => $part->sku,
			'name'         => $part->name,
			'category'     => $part->category,
			'price'        => ! empty( $part->price ) ? floatval( $part->price ) : null,
			'in_stock'     => (bool) $part->in_stock,
			'manufacturer' => $part->manufacturer,
			'image'        => ! empty( $images ) && isset( $images[0]['url'] ) ? $images[0]['url'] : null,
			'link'         => $this->get_part_url( $part->category, $part->sku ),
		);

		// Add full details if requested.
		if ( $include_details ) {
			$compatibility  = ! empty( $part->compatibility ) ? json_decode( $part->compatibility, true ) : array();
			$specifications = ! empty( $part->specifications ) ? json_decode( $part->specifications, true ) : array();
			$features       = ! empty( $part->features ) ? json_decode( $part->features, true ) : array();

			$formatted['description']    = $part->description;
			$formatted['position']       = $part->position;
			$formatted['specifications'] = $specifications;
			$formatted['features']       = $features;
			$formatted['tech_notes']     = $part->tech_notes;
			$formatted['images']         = $images;
			$formatted['compatibility']  = $compatibility;
			$formatted['created_at']     = $part->created_at;
			$formatted['updated_at']     = $part->updated_at;
		}

		return $formatted;
	}

	/**
	 * Get part URL (virtual URL).
	 *
	 * @since 2.0.0
	 * @param string $category Part category.
	 * @param string $sku      Part SKU.
	 * @return string Part URL.
	 */
	private function get_part_url( string $category, string $sku ): string {
		// Singularize category (Radiators -> Radiator).
		$category_singular = rtrim( $category, 's' );

		return home_url( sprintf(
			'/parts/%s-%s',
			sanitize_title( $category_singular ),
			sanitize_title( $sku )
		) );
	}

	/**
	 * Get cached response.
	 *
	 * @since 2.0.0
	 * @param string $key Cache key.
	 * @return mixed|false Cached data or false.
	 */
	private function get_cached_response( string $key ) {
		if ( ! get_option( 'csf_parts_enable_cache', 1 ) ) {
			return false;
		}

		return get_transient( $key );
	}

	/**
	 * Cache response.
	 *
	 * @since 2.0.0
	 * @param string $key  Cache key.
	 * @param mixed  $data Data to cache.
	 */
	private function cache_response( string $key, $data ): void {
		if ( ! get_option( 'csf_parts_enable_cache', 1 ) ) {
			return;
		}

		$duration = get_option( 'csf_parts_cache_duration', CSF_Parts_Constants::CACHE_DURATION_DEFAULT );
		set_transient( $key, $data, intval( $duration ) );
	}
}
