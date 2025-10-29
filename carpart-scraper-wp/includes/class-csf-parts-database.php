<?php
/**
 * Database Schema and Management.
 *
 * Handles custom table creation and database operations for normalized parts storage.
 * Uses custom tables instead of wp_posts for scalability and performance.
 *
 * @package CSF_Parts_Catalog
 * @since   2.0.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

/**
 * Class CSF_Parts_Database
 */
class CSF_Parts_Database {

	/**
	 * Table name for parts.
	 *
	 * @var string
	 */
	private $table_parts;

	/**
	 * WordPress database object.
	 *
	 * @var wpdb
	 */
	private $wpdb;

	/**
	 * Constructor.
	 */
	public function __construct() {
		global $wpdb;
		$this->wpdb        = $wpdb;
		$this->table_parts = $wpdb->prefix . 'csf_parts';
	}

	/**
	 * Create custom tables on plugin activation.
	 *
	 * @since 2.0.0
	 */
	public function create_tables(): void {
		require_once ABSPATH . 'wp-admin/includes/upgrade.php';

		$charset_collate = $this->wpdb->get_charset_collate();

		// Main parts table - one row per SKU (normalized).
		$sql_parts = "CREATE TABLE {$this->table_parts} (
			id bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
			sku varchar(50) NOT NULL,
			name varchar(200) NOT NULL,
			description longtext,
			short_description text,
			category varchar(100),
			price decimal(10,2),
			manufacturer varchar(100),
			in_stock tinyint(1) DEFAULT 1,
			position varchar(50),
			specifications longtext,
			features longtext,
			tech_notes text,
			compatibility longtext NOT NULL,
			images longtext,
			scraped_at varchar(50),
			created_at datetime DEFAULT CURRENT_TIMESTAMP,
			updated_at datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
			PRIMARY KEY  (id),
			UNIQUE KEY sku (sku),
			KEY category (category),
			KEY manufacturer (manufacturer),
			KEY in_stock (in_stock)
		) $charset_collate;";

		dbDelta( $sql_parts );

