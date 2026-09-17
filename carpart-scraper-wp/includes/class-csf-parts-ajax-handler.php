<?php
/**
 * AJAX Handler.
 *
 * Handles AJAX requests for frontend features.
 *
 * @package CSF_Parts_Catalog
 * @since   1.0.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

/**
 * Class CSF_Parts_AJAX_Handler
 */
class CSF_Parts_AJAX_Handler {

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
		// Initialize database instance (reused across all AJAX methods).
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-database.php';
		$this->database = new CSF_Parts_Database();

		// Register AJAX handlers for logged-in and non-logged-in users.
		add_action( 'wp_ajax_csf_search_parts', array( $this, 'search_parts' ) );
		add_action( 'wp_ajax_nopriv_csf_search_parts', array( $this, 'search_parts' ) );
		add_action( 'wp_ajax_csf_load_more_parts', array( $this, 'load_more_parts' ) );
		add_action( 'wp_ajax_nopriv_csf_load_more_parts', array( $this, 'load_more_parts' ) );
		add_action( 'wp_ajax_csf_get_makes_by_year', array( $this, 'get_makes_by_year' ) );
		add_action( 'wp_ajax_nopriv_csf_get_makes_by_year', array( $this, 'get_makes_by_year' ) );
		add_action( 'wp_ajax_csf_get_models_by_year_make', array( $this, 'get_models_by_year_make' ) );
		add_action( 'wp_ajax_csf_get_years_by_make', array( $this, 'get_years_by_make' ) );
		add_action( 'wp_ajax_nopriv_csf_get_years_by_make', array( $this, 'get_years_by_make' ) );
		add_action( 'wp_ajax_nopriv_csf_get_models_by_year_make', array( $this, 'get_models_by_year_make' ) );
		add_action( 'wp_ajax_csf_filter_products', array( $this, 'filter_products' ) );
		add_action( 'wp_ajax_nopriv_csf_filter_products', array( $this, 'filter_products' ) );

