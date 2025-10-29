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
	 * Constructor.
	 */
	public function __construct() {
		// Register AJAX handlers for logged-in and non-logged-in users.
		add_action( 'wp_ajax_csf_search_parts', array( $this, 'search_parts' ) );
		add_action( 'wp_ajax_nopriv_csf_search_parts', array( $this, 'search_parts' ) );
		add_action( 'wp_ajax_csf_load_more_parts', array( $this, 'load_more_parts' ) );
		add_action( 'wp_ajax_nopriv_csf_load_more_parts', array( $this, 'load_more_parts' ) );
		add_action( 'wp_ajax_csf_get_makes_by_year', array( $this, 'get_makes_by_year' ) );
		add_action( 'wp_ajax_nopriv_csf_get_makes_by_year', array( $this, 'get_makes_by_year' ) );
		add_action( 'wp_ajax_csf_get_models_by_year_make', array( $this, 'get_models_by_year_make' ) );
		add_action( 'wp_ajax_nopriv_csf_get_models_by_year_make', array( $this, 'get_models_by_year_make' ) );
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

		// Get database instance.
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-database.php';
		$database = new CSF_Parts_Database();

		// Search by SKU, name, or category (V2 database query).
		$filters = array(
			'search' => $search_query,
		);

		$results = $database->query_parts( $filters, 10, 1 );

		// Format results for AJAX response.
		$parts = array();
		foreach ( $results as $part ) {
			// Generate part URL (V2 format: /parts/category-sku).
			$category_slug = strtolower( str_replace( array( ' ', '/', '&' ), '-', $part->category ) );
			$category_slug = preg_replace( '/-+/', '-', $category_slug );
			$part_url      = home_url( '/parts/' . $category_slug . '-' . $part->sku );

			// Get primary image from JSON.
			$primary_image = null;
			if ( ! empty( $part->images ) ) {
				$images = json_decode( $part->images, true );
				if ( is_array( $images ) && ! empty( $images ) ) {
					$first_image = $images[0];
					if ( is_string( $first_image ) ) {
						$primary_image = $first_image;
					} elseif ( is_array( $first_image ) && isset( $first_image['url'] ) ) {
						$primary_image = $first_image['url'];
					}
				}
			}

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

		// Get database instance.
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-database.php';
		$database = new CSF_Parts_Database();

		// Query parts.
		$result      = $database->query_parts( $filters, $per_page, $page );
		$parts       = $result['parts'] ?? array();
		$total_parts = $result['total'] ?? 0;
		$total_pages = $per_page > 0 ? ceil( $total_parts / $per_page ) : 1;

		// Helper function to generate part URL.
		$get_part_url = function( $category, $sku ) {
			$category_slug = strtolower( str_replace( array( ' ', '/', '&' ), '-', $category ) );
			$category_slug = preg_replace( '/-+/', '-', $category_slug );
			return home_url( '/parts/' . $category_slug . '-' . $sku );
		};

		// Helper function to get primary image from JSON.
		$get_primary_image = function( $images_json ) {
			if ( empty( $images_json ) ) {
				return null;
			}

			$images = json_decode( $images_json, true );
			if ( ! is_array( $images ) || empty( $images ) ) {
				return null;
			}

			$first_image = $images[0];
			if ( is_string( $first_image ) ) {
				return $first_image;
			}
			if ( is_array( $first_image ) && isset( $first_image['url'] ) ) {
				return $first_image['url'];
			}

			return null;
		};

		// Build HTML for parts.
		ob_start();
		foreach ( $parts as $part ) {
			$part_url      = $get_part_url( $part->category, $part->sku );
			$display_title = ! empty( $part->name ) ? $part->name : $part->category . ' - ' . $part->sku;
			$primary_image = $get_primary_image( $part->images );
			?>
			<div class="csf-grid-item" style="border: 1px solid #ddd; border-radius: 4px; padding: 16px;">
				<?php if ( $primary_image ) : ?>
					<div class="csf-item-image" style="margin-bottom: 12px;">
						<a href="<?php echo esc_url( $part_url ); ?>">
							<img
								src="<?php echo esc_url( $primary_image ); ?>"
								alt="<?php echo esc_attr( $display_title ); ?>"
								style="width: 100%; height: auto; border-radius: 4px;"
							/>
						</a>
					</div>
				<?php endif; ?>
				<div class="csf-item-content">
					<h3 class="csf-item-title" style="margin: 0 0 8px; font-size: 16px;">
						<a href="<?php echo esc_url( $part_url ); ?>" style="text-decoration: none; color: #333;">
							<?php echo esc_html( $display_title ); ?>
						</a>
					</h3>
					<p class="csf-item-sku" style="margin: 4px 0; font-size: 13px; color: #757575;">
						<strong><?php esc_html_e( 'SKU:', 'csf-parts' ); ?></strong> <?php echo esc_html( $part->sku ); ?>
					</p>
					<?php if ( ! is_null( $part->price ) && $part->price > 0 ) : ?>
						<p class="csf-item-price" style="margin: 4px 0; font-size: 14px; font-weight: 600; color: #2c3e50;">
							$<?php echo esc_html( number_format( $part->price, 2 ) ); ?>
						</p>
					<?php endif; ?>
					<a
						href="<?php echo esc_url( $part_url ); ?>"
						class="csf-item-link"
						style="display: inline-block; margin-top: 8px; padding: 6px 12px; background: #0073aa; color: #fff; text-decoration: none; border-radius: 3px; font-size: 13px;"
					>
						<?php esc_html_e( 'View Details', 'csf-parts' ); ?>
					</a>
				</div>
			</div>
			<?php
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

		// Get database instance.
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-database.php';
		$database = new CSF_Parts_Database();

		// Get makes for year.
		$makes = $database->get_vehicle_makes_by_year( $year );

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

		if ( $year <= 0 || empty( $make ) ) {
			wp_send_json_error( array( 'message' => 'Invalid year or make parameter' ) );
		}

		// Get database instance.
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-database.php';
		$database = new CSF_Parts_Database();

		// Get models for year and make.
		$models = $database->get_vehicle_models( $make, $year );

		wp_send_json_success( array( 'models' => $models ) );
	}
}