		// Store schema version for future migrations.
		update_option( 'csf_parts_db_version', '2.0.0' );
	}

	/**
	 * Drop custom tables on plugin uninstall.
	 *
	 * @since 2.0.0
	 */
	public function drop_tables(): void {
		$this->wpdb->query( "DROP TABLE IF EXISTS {$this->table_parts}" );
		delete_option( 'csf_parts_db_version' );
	}

	/**
	 * Get part by SKU.
	 *
	 * @since 2.0.0
	 * @param string $sku Part SKU.
	 * @return object|null Part object or null if not found.
	 */
	public function get_part_by_sku( string $sku ): ?object {
		$result = $this->wpdb->get_row(
			$this->wpdb->prepare(
				"SELECT * FROM {$this->table_parts} WHERE sku = %s",
				$sku
			)
		);

		return $result ?: null;
	}

	/**
	 * Insert or update part.
	 *
	 * @since 2.0.0
	 * @param array $data Part data.
	 * @return int|false Part ID on success, false on failure.
	 */
	public function upsert_part( array $data ) {
		$existing = $this->get_part_by_sku( $data['sku'] );

		// Prepare data for database.
		$db_data = array(
			'sku'               => $data['sku'],
			'name'              => $data['name'] ?? '',
			'description'       => $data['description'] ?? '',
			'short_description' => $data['short_description'] ?? '',
			'category'          => $data['category'] ?? '',
			'price'             => $data['price'] ?? null,
			'manufacturer'      => $data['manufacturer'] ?? '',
			'in_stock'          => isset( $data['in_stock'] ) ? (int) $data['in_stock'] : 1,
			'position'          => $data['position'] ?? '',
			'specifications'    => isset( $data['specifications'] ) ? wp_json_encode( $data['specifications'] ) : '',
			'features'          => isset( $data['features'] ) ? wp_json_encode( $data['features'] ) : '',
			'tech_notes'        => $data['tech_notes'] ?? '',
			'compatibility'     => isset( $data['compatibility'] ) ? wp_json_encode( $data['compatibility'] ) : '',
			'images'            => isset( $data['images'] ) ? wp_json_encode( $data['images'] ) : '',
			'scraped_at'        => $data['scraped_at'] ?? '',
		);

		if ( $existing ) {
			// Update existing part.
			$result = $this->wpdb->update(
				$this->table_parts,
				$db_data,
				array( 'id' => $existing->id ),
				array(
					'%s', // sku.
					'%s', // name.
					'%s', // description.
					'%s', // short_description.
					'%s', // category.
					'%f', // price.
					'%s', // manufacturer.
					'%d', // in_stock.
					'%s', // position.
					'%s', // specifications.
					'%s', // features.
					'%s', // tech_notes.
					'%s', // compatibility.
					'%s', // images.
					'%s', // scraped_at.
				),
				array( '%d' )
			);

			return false !== $result ? $existing->id : false;
		} else {
			// Insert new part.
			$result = $this->wpdb->insert(
				$this->table_parts,
				$db_data,
				array(
					'%s', // sku.
					'%s', // name.
					'%s', // description.
					'%s', // short_description.
					'%s', // category.
					'%f', // price.
					'%s', // manufacturer.
					'%d', // in_stock.
					'%s', // position.
					'%s', // specifications.
					'%s', // features.
					'%s', // tech_notes.
					'%s', // compatibility.
					'%s', // images.
					'%s', // scraped_at.
				)
			);

			return false !== $result ? $this->wpdb->insert_id : false;
		}
	}

	/**
	 * Get all parts with pagination.
	 *
	 * @since 2.0.0
	 * @param int $per_page Parts per page.
	 * @param int $page     Page number.
	 * @return array Array of part objects.
	 */
	public function get_parts( int $per_page = 20, int $page = 1 ): array {
		$offset = ( $page - 1 ) * $per_page;

		$results = $this->wpdb->get_results(
			$this->wpdb->prepare(
				"SELECT * FROM {$this->table_parts} ORDER BY id DESC LIMIT %d OFFSET %d",
				$per_page,
				$offset
			)
		);

		return $results ?: array();
	}

	/**
	 * Get total parts count.
	 *
	 * @since 2.0.0
	 * @return int Total number of parts.
	 */
	public function get_total_parts(): int {
		return (int) $this->wpdb->get_var( "SELECT COUNT(*) FROM {$this->table_parts}" );
	}

	/**
	 * Search parts by keyword.
	 *
	 * @since 2.0.0
	 * @param string $keyword Search keyword.
	 * @param int    $limit   Maximum results.
	 * @return array Array of part objects.
	 */
	public function search_parts( string $keyword, int $limit = 20 ): array {
		$results = $this->wpdb->get_results(
			$this->wpdb->prepare(
				"SELECT * FROM {$this->table_parts}
				WHERE sku LIKE %s
				   OR name LIKE %s
				   OR description LIKE %s
				   OR manufacturer LIKE %s
				ORDER BY sku ASC
				LIMIT %d",
				'%' . $this->wpdb->esc_like( $keyword ) . '%',
				'%' . $this->wpdb->esc_like( $keyword ) . '%',
				'%' . $this->wpdb->esc_like( $keyword ) . '%',
				'%' . $this->wpdb->esc_like( $keyword ) . '%',
				$limit
			)
		);

		return $results ?: array();
	}

	/**
	 * Get parts by category.
	 *
	 * @since 2.0.0
	 * @param string $category Category name.
	 * @param int    $per_page Parts per page.
	 * @param int    $page     Page number.
	 * @return array Array of part objects.
	 */
	public function get_parts_by_category( string $category, int $per_page = 20, int $page = 1 ): array {
		$offset = ( $page - 1 ) * $per_page;

		$results = $this->wpdb->get_results(
			$this->wpdb->prepare(
				"SELECT * FROM {$this->table_parts}
				WHERE category = %s
				ORDER BY name ASC
				LIMIT %d OFFSET %d",
				$category,
				$per_page,
				$offset
			)
		);

		return $results ?: array();
	}

	/**
	 * Get all unique categories.
	 *
	 * @since 2.0.0
	 * @return array Array of category names.
	 */
	public function get_categories(): array {
		$results = $this->wpdb->get_col(
			"SELECT DISTINCT category FROM {$this->table_parts} WHERE category != '' ORDER BY category ASC"
		);

		return $results ?: array();
	}

	/**
	 * Get all unique vehicle makes from compatibility JSON.
	 *
	 * @since 2.0.0
	 * @return array Array of make names with counts.
	 */
	public function get_vehicle_makes(): array {
		$query = "
			SELECT DISTINCT JSON_UNQUOTE(JSON_EXTRACT(v.value, '$.make')) as make
			FROM {$this->table_parts} p,
			     JSON_TABLE(
			         p.compatibility,
			         '$[*]' COLUMNS (
			             value JSON PATH '$'
			         )
			     ) v
			WHERE p.compatibility IS NOT NULL
			  AND JSON_EXTRACT(v.value, '$.make') IS NOT NULL
			ORDER BY make ASC
		";

		$results = $this->wpdb->get_col( $query );

		return $results ?: array();
	}

	/**
	 * Get unique vehicle makes for a specific year.
	 *
	 * @since 2.0.0
	 * @param int $year Vehicle year.
	 * @return array Array of make names for the specified year.
	 */
	public function get_vehicle_makes_by_year( int $year ): array {
		$query = $this->wpdb->prepare(
			"SELECT DISTINCT JSON_UNQUOTE(JSON_EXTRACT(v.value, '$.make')) as make
			FROM {$this->table_parts} p,
			     JSON_TABLE(
			         p.compatibility,
			         '$[*]' COLUMNS (
			             value JSON PATH '$'
			         )
			     ) v
			WHERE p.compatibility IS NOT NULL
			  AND JSON_EXTRACT(v.value, '$.year') = %d
			  AND JSON_EXTRACT(v.value, '$.make') IS NOT NULL
			ORDER BY make ASC",
			$year
		);

		$results = $this->wpdb->get_col( $query );

		return $results ?: array();
	}

	/**
	 * Get unique vehicle models for a given make.
	 *
	 * @since 2.0.0
	 * @param string   $make Vehicle make (required).
	 * @param int|null $year Vehicle year (optional filter).
	 * @return array Array of model names.
	 */
	public function get_vehicle_models( string $make = '', ?int $year = null ): array {
		// If no make specified, return all models.
		if ( empty( $make ) ) {
			$query = "SELECT DISTINCT JSON_UNQUOTE(JSON_EXTRACT(v.value, '$.model')) as model
				FROM {$this->table_parts} p,
				     JSON_TABLE(
				         p.compatibility,
				         '$[*]' COLUMNS (
				             value JSON PATH '$'
				         )
				     ) v
				WHERE p.compatibility IS NOT NULL
				  AND JSON_EXTRACT(v.value, '$.model') IS NOT NULL
				ORDER BY model ASC";
			$results = $this->wpdb->get_col( $query );
			return $results ?: array();
		}

		if ( $year ) {
			$query = $this->wpdb->prepare(
				"SELECT DISTINCT JSON_UNQUOTE(JSON_EXTRACT(v.value, '$.model')) as model
				FROM {$this->table_parts} p,
				     JSON_TABLE(
				         p.compatibility,
				         '$[*]' COLUMNS (
				             value JSON PATH '$'
				         )
				     ) v
				WHERE p.compatibility IS NOT NULL
				  AND JSON_UNQUOTE(JSON_EXTRACT(v.value, '$.make')) = %s
				  AND JSON_EXTRACT(v.value, '$.year') = %d
				  AND JSON_EXTRACT(v.value, '$.model') IS NOT NULL
				ORDER BY model ASC",
				$make,
				$year
			);
		} else {
			$query = $this->wpdb->prepare(
				"SELECT DISTINCT JSON_UNQUOTE(JSON_EXTRACT(v.value, '$.model')) as model
				FROM {$this->table_parts} p,
				     JSON_TABLE(
				         p.compatibility,
				         '$[*]' COLUMNS (
				             value JSON PATH '$'
				         )
				     ) v
				WHERE p.compatibility IS NOT NULL
				  AND JSON_UNQUOTE(JSON_EXTRACT(v.value, '$.make')) = %s
				  AND JSON_EXTRACT(v.value, '$.model') IS NOT NULL
				ORDER BY model ASC",
				$make
			);
		}

		$results = $this->wpdb->get_col( $query );

		return $results ?: array();
	}

	/**
	 * Get all unique vehicle years from compatibility JSON.
	 *
	 * @since 2.0.0
	 * @return array Array of years with counts.
	 */
	public function get_vehicle_years(): array {
		$query = "
			SELECT DISTINCT JSON_EXTRACT(v.value, '$.year') as year
			FROM {$this->table_parts} p,
			     JSON_TABLE(
			         p.compatibility,
			         '$[*]' COLUMNS (
			             value JSON PATH '$'
			         )
			     ) v
			WHERE p.compatibility IS NOT NULL
			  AND JSON_EXTRACT(v.value, '$.year') IS NOT NULL
			ORDER BY year DESC
		";

		$results = $this->wpdb->get_col( $query );

		return $results ?: array();
	}

	/**
	 * Get all unique categories.
	 *
	 * Returns a flat array of all distinct categories from the parts table.
	 *
	 * @since 2.0.0
	 * @return array Array of category names.
	 */
	public function get_all_categories(): array {
		$query = "SELECT DISTINCT category FROM {$this->table_parts} WHERE category IS NOT NULL AND category != '' ORDER BY category ASC";

		$results = $this->wpdb->get_col( $query );

		return $results ?: array();
	}

	/**
	 * Get parts compatible with specific vehicle.
	 *
	 * @since 2.0.0
	 * @param string $make  Vehicle make.
	 * @param string $model Vehicle model.
	 * @param int    $year  Vehicle year.
	 * @return array Array of part objects.
	 */
	public function get_parts_by_vehicle( string $make, string $model, int $year ): array {
		$query = $this->wpdb->prepare(
			"SELECT p.*
			FROM {$this->table_parts} p,
			     JSON_TABLE(
			         p.compatibility,
			         '$[*]' COLUMNS (
			             value JSON PATH '$'
			         )
			     ) v
			WHERE p.compatibility IS NOT NULL
			  AND JSON_UNQUOTE(JSON_EXTRACT(v.value, '$.make')) = %s
			  AND JSON_UNQUOTE(JSON_EXTRACT(v.value, '$.model')) = %s
			  AND JSON_EXTRACT(v.value, '$.year') = %d
			ORDER BY p.category ASC, p.name ASC",
			$make,
			$model,
			$year
		);

		$results = $this->wpdb->get_results( $query );

		return $results ?: array();
	}

	/**
	 * Advanced search with filters.
	 *
	 * @since 2.0.0
	 * @param array $filters {
	 *     Filter parameters.
	 *
	 *     @type string   $search   Search keyword (optional).
	 *     @type string   $category Category name (optional).
	 *     @type string   $make     Vehicle make (optional).
	 *     @type string   $model    Vehicle model (optional).
	 *     @type int      $year     Vehicle year (optional).
	 *     @type int      $per_page Results per page (default: 20).
	 *     @type int      $page     Page number (default: 1).
	 * }
	 * @return array {
	 *     Query results.
	 *
	 *     @type array $parts Array of part objects.
	 *     @type int   $total Total number of matching parts.
	 * }
	 */
	public function query_parts( array $filters = array(), int $per_page = 20, int $page = 1 ): array {
		$search     = $filters['search'] ?? '';
		$categories = $filters['categories'] ?? $filters['category'] ?? array();
		$makes      = $filters['makes'] ?? $filters['make'] ?? array();
		$models     = $filters['models'] ?? $filters['model'] ?? array();
		$years      = $filters['years'] ?? $filters['year'] ?? array();

		// Normalize to arrays (support both single values and arrays).
		$categories = ! empty( $categories ) ? (array) $categories : array();
		$makes      = ! empty( $makes ) ? (array) $makes : array();
		$models     = ! empty( $models ) ? (array) $models : array();
		$years      = ! empty( $years ) ? (array) $years : array();

		$offset = ( $page - 1 ) * $per_page;

		// Build WHERE clauses.
		$where_clauses = array( '1=1' );
		$prepare_args  = array();

		// Search keyword.
		if ( ! empty( $search ) ) {
			$where_clauses[] = '(p.sku LIKE %s OR p.name LIKE %s OR p.description LIKE %s OR p.manufacturer LIKE %s)';
			$search_term     = '%' . $this->wpdb->esc_like( $search ) . '%';
			$prepare_args[]  = $search_term;
			$prepare_args[]  = $search_term;
			$prepare_args[]  = $search_term;
			$prepare_args[]  = $search_term;
		}

		// Category filter (array support).
		if ( ! empty( $categories ) ) {
			$placeholders    = implode( ',', array_fill( 0, count( $categories ), '%s' ) );
			$where_clauses[] = "p.category IN ($placeholders)";
			$prepare_args    = array_merge( $prepare_args, $categories );
		}

		// Vehicle compatibility filter (requires JSON_TABLE).
		$from_clause = $this->table_parts . ' p';
		if ( ! empty( $makes ) || ! empty( $models ) || ! empty( $years ) ) {
			$from_clause .= ", JSON_TABLE(
				p.compatibility,
				'$[*]' COLUMNS (
					value JSON PATH '$'
				)
			) v";

			$where_clauses[] = 'p.compatibility IS NOT NULL';

			// Makes filter (array support).
			if ( ! empty( $makes ) ) {
				$placeholders    = implode( ',', array_fill( 0, count( $makes ), '%s' ) );
				$where_clauses[] = "JSON_UNQUOTE(JSON_EXTRACT(v.value, '$.make')) IN ($placeholders)";
				$prepare_args    = array_merge( $prepare_args, $makes );
			}

			// Models filter (array support).
			if ( ! empty( $models ) ) {
				$placeholders    = implode( ',', array_fill( 0, count( $models ), '%s' ) );
				$where_clauses[] = "JSON_UNQUOTE(JSON_EXTRACT(v.value, '$.model')) IN ($placeholders)";
				$prepare_args    = array_merge( $prepare_args, $models );
			}

			// Years filter (array support).
			if ( ! empty( $years ) ) {
				// Convert years to integers.
				$years           = array_map( 'intval', $years );
				$placeholders    = implode( ',', array_fill( 0, count( $years ), '%d' ) );
				$where_clauses[] = "JSON_EXTRACT(v.value, '$.year') IN ($placeholders)";
				$prepare_args    = array_merge( $prepare_args, $years );
			}
		}

		$where_sql = implode( ' AND ', $where_clauses );

		// Get total count.
		$count_query = "SELECT COUNT(DISTINCT p.id) FROM {$from_clause} WHERE {$where_sql}";

		if ( ! empty( $prepare_args ) ) {
			// phpcs:ignore WordPress.DB.PreparedSQL.NotPrepared
			$count_query = $this->wpdb->prepare( $count_query, ...$prepare_args );
		}

		// phpcs:ignore WordPress.DB.PreparedSQL.NotPrepared
		$total = (int) $this->wpdb->get_var( $count_query );

		// Get parts.
		$parts_query     = "SELECT DISTINCT p.* FROM {$from_clause} WHERE {$where_sql} ORDER BY p.name ASC LIMIT %d OFFSET %d";
		$prepare_args[]  = $per_page;
		$prepare_args[]  = $offset;

		// phpcs:ignore WordPress.DB.PreparedSQL.NotPrepared
		$parts_query = $this->wpdb->prepare( $parts_query, ...$prepare_args );

		// phpcs:ignore WordPress.DB.PreparedSQL.NotPrepared
		$parts = $this->wpdb->get_results( $parts_query );

		return array(
			'parts' => $parts ?: array(),
			'total' => $total,
		);
	}
}