		// Admin-only: refresh part from detail page.
		add_action( 'wp_ajax_csf_refresh_part', array( $this, 'refresh_part' ) );
	}

	/**
	 * Search parts via AJAX (V2 Architecture).
	 *
	 * Uses custom database table for direct queries.
	 *
	 * @since 1.0.0
	 */
	public function search_parts(): void {
		// Verify nonce.
		check_ajax_referer( 'csf_parts_search', 'nonce' );

		$search_query = isset( $_GET['s'] ) ? sanitize_text_field( wp_unslash( $_GET['s'] ) ) : '';

		if ( empty( $search_query ) ) {
			wp_send_json_success( array( 'parts' => array() ) );
		}

		// Search by SKU, name, or category (V2 database query).
		$filters = array(
			'search' => $search_query,
		);

		$results = $this->database->query_parts( $filters, 10, 1 );

		// Format results for AJAX response.
		$parts = array();
		foreach ( $results as $part ) {
			// Generate part URL using shared helper function.
			$part_url = csf_get_part_url( $part->sku );

			// Get primary image using shared helper.
			$primary_image = $this->get_primary_image( $part->images );

			// Display title with fallback.
			$display_title = ! empty( $part->name ) ? $part->name : $part->category . ' - ' . $part->sku;

			$parts[] = array(
				'id'      => $part->id,
				'title'   => $display_title,
				'sku'     => $part->sku,
				'price'   => $part->price,
				'excerpt' => ! empty( $part->description ) ? wp_trim_words( $part->description, 20 ) : '',
				'image'   => $primary_image,
				'link'    => $part_url,
			);
		}

		wp_send_json_success(
			array(
				'parts' => $parts,
				'total' => count( $parts ),
			)
		);
	}

	/**
	 * Load more parts for pagination via AJAX.
	 *
	 * Handles endless scroll and load more button functionality.
	 *
	 * @since 2.0.0
	 */
	public function load_more_parts(): void {
		// Verify nonce.
		check_ajax_referer( 'csf_parts_pagination', 'nonce' );

		// Get pagination parameters.
		$page     = isset( $_POST['page'] ) ? max( 1, intval( $_POST['page'] ) ) : 1;
		$per_page = isset( $_POST['per_page'] ) ? max( 1, min( 100, intval( $_POST['per_page'] ) ) ) : 12;

		// Get filter parameters.
		$filters = array();

		if ( ! empty( $_POST['year'] ) ) {
			$filters['years'] = array( sanitize_text_field( wp_unslash( $_POST['year'] ) ) );
		}
		if ( ! empty( $_POST['make'] ) ) {
			$filters['makes'] = array( sanitize_text_field( wp_unslash( $_POST['make'] ) ) );
		}
		if ( ! empty( $_POST['model'] ) ) {
			$filters['models'] = array( sanitize_text_field( wp_unslash( $_POST['model'] ) ) );
		}
		if ( ! empty( $_POST['category'] ) ) {
			$filters['categories'] = array( sanitize_text_field( wp_unslash( $_POST['category'] ) ) );
		}

		// Sort options (validated against whitelist in query_parts).
		if ( ! empty( $_POST['orderby'] ) ) {
			$filters['orderby'] = sanitize_key( wp_unslash( $_POST['orderby'] ) );
		}
		if ( ! empty( $_POST['order'] ) ) {
			$filters['order'] = sanitize_key( wp_unslash( $_POST['order'] ) );
		}

		// Query parts using shared database instance.
		$result      = $this->database->query_parts( $filters, $per_page, $page );
		$parts       = $result['parts'] ?? array();
		$total_parts = $result['total'] ?? 0;
		$total_pages = $per_page > 0 ? ceil( $total_parts / $per_page ) : 1;

		// Build HTML for parts.
		ob_start();
		foreach ( $parts as $part ) {
			echo CSF_Parts_Part_Card::render( $part, csf_get_part_url( $part->sku ) ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Escaped in the renderer.
		}
		$html = ob_get_clean();

		wp_send_json_success(
			array(
				'html'         => $html,
				'current_page' => $page,
				'total_pages'  => $total_pages,
				'has_more'     => $page < $total_pages,
			)
		);
	}

	/**
	 * Get vehicle makes for a specific year via AJAX.
	 *
	 * @since 2.0.0
	 */
	public function get_makes_by_year(): void {
		// Verify nonce.
		check_ajax_referer( 'csf_parts_filter', 'nonce' );

		// Get year parameter.
		$year = isset( $_POST['year'] ) ? intval( $_POST['year'] ) : 0;

		if ( $year <= 0 ) {
			wp_send_json_error( array( 'message' => 'Invalid year parameter' ) );
		}

		// Get makes for year using shared database instance.
		$makes = $this->database->get_vehicle_makes_by_year( $year );

		wp_send_json_success( array( 'makes' => $makes ) );
	}

	/**
	 * Get vehicle models for a specific year and make via AJAX.
	 *
	 * @since 2.0.0
	 */
	public function get_models_by_year_make(): void {
		// Verify nonce.
		check_ajax_referer( 'csf_parts_filter', 'nonce' );

		// Get parameters.
		$year = isset( $_POST['year'] ) ? intval( $_POST['year'] ) : 0;
		$make = isset( $_POST['make'] ) ? sanitize_text_field( wp_unslash( $_POST['make'] ) ) : '';

		if ( empty( $make ) ) {
			wp_send_json_error( array( 'message' => 'Invalid make parameter' ) );
		}

		// Get models for the make, narrowed by year when one was chosen.
		$models = $this->database->get_vehicle_models( $make, $year > 0 ? $year : null );

		wp_send_json_success( array( 'models' => $models ) );
	}

	/**
	 * Get vehicle years for a make (optionally a model) via AJAX.
	 *
	 * Lets the Part Finder narrow the Year list when Make/Model are chosen first.
	 *
	 * @since 1.12.0
	 */
	public function get_years_by_make(): void {
		check_ajax_referer( 'csf_parts_filter', 'nonce' );

		$make  = isset( $_POST['make'] ) ? sanitize_text_field( wp_unslash( $_POST['make'] ) ) : '';
		$model = isset( $_POST['model'] ) ? sanitize_text_field( wp_unslash( $_POST['model'] ) ) : '';

		if ( '' === $make ) {
			wp_send_json_error( array( 'message' => 'Invalid make parameter' ) );
		}

		wp_send_json_success( array( 'years' => $this->database->get_vehicle_years_by_make( $make, $model ) ) );
	}

	/**
	 * Filter products via AJAX without page reload.
	 *
	 * Returns HTML for filtered results grid matching render.php structure.
	 *
	 * @since 2.0.0
	 */
	public function filter_products(): void {
		// Verify nonce.
		check_ajax_referer( 'csf_parts_filter', 'nonce' );

		// Get filter parameters.
		$selected_year  = isset( $_POST['csf_year'] ) ? sanitize_text_field( wp_unslash( $_POST['csf_year'] ) ) : '';
		$selected_make  = isset( $_POST['csf_make'] ) ? sanitize_text_field( wp_unslash( $_POST['csf_make'] ) ) : '';
		$selected_model = isset( $_POST['csf_model'] ) ? sanitize_text_field( wp_unslash( $_POST['csf_model'] ) ) : '';
		$search_query   = isset( $_POST['csf_search'] ) ? sanitize_text_field( wp_unslash( $_POST['csf_search'] ) ) : '';

		// Get default categories from block attributes (passed via JS).
		$default_categories = array();
		if ( ! empty( $_POST['default_categories'] ) ) {
			$decoded = json_decode( sanitize_text_field( wp_unslash( $_POST['default_categories'] ) ), true );
			if ( is_array( $decoded ) ) {
				$default_categories = array_map( 'sanitize_text_field', $decoded );
			}
		}

		// A category chosen by the visitor narrows within (or replaces) the editor defaults.
		$selected_category = isset( $_POST['csf_category'] ) ? sanitize_text_field( wp_unslash( $_POST['csf_category'] ) ) : '';

		// Card rendering options (badge window, summary lines) come from the block.
		$card_options = array();
		if ( ! empty( $_POST['card_options'] ) ) {
			$decoded_options = json_decode( sanitize_text_field( wp_unslash( $_POST['card_options'] ) ), true );
			if ( is_array( $decoded_options ) ) {
				$card_options = $decoded_options;
			}
		}

		$filters = array();
		if ( '' !== $selected_category ) {
			$filters['categories'] = array( $selected_category );
		} elseif ( ! empty( $default_categories ) ) {
			$filters['categories'] = $default_categories;
		}
		if ( ! empty( $selected_year ) ) {
			$filters['years'] = array( $selected_year );
		}
		if ( ! empty( $selected_make ) ) {
			$filters['makes'] = array( $selected_make );
		}
		if ( ! empty( $selected_model ) ) {
			$filters['models'] = array( $selected_model );
		}
		if ( ! empty( $search_query ) ) {
			$filters['search'] = $search_query;
		}

		// Sort options (validated against whitelist in query_parts).
		if ( ! empty( $_POST['orderby'] ) ) {
			$filters['orderby'] = sanitize_key( wp_unslash( $_POST['orderby'] ) );
		}
		if ( ! empty( $_POST['order'] ) ) {
			$filters['order'] = sanitize_key( wp_unslash( $_POST['order'] ) );
		}

		// Get pagination parameters from request.
		$per_page     = isset( $_POST['per_page'] ) ? absint( $_POST['per_page'] ) : 12;
		$per_page     = min( max( $per_page, 1 ), 100 ); // Clamp between 1 and 100.
		$current_page = isset( $_POST['page'] ) ? max( 1, absint( $_POST['page'] ) ) : 1;

		// Query parts using shared database instance.
		$result      = $this->database->query_parts( $filters, $per_page, $current_page );
		$parts       = $result['parts'] ?? array();
		$total_parts = $result['total'] ?? 0;

		// Helper function to generate part URL with filter params.
		$get_part_url = function( $category, $sku ) use ( $selected_year, $selected_make, $selected_model ) {
			// Use shared helper for base URL generation.
			$base_url = csf_get_part_url( $sku );

			$params = array();
			if ( ! empty( $selected_year ) ) {
				$params['csf_year'] = $selected_year;
			}
			if ( ! empty( $selected_make ) ) {
				$params['csf_make'] = $selected_make;
			}
			if ( ! empty( $selected_model ) ) {
				$params['csf_model'] = $selected_model;
			}

			return ! empty( $params ) ? add_query_arg( $params, $base_url ) : $base_url;
		};

		// Build HTML for parts matching render.php structure.
		ob_start();
		if ( empty( $parts ) ) {
			?>
			<div class="csf-no-results">
				<p class="csf-no-results__text">No parts found matching your selection. Please try different filters.</p>
			</div>
			<?php
		} else {
			foreach ( $parts as $part ) {
				echo CSF_Parts_Part_Card::render( $part, $get_part_url( $part->category, $part->sku ), $card_options ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Escaped in the renderer.
			}
		}
		$html = ob_get_clean();

		$total_pages = $per_page > 0 ? (int) ceil( $total_parts / $per_page ) : 1;

		wp_send_json_success(
			array(
				'html'        => $html,
				'count'       => $total_parts,
				'total_pages' => $total_pages,
				'per_page'    => $per_page,
				'page'        => $current_page,
			)
		);
	}

	/**
	 * Refresh a single part from its detail page.
	 *
	 * Fetches the latest detail data (specs, tech notes, interchange, images)
	 * from csf.autocaredata.com and merges with existing part data.
	 *
	 * @since 1.1.5
	 */
	public function refresh_part(): void {
		// Verify nonce.
		check_ajax_referer( 'csf_parts_admin', 'nonce' );

		// Check capability.
		if ( ! current_user_can( 'manage_options' ) ) {
			wp_send_json_error( array( 'message' => 'Insufficient permissions.' ) );
		}

		$part_id = isset( $_POST['part_id'] ) ? intval( $_POST['part_id'] ) : 0;
		if ( $part_id <= 0 ) {
			wp_send_json_error( array( 'message' => 'Invalid part ID.' ) );
		}

		// Get existing part.
		$part = $this->database->get_part_by_id( $part_id );
		if ( ! $part ) {
			wp_send_json_error( array( 'message' => 'Part not found.' ) );
		}

		// Fetch detail page data.
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-detail-fetcher.php';
		$fetcher     = new CSF_Parts_Detail_Fetcher();
		$detail_data = $fetcher->fetch( $part->sku );

		if ( is_wp_error( $detail_data ) ) {
			wp_send_json_error( array( 'message' => $detail_data->get_error_message() ) );
		}

		// Merge detail data with existing part data (preserve fields not on detail page).
		$existing_specs = ! empty( $part->specifications ) ? json_decode( $part->specifications, true ) : array();
		if ( ! is_array( $existing_specs ) ) {
			$existing_specs = array();
		}
		$merged_specs = array_merge( $existing_specs, $detail_data['specifications'] );

		$update_data = array(
			'sku'                 => $part->sku,
			'name'                => $part->name,
			'category'            => $part->category,
			'price'               => $part->price,
			'manufacturer'        => $part->manufacturer,
			'in_stock'            => $part->in_stock,
			'position'            => $part->position,
			'short_description'   => $part->short_description,
			'compatibility'       => json_decode( $part->compatibility, true ),
			'scraped_at'          => $part->scraped_at,
			'specifications'      => $merged_specs,
			'tech_notes'          => $detail_data['tech_notes'] ?? $part->tech_notes,
			'interchange_numbers' => ! empty( $detail_data['interchange_numbers'] ) ? $detail_data['interchange_numbers'] : json_decode( $part->interchange_numbers, true ),
			'features'            => json_decode( $part->features, true ),
		);

		// Update description only if detail page returned one.
		if ( ! empty( $detail_data['description'] ) ) {
			$update_data['description'] = $detail_data['description'];
		} else {
			$update_data['description'] = $part->description;
		}

		// Update images only if detail page returned new ones.
		if ( ! empty( $detail_data['images'] ) ) {
			$update_data['images'] = $detail_data['images'];
		} else {
			$update_data['images'] = json_decode( $part->images, true );
		}

		// Upsert the merged data.
		$result = $this->database->upsert_part( $update_data );

		if ( false === $result['id'] ) {
			wp_send_json_error( array( 'message' => 'Failed to update part in database.' ) );
		}

		wp_send_json_success(
			array(
				'message'        => sprintf( 'Refreshed %s successfully.', $part->sku ),
				'fields_updated' => $detail_data['fields_updated'],
				'sku'            => $part->sku,
			)
		);
	}

	/**
	 * Get primary image from JSON (shared helper).
	 *
	 * Prefers second image (product photo) if available, otherwise uses first (technical drawing).
	 * Returns placeholder image if no images are available.
	 *
	 * @since 2.0.0
	 * @param string $images_json JSON encoded images array.
	 * @return string Image URL or placeholder if none found.
	 */
	private function get_primary_image( string $images_json ): string {
		if ( empty( $images_json ) ) {
			return csf_get_placeholder_image_url();
		}

		$images = json_decode( $images_json, true );
		if ( ! is_array( $images ) || empty( $images ) ) {
			return csf_get_placeholder_image_url();
		}

		// Prefer second image (product photo) if available, otherwise use first (technical drawing).
		$image_index = isset( $images[1] ) ? 1 : 0;
		$image       = $images[ $image_index ];

		$raw_url = null;
		if ( is_string( $image ) ) {
			$raw_url = $image;
		} elseif ( is_array( $image ) && isset( $image['url'] ) ) {
			$raw_url = $image['url'];
		}

		return $raw_url ? csf_resolve_image_url( $raw_url ) : csf_get_placeholder_image_url();
	}
}
