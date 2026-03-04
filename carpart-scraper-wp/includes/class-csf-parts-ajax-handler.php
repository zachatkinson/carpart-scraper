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

		// Query parts using shared database instance.
		$result      = $this->database->query_parts( $filters, $per_page, $page );
		$parts       = $result['parts'] ?? array();
		$total_parts = $result['total'] ?? 0;
		$total_pages = $per_page > 0 ? ceil( $total_parts / $per_page ) : 1;

		// Build HTML for parts.
		ob_start();
		foreach ( $parts as $part ) {
			$part_url      = csf_get_part_url( $part->sku );
			$display_title = ! empty( $part->name ) ? $part->name : $part->category . ' - ' . $part->sku;
			$primary_image = $this->get_primary_image( $part->images );
			?>
			<div class="csf-grid-item" style="border: 1px solid #ddd; border-radius: 4px; padding: 16px;">
				<div class="csf-item-image" style="margin-bottom: 12px;">
					<a href="<?php echo esc_url( $part_url ); ?>">
						<img
							src="<?php echo esc_url( $primary_image ); ?>"
							alt="<?php echo esc_attr( $display_title ); ?>"
							style="width: 100%; height: auto; border-radius: 4px;"
						/>
					</a>
				</div>
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
							$<?php echo esc_html( number_format( (float) $part->price, 2 ) ); ?>
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

		if ( $year <= 0 || empty( $make ) ) {
			wp_send_json_error( array( 'message' => 'Invalid year or make parameter' ) );
		}

		// Get models for year and make using shared database instance.
		$models = $this->database->get_vehicle_models( $make, $year );

		wp_send_json_success( array( 'models' => $models ) );
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

		$filters = array();
		if ( ! empty( $default_categories ) ) {
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

		// Query parts using shared database instance.
		$result      = $this->database->query_parts( $filters, 100, 1 );
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

		// Helper function to get dimensions.
		$get_dimensions = function( $specifications_json ) {
			$specs = json_decode( $specifications_json, true );
			if ( ! is_array( $specs ) ) {
				return null;
			}

			$length = $specs['Box Length (in)'] ?? null;
			$width  = $specs['Box Width (in)'] ?? null;
			$height = $specs['Box Height (in)'] ?? null;

			if ( ! $length || ! $width || ! $height ) {
				return null;
			}

			// Format fractions (basic version).
			return sprintf( '%s" × %s" × %s"', $length, $width, $height );
		};

		// Build HTML for parts matching render.php structure.
		ob_start();
		if ( empty( $parts ) ) {
			?>
			<div class="csf-no-results" style="padding: 24px; text-align: center; background: #f9f9f9; border-radius: 4px;">
				<p style="margin: 0;">No parts found matching your selection. Please try different filters.</p>
			</div>
			<?php
		} else {
			foreach ( $parts as $part ) {
				$part_url      = $get_part_url( $part->category, $part->sku );
				$display_title = csf_format_sku_display( $part->sku );  // Use shared helper for consistent formatting.
				$primary_image = $this->get_primary_image( $part->images );
				$dimensions    = $get_dimensions( $part->specifications );

				// Get compatibility data for fitment badges.
				$compatibility_data = ! empty( $part->compatibility ) ? json_decode( $part->compatibility, true ) : array();
				$part_makes         = array();
				if ( is_array( $compatibility_data ) ) {
					foreach ( $compatibility_data as $vehicle ) {
						if ( isset( $vehicle['make'] ) && ! in_array( $vehicle['make'], $part_makes, true ) ) {
							$part_makes[] = $vehicle['make'];
						}
					}
				}
				?>
				<article class="csf-part-card">
					<a href="<?php echo esc_url( $part_url ); ?>" class="csf-part-card__link">
						<?php if ( $primary_image ) : ?>
							<div class="csf-part-card__image">
								<img
									src="<?php echo esc_url( $primary_image ); ?>"
									alt="<?php echo esc_attr( $display_title ); ?>"
									loading="lazy"
								/>
								<?php if ( ! empty( $part->category ) ) : ?>
									<span class="csf-part-card__badge"><?php echo esc_html( $part->category ); ?></span>
								<?php endif; ?>
							</div>
						<?php else : ?>
							<div class="csf-part-card__image csf-part-card__image--placeholder">
								<svg width="48" height="48" viewBox="0 0 20 20" fill="currentColor" opacity="0.2">
									<path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd"/>
								</svg>
								<?php if ( ! empty( $part->category ) ) : ?>
									<span class="csf-part-card__badge"><?php echo esc_html( $part->category ); ?></span>
								<?php endif; ?>
							</div>
						<?php endif; ?>
						<div class="csf-part-card__content">
							<h3 class="csf-part-card__title"><?php echo esc_html( $display_title ); ?></h3>
							<?php if ( ! empty( $dimensions ) ) : ?>
								<div class="csf-dimensions-section">
									<p class="csf-dimensions-section__label">Dimensions</p>
									<p class="csf-dimensions-section__value"><?php echo esc_html( $dimensions ); ?></p>
								</div>
							<?php endif; ?>
							<?php if ( ! empty( $part_makes ) ) : ?>
								<div class="csf-fitment-section">
									<p class="csf-fitment-section__label">Fits Models By</p>
									<div class="csf-part-card__makes">
										<?php
										$max_badges    = 4;
										$display_makes = array_slice( $part_makes, 0, $max_badges );
										foreach ( $display_makes as $make ) :
										?>
											<span class="csf-part-card__make-badge"><?php echo esc_html( $make ); ?></span>
										<?php endforeach; ?>
										<?php if ( count( $part_makes ) > $max_badges ) : ?>
											<span class="csf-part-card__make-badge csf-part-card__make-badge--more">+<?php echo esc_html( count( $part_makes ) - $max_badges ); ?></span>
										<?php endif; ?>
									</div>
								</div>
							<?php endif; ?>
						</div>
					</a>
				</article>
				<?php
			}
		}
		$html = ob_get_clean();

		wp_send_json_success(
			array(
				'html'  => $html,
				'count' => $total_parts,
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

		if ( false === $result ) {
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
