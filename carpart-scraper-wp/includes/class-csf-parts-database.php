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
	 * Schema version written on activation and reached by maybe_migrate().
	 */
	const DB_VERSION = '2.3.0';

	/**
	 * Content fields that define a part for change detection, in storage form.
	 *
	 * These are what CSF publishes. scraped_at, last_synced and the timestamps
	 * describe when we looked and are deliberately absent, so re-importing an
	 * identical part never counts as a change.
	 */
	const CONTENT_FIELDS = array(
		'name',
		'description',
		'short_description',
		'category',
		'price',
		'manufacturer',
		'in_stock',
		'position',
		'specifications',
		'features',
		'tech_notes',
		'compatibility',
		'images',
		'interchange_numbers',
	);

	/**
	 * Table name for parts.
	 *
	 * @var string
	 */
	private $table_parts;

	/**
	 * Change-log table name: one row per part per import that created or changed it.
	 *
	 * @var string
	 */
	private $table_changes;

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
		$this->table_parts   = $wpdb->prefix . 'csf_parts';
		$this->table_changes = $wpdb->prefix . 'csf_part_changes';
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
			interchange_numbers longtext,
			scraped_at varchar(50),
			content_hash char(32) DEFAULT NULL,
			last_synced datetime DEFAULT NULL,
			created_at datetime DEFAULT CURRENT_TIMESTAMP,
			updated_at datetime DEFAULT CURRENT_TIMESTAMP,
			PRIMARY KEY  (id),
			UNIQUE KEY sku (sku),
			KEY category (category),
			KEY manufacturer (manufacturer),
			KEY in_stock (in_stock),
			KEY updated_at (updated_at)
		) $charset_collate;";

		// Timestamp semantics (all set by upsert_part, never by MySQL triggers):
		//   created_at  - first import that saw the SKU
		//   updated_at  - last import in which a content field differed (see CONTENT_FIELDS)
		//   last_synced - last import that saw the SKU at all
		// content_hash is the MD5 of the stored content fields so an unchanged
		// part costs one string comparison, not fourteen.
		dbDelta( $sql_parts );

		// Change log: what each import created or changed, queryable after CI logs expire.
		$sql_changes = "CREATE TABLE {$this->table_changes} (
			id bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
			part_id bigint(20) UNSIGNED NOT NULL,
			sku varchar(50) NOT NULL,
			change_type varchar(10) NOT NULL,
			changed_fields text,
			observed_at datetime NOT NULL,
			PRIMARY KEY  (id),
			KEY sku (sku),
			KEY observed_at (observed_at)
		) $charset_collate;";

		dbDelta( $sql_changes );

		// Store schema version for future migrations.
		update_option( 'csf_parts_db_version', self::DB_VERSION );
	}

	/**
	 * Run database migrations if needed.
	 *
	 * @since 2.1.0
	 */
	public function maybe_migrate(): void {
		$current_version = get_option( 'csf_parts_db_version', '2.0.0' );

		// Migration for 2.1.0: Add interchange_numbers column.
		if ( version_compare( $current_version, '2.1.0', '<' ) ) {
			$this->migrate_to_2_1_0();
			update_option( 'csf_parts_db_version', '2.1.0' );
		}

		// Migration for 2.2.0: Add last_synced column.
		if ( version_compare( $current_version, '2.2.0', '<' ) ) {
			$this->migrate_to_2_2_0();
			update_option( 'csf_parts_db_version', '2.2.0' );
		}

		// Migration for 2.3.0: content hash, explicit updated_at, change log.
		if ( version_compare( $current_version, '2.3.0', '<' ) ) {
			$this->migrate_to_2_3_0();
			update_option( 'csf_parts_db_version', '2.3.0' );
		}
	}

	/**
	 * Migration to version 2.1.0: Add interchange_numbers column.
	 *
	 * @since 2.1.0
	 */
	private function migrate_to_2_1_0(): void {
		// Check if column exists.
		// phpcs:ignore WordPress.DB.PreparedSQL.InterpolatedNotPrepared
		$column_exists = $this->wpdb->get_results(
			"SHOW COLUMNS FROM {$this->table_parts} LIKE 'interchange_numbers'"
		);

		// Add column if it doesn't exist.
		if ( empty( $column_exists ) ) {
			// phpcs:ignore WordPress.DB.PreparedSQL.InterpolatedNotPrepared
			$this->wpdb->query(
				"ALTER TABLE {$this->table_parts}
				ADD COLUMN interchange_numbers longtext AFTER images"
			);
		}
	}

	/**
	 * Migration to version 2.2.0: Add last_synced column.
	 *
	 * @since 2.2.0
	 */
	private function migrate_to_2_2_0(): void {
		// Check if column exists.
		// phpcs:ignore WordPress.DB.PreparedSQL.InterpolatedNotPrepared
		$column_exists = $this->wpdb->get_results(
			"SHOW COLUMNS FROM {$this->table_parts} LIKE 'last_synced'"
		);

		// Add column if it doesn't exist.
		if ( empty( $column_exists ) ) {
			// phpcs:ignore WordPress.DB.PreparedSQL.InterpolatedNotPrepared
			$this->wpdb->query(
				"ALTER TABLE {$this->table_parts}
				ADD COLUMN last_synced datetime DEFAULT NULL AFTER scraped_at"
			);
		}
	}

	/**
	 * Migration to version 2.3.0: content_hash column, updated_at without the
	 * MySQL ON UPDATE trigger, and the change-log table.
	 *
	 * Existing rows keep their updated_at; the first import after upgrading
	 * compares fields (no hash yet), stores the hash, and only bumps updated_at
	 * for parts whose content really differs.
	 *
	 * @since 2.3.0
	 */
	private function migrate_to_2_3_0(): void {
		// phpcs:ignore WordPress.DB.PreparedSQL.InterpolatedNotPrepared
		$column_exists = $this->wpdb->get_results(
			"SHOW COLUMNS FROM {$this->table_parts} LIKE 'content_hash'"
		);

		if ( empty( $column_exists ) ) {
			// phpcs:ignore WordPress.DB.PreparedSQL.InterpolatedNotPrepared
			$this->wpdb->query(
				"ALTER TABLE {$this->table_parts}
				ADD COLUMN content_hash char(32) DEFAULT NULL AFTER scraped_at"
			);
		}

		// updated_at becomes application-managed: only a content change sets it.
		// phpcs:ignore WordPress.DB.PreparedSQL.InterpolatedNotPrepared
		$this->wpdb->query(
			"ALTER TABLE {$this->table_parts}
			MODIFY updated_at datetime DEFAULT CURRENT_TIMESTAMP"
		);

		// phpcs:ignore WordPress.DB.PreparedSQL.InterpolatedNotPrepared
		$index_exists = $this->wpdb->get_results(
			"SHOW INDEX FROM {$this->table_parts} WHERE Key_name = 'updated_at'"
		);

		if ( empty( $index_exists ) ) {
			// phpcs:ignore WordPress.DB.PreparedSQL.InterpolatedNotPrepared
			$this->wpdb->query( "ALTER TABLE {$this->table_parts} ADD KEY updated_at (updated_at)" );
		}

		$charset_collate = $this->wpdb->get_charset_collate();
		// phpcs:ignore WordPress.DB.PreparedSQL.InterpolatedNotPrepared
		$this->wpdb->query(
			"CREATE TABLE IF NOT EXISTS {$this->table_changes} (
				id bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
				part_id bigint(20) UNSIGNED NOT NULL,
				sku varchar(50) NOT NULL,
				change_type varchar(10) NOT NULL,
				changed_fields text,
				observed_at datetime NOT NULL,
				PRIMARY KEY  (id),
				KEY sku (sku),
				KEY observed_at (observed_at)
			) $charset_collate"
		);
	}

	/**
	 * Drop custom tables on plugin uninstall.
	 *
	 * @since 2.0.0
	 */
	public function drop_tables(): void {
		$this->wpdb->query( "DROP TABLE IF EXISTS {$this->table_changes}" );
		$this->wpdb->query( "DROP TABLE IF EXISTS {$this->table_parts}" );
		delete_option( 'csf_parts_db_version' );
	}

	/**
	 * Get part by ID.
	 *
	 * @since 1.1.5
	 * @param int $id Part ID.
	 * @return object|null Part object or null if not found.
	 */
	public function get_part_by_id( int $id ): ?object {
		$result = $this->wpdb->get_row(
			$this->wpdb->prepare(
				"SELECT * FROM {$this->table_parts} WHERE id = %d",
				$id
			)
		);

		return $result ?: null;
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
	 * Order compatibility rows by make, model, year (then engine) so the stored
	 * JSON, and anything that summarises it without a vehicle context, is
	 * deterministic regardless of the order the scraper emitted rows.
	 *
	 * @since 1.19.0
	 * @param array<int, mixed> $rows Compatibility rows.
	 * @return array<int, mixed> Sorted rows, re-indexed; non-array rows sort last.
	 */
	public static function sort_compatibility( array $rows ): array {
		usort(
			$rows,
			static function ( $a, $b ): int {
				if ( ! is_array( $a ) || ! is_array( $b ) ) {
					return is_array( $b ) <=> is_array( $a );
				}
				return strcasecmp( (string) ( $a['make'] ?? '' ), (string) ( $b['make'] ?? '' ) )
					?: strnatcasecmp( (string) ( $a['model'] ?? '' ), (string) ( $b['model'] ?? '' ) )
					?: ( (int) ( $a['year'] ?? 0 ) <=> (int) ( $b['year'] ?? 0 ) )
					?: strnatcasecmp( (string) ( $a['engine'] ?? '' ), (string) ( $b['engine'] ?? '' ) );
			}
		);
		return array_values( $rows );
	}

	/**
	 * Insert or update part.
	 *
	 * A part is "changed" when any CONTENT_FIELDS value differs from what is
	 * stored. The stored content_hash short-circuits the common case; rows
	 * without one (imported before 2.3.0) fall back to a field comparison so
	 * upgrading never marks the whole catalog as changed. Only a real change
	 * moves updated_at; every import moves last_synced. Created and updated
	 * parts are appended to the change log.
	 *
	 * @since 2.0.0
	 * @param array $data Part data.
	 * @return array{id: int|false, status: string, changed_fields: string[]} Part ID, status
	 *                ('created', 'updated', 'unchanged') and, for 'updated', the content fields
	 *                whose stored value differed from the incoming one.
	 */
	public function upsert_part( array $data ) {
		$sku      = (string) $data['sku'];
		$existing = $this->get_part_by_sku( $sku );
		$content  = self::content_data( $data );
		$hash     = self::content_hash( $content );
		$now      = current_time( 'mysql' );
		$scraped  = (string) ( $data['scraped_at'] ?? '' );

		if ( ! $existing ) {
			$row = array_merge(
				array( 'sku' => $sku ),
				$content,
				array(
					'scraped_at'   => $scraped,
					'content_hash' => $hash,
					'last_synced'  => $now,
					'created_at'   => $now,
					'updated_at'   => $now,
				)
			);

			$result = $this->wpdb->insert( $this->table_parts, $row, self::row_formats( $row ) );
			$id     = false !== $result ? (int) $this->wpdb->insert_id : false;

			if ( false !== $id ) {
				$this->record_change( $id, $sku, 'created', array(), $now );
			}

			return array(
				'id'             => $id,
				'status'         => 'created',
				'changed_fields' => array(),
			);
		}

		$changed_fields = (string) ( $existing->content_hash ?? '' ) === $hash
			? array()
			: self::diff_content( $existing, $content );

		if ( empty( $changed_fields ) ) {
			// Nothing CSF publishes differs: note that we saw it, store the hash
			// (fills in rows from before hashing) and leave updated_at alone.
			$this->wpdb->query(
				$this->wpdb->prepare(
					"UPDATE {$this->table_parts}
					SET last_synced = %s, scraped_at = %s, content_hash = %s, updated_at = updated_at
					WHERE id = %d",
					$now,
					$scraped,
					$hash,
					$existing->id
				)
			);

			return array(
				'id'             => $existing->id,
				'status'         => 'unchanged',
				'changed_fields' => array(),
			);
		}

		$row = array_merge(
			$content,
			array(
				'scraped_at'   => $scraped,
				'content_hash' => $hash,
				'last_synced'  => $now,
				'updated_at'   => $now,
			)
		);

		$result = $this->wpdb->update(
			$this->table_parts,
			$row,
			array( 'id' => $existing->id ),
			self::row_formats( $row ),
			array( '%d' )
		);

		if ( false !== $result ) {
			$this->record_change( (int) $existing->id, $sku, 'updated', $changed_fields, $now );
		}

		return array(
			'id'             => false !== $result ? $existing->id : false,
			'status'         => 'updated',
			'changed_fields' => $changed_fields,
		);
	}

	/**
	 * Content fields of an incoming part in the form they are stored.
	 *
	 * @since 2.3.0
	 * @param array $data Part data as pushed by the scraper.
	 * @return array<string, mixed> CONTENT_FIELDS keyed values.
	 */
	public static function content_data( array $data ): array {
		$compatibility = $data['compatibility'] ?? null;
		if ( is_array( $compatibility ) ) {
			$compatibility = self::sort_compatibility( $compatibility );
		}

		return array(
			'name'                => $data['name'] ?? '',
			'description'         => $data['description'] ?? '',
			'short_description'   => $data['short_description'] ?? '',
			'category'            => $data['category'] ?? '',
			'price'               => $data['price'] ?? null,
			'manufacturer'        => $data['manufacturer'] ?? '',
			'in_stock'            => isset( $data['in_stock'] ) ? (int) $data['in_stock'] : 1,
			'position'            => $data['position'] ?? '',
			'specifications'      => isset( $data['specifications'] ) ? wp_json_encode( $data['specifications'] ) : '',
			'features'            => isset( $data['features'] ) ? wp_json_encode( $data['features'] ) : '',
			'tech_notes'          => $data['tech_notes'] ?? '',
			'compatibility'       => null !== $compatibility ? wp_json_encode( $compatibility ) : '',
			'images'              => isset( $data['images'] ) ? wp_json_encode( $data['images'] ) : '',
			'interchange_numbers' => isset( $data['interchange_numbers'] ) ? wp_json_encode( $data['interchange_numbers'] ) : '',
		);
	}

	/**
	 * Hash of a part's content fields in comparison form.
	 *
	 * Two parts hash alike exactly when diff_content() would find no
	 * differing field, so the hash can stand in for the comparison.
	 *
	 * @since 2.3.0
	 * @param array<string, mixed> $content Output of content_data().
	 * @return string 32-character MD5 hex digest.
	 */
	public static function content_hash( array $content ): string {
		$normalized = array();
		foreach ( self::CONTENT_FIELDS as $field ) {
			$normalized[ $field ] = self::comparable( $field, $content[ $field ] ?? '' );
		}
		return md5( (string) wp_json_encode( $normalized ) );
	}

	/**
	 * Content fields whose stored value differs from the incoming one.
	 *
	 * @since 2.3.0
	 * @param object               $existing Stored row.
	 * @param array<string, mixed> $content  Output of content_data().
	 * @return string[] Differing field names in CONTENT_FIELDS order.
	 */
	public static function diff_content( object $existing, array $content ): array {
		$changed = array();
		foreach ( self::CONTENT_FIELDS as $field ) {
			$stored   = self::comparable( $field, $existing->$field ?? '' );
			$incoming = self::comparable( $field, $content[ $field ] ?? '' );
			if ( $stored !== $incoming ) {
				$changed[] = $field;
			}
		}
		return $changed;
	}

	/**
	 * A field value in the form used for comparison and hashing.
	 *
	 * Everything compares as a string. Price compares to two decimals so
	 * 199.99 and "199.990000" agree; a null price stays distinct from 0.
	 *
	 * @param string $field Field name.
	 * @param mixed  $value Stored or incoming value.
	 * @return string
	 */
	private static function comparable( string $field, $value ): string {
		if ( 'price' === $field ) {
			return null === $value || '' === $value ? '' : number_format( (float) $value, 2, '.', '' );
		}
		return (string) $value;
	}

	/**
	 * wpdb format specifiers for a row, keyed like the row.
	 *
	 * @param array<string, mixed> $row Column => value.
	 * @return string[] One specifier per column, in row order.
	 */
	private static function row_formats( array $row ): array {
		$formats = array();
		foreach ( array_keys( $row ) as $column ) {
			if ( 'price' === $column ) {
				$formats[] = '%f';
			} elseif ( 'in_stock' === $column ) {
				$formats[] = '%d';
			} else {
				$formats[] = '%s';
			}
		}
		return $formats;
	}

	/**
	 * Append a row to the change log.
	 *
	 * @since 2.3.0
	 * @param int      $part_id        Part row ID.
	 * @param string   $sku            Part SKU.
	 * @param string   $change_type    'created' or 'updated'.
	 * @param string[] $changed_fields Differing fields ('updated' only).
	 * @param string   $observed_at    MySQL datetime of the import.
	 */
	private function record_change( int $part_id, string $sku, string $change_type, array $changed_fields, string $observed_at ): void {
		$this->wpdb->insert(
			$this->table_changes,
			array(
				'part_id'        => $part_id,
				'sku'            => $sku,
				'change_type'    => $change_type,
				'changed_fields' => wp_json_encode( array_values( $changed_fields ) ),
				'observed_at'    => $observed_at,
			),
			array( '%d', '%s', '%s', '%s', '%s' )
		);
	}

	/**
	 * Most recent change-log entries, newest first.
	 *
	 * @since 2.3.0
	 * @param int $limit Maximum rows (1-500).
	 * @return array<int, object> Rows with sku, change_type, changed_fields (string[]) and observed_at.
	 */
	public function get_recent_changes( int $limit = 20 ): array {
		$limit = max( 1, min( 500, $limit ) );

		$rows = $this->wpdb->get_results(
			$this->wpdb->prepare(
				"SELECT sku, change_type, changed_fields, observed_at
				FROM {$this->table_changes}
				ORDER BY observed_at DESC, id DESC
				LIMIT %d",
				$limit
			)
		);

		foreach ( (array) $rows as $row ) {
			$decoded             = json_decode( (string) ( $row->changed_fields ?? '' ), true );
			$row->changed_fields = is_array( $decoded ) ? array_map( 'strval', $decoded ) : array();
		}

		return (array) $rows;
	}

	/**
	 * Delete change-log rows older than a retention window.
	 *
	 * @since 2.3.0
	 * @param int $days Rows observed more than this many days ago are removed.
	 * @return int Rows deleted.
	 */
	public function prune_changes( int $days = 365 ): int {
		$days   = max( 1, $days );
		$cutoff = gmdate( 'Y-m-d H:i:s', time() - $days * DAY_IN_SECONDS );

		$deleted = $this->wpdb->query(
			$this->wpdb->prepare(
				"DELETE FROM {$this->table_changes} WHERE observed_at < %s",
				$cutoff
			)
		);

		return false === $deleted ? 0 : (int) $deleted;
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
	 * Part counts per category, alphabetical.
	 *
	 * @since 1.14.0
	 * @return array<string, int> category => count
	 */
	public function get_category_counts(): array {
		$rows = $this->wpdb->get_results(
			"SELECT category, COUNT(*) AS count FROM {$this->table_parts}
			 WHERE category IS NOT NULL AND category != ''
			 GROUP BY category ORDER BY category ASC"
		);

		$counts = array();
		foreach ( $rows ?: array() as $row ) {
			$counts[ (string) $row->category ] = (int) $row->count;
		}
		return $counts;
	}

	/**
	 * Get all unique vehicle makes from compatibility JSON.
	 *
	 * @since 2.0.0
	 * @return array Array of make names with counts.
	 */
	public function get_vehicle_makes(): array {
		$query = "
			SELECT
				JSON_UNQUOTE(JSON_EXTRACT(v.value, '$.make')) as make,
				COUNT(DISTINCT p.id) as count
			FROM {$this->table_parts} p,
			     JSON_TABLE(
			         p.compatibility,
			         '$[*]' COLUMNS (
			             value JSON PATH '$'
			         )
			     ) v
			WHERE p.compatibility IS NOT NULL
			  AND p.compatibility != ''
			  AND p.compatibility != '[]'
			  AND JSON_VALID(p.compatibility)
			  AND JSON_EXTRACT(v.value, '$.make') IS NOT NULL
			GROUP BY make
			ORDER BY make ASC
		";

		$results = $this->wpdb->get_results( $query );

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
			  AND JSON_UNQUOTE(JSON_EXTRACT(v.value, '$.year')) = %s
			  AND JSON_EXTRACT(v.value, '$.make') IS NOT NULL
			ORDER BY make ASC",
			(string) $year
		);

		$results = $this->wpdb->get_col( $query );

		return $results ?: array();
	}

	/**
	 * Get unique vehicle years for a make, optionally narrowed by model.
	 *
	 * Mirror of get_vehicle_makes_by_year() so the Year → Make → Model cascade
	 * also works in the other direction.
	 *
	 * @since 1.12.0
	 * @param string $make  Vehicle make (required).
	 * @param string $model Vehicle model (optional filter).
	 * @return int[] Years, newest first.
	 */
	public function get_vehicle_years_by_make( string $make, string $model = '' ): array {
		if ( '' === $make ) {
			return array();
		}

		$model_clause = '' !== $model ? " AND JSON_UNQUOTE(JSON_EXTRACT(v.value, '$.model')) = %s" : '';
		$args         = '' !== $model ? array( $make, $model ) : array( $make );

		$query = $this->wpdb->prepare(
			"SELECT DISTINCT CAST(JSON_UNQUOTE(JSON_EXTRACT(v.value, '$.year')) AS UNSIGNED) as year
			FROM {$this->table_parts} p,
			     JSON_TABLE(
			         p.compatibility,
			         '$[*]' COLUMNS (
			             value JSON PATH '$'
			         )
			     ) v
			WHERE p.compatibility IS NOT NULL
			  AND JSON_UNQUOTE(JSON_EXTRACT(v.value, '$.make')) = %s
			  {$model_clause}
			  AND JSON_EXTRACT(v.value, '$.year') IS NOT NULL
			ORDER BY year DESC",
			...$args
		);

		$results = $this->wpdb->get_col( $query );

		return array_map( 'intval', $results ?: array() );
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
				  AND p.compatibility != ''
				  AND p.compatibility != '[]'
				  AND JSON_VALID(p.compatibility)
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
				  AND JSON_UNQUOTE(JSON_EXTRACT(v.value, '$.year')) = %s
				  AND JSON_EXTRACT(v.value, '$.model') IS NOT NULL
				ORDER BY model ASC",
				$make,
				(string) $year
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
			SELECT
				CAST(JSON_UNQUOTE(JSON_EXTRACT(v.value, '$.year')) AS UNSIGNED) as year,
				COUNT(DISTINCT p.id) as count
			FROM {$this->table_parts} p,
			     JSON_TABLE(
			         p.compatibility,
			         '$[*]' COLUMNS (
			             value JSON PATH '$'
			         )
			     ) v
			WHERE p.compatibility IS NOT NULL
			  AND p.compatibility != ''
			  AND p.compatibility != '[]'
			  AND JSON_VALID(p.compatibility)
			  AND JSON_EXTRACT(v.value, '$.year') IS NOT NULL
			GROUP BY year
			ORDER BY year DESC
		";

		$results = $this->wpdb->get_results( $query );

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

		// Allow per_page/page from filters (REST API passes them there).
		if ( isset( $filters['per_page'] ) ) {
			$per_page = intval( $filters['per_page'] );
		}
		if ( isset( $filters['page'] ) ) {
			$page = intval( $filters['page'] );
		}

		// Sort options with whitelist validation.
		$allowed_orderby = array( 'name', 'sku', 'category', 'created_at', 'updated_at', 'latest' );
		$raw_orderby     = $filters['orderby'] ?? 'name';
		$orderby         = in_array( $raw_orderby, $allowed_orderby, true ) ? $raw_orderby : 'name';
		$order           = 'desc' === strtolower( $filters['order'] ?? 'asc' ) ? 'DESC' : 'ASC';

		// Normalize to arrays (support both single values and arrays).
		$categories = ! empty( $categories ) ? (array) $categories : array();
		$makes      = ! empty( $makes ) ? (array) $makes : array();
		$models     = ! empty( $models ) ? (array) $models : array();
		$years      = ! empty( $years ) ? (array) $years : array();

		$offset = ( $page - 1 ) * $per_page;

		// Build WHERE clauses.
		$where_clauses = array( '1=1' );
		$prepare_args  = array();

		// Search keyword (includes SKU, name, description, manufacturer, and interchange numbers).
		if ( ! empty( $search ) ) {
			$where_clauses[] = '(p.sku LIKE %s OR p.name LIKE %s OR p.description LIKE %s OR p.manufacturer LIKE %s OR p.interchange_numbers LIKE %s)';
			$search_term     = '%' . $this->wpdb->esc_like( $search ) . '%';
			$prepare_args[]  = $search_term;
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
				// Convert years to strings (JSON stores years as strings, not integers).
				$years           = array_map( 'strval', $years );
				$placeholders    = implode( ',', array_fill( 0, count( $years ), '%s' ) );
				$where_clauses[] = "JSON_UNQUOTE(JSON_EXTRACT(v.value, '$.year')) IN ($placeholders)";
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
		// "latest" uses whichever is more recent: created_at or updated_at.
		$order_clause = 'latest' === $orderby
			? "GREATEST(p.created_at, p.updated_at) {$order}"
			: "p.{$orderby} {$order}";

		$parts_query     = "SELECT DISTINCT p.* FROM {$from_clause} WHERE {$where_sql} ORDER BY {$order_clause} LIMIT %d OFFSET %d";
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
