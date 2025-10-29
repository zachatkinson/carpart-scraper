<?php
/**
 * Server-side render for Product Catalog block (V2 Architecture).
 *
 * Unified block supporting:
 * - Static showcases (editor sets defaults, hides filters)
 * - Interactive search (users filter via dropdowns)
 * - Hybrid (defaults with user override)
 *
 * @package CSF_Parts_Catalog
 * @since   2.0.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

// Get block attributes with defaults.
$default_years      = $attributes['defaultYears'] ?? array();
$default_makes      = $attributes['defaultMakes'] ?? array();
$default_models     = $attributes['defaultModels'] ?? array();
$default_categories = $attributes['defaultCategories'] ?? array();
$show_filters       = $attributes['showFilters'] ?? true;
$show_year_filter   = $attributes['showYearFilter'] ?? true;
$show_make_filter   = $attributes['showMakeFilter'] ?? true;
$show_model_filter  = $attributes['showModelFilter'] ?? true;
$show_category_filter = $attributes['showCategoryFilter'] ?? false;
$per_page           = $attributes['perPage'] ?? 12;
// Get responsive columns.
$columns = wp_parse_args(
	$attributes['columns'] ?? array(),
	array(
		'mobile'  => 2,
		'tablet'  => 3,
		'desktop' => 4,
	)
);

// Get responsive gap.
$gap = wp_parse_args(
	$attributes['gap'] ?? array(),
	array(
		'mobile'  => 16,
		'tablet'  => 20,
		'desktop' => 24,
	)
);

$button_text         = $attributes['buttonText'] ?? __( 'Find Parts', 'csf-parts' );
$enable_ajax         = $attributes['enableAjax'] ?? true;
$pagination_type     = $attributes['paginationType'] ?? 'numbered';
$image_aspect_ratio  = $attributes['imageAspectRatio'] ?? '1/1';
$hover_effect        = $attributes['hoverEffect'] ?? 'lift';
$border_radius       = absint( $attributes['borderRadius'] ?? 4 );
$border_width        = absint( $attributes['borderWidth'] ?? 1 );
$border_color        = sanitize_hex_color( $attributes['borderColor'] ?? '#dddddd' );
$card_shadow         = $attributes['cardShadow'] ?? 'sm';
$block_padding       = $attributes['blockPadding'] ?? array( 'top' => 0, 'right' => 0, 'bottom' => 0, 'left' => 0 );
$block_margin        = $attributes['blockMargin'] ?? array( 'top' => 0, 'right' => 0, 'bottom' => 0, 'left' => 0 );
$hide_on_mobile      = $attributes['hideOnMobile'] ?? false;
$hide_on_tablet      = $attributes['hideOnTablet'] ?? false;
$hide_on_desktop     = $attributes['hideOnDesktop'] ?? false;
$scroll_animation    = $attributes['scrollAnimation'] ?? 'none';
$color_scheme        = $attributes['colorScheme'] ?? 'default';

// Get current page from URL.
$current_page = 1;
if ( isset( $_GET['csf_page'] ) && is_numeric( $_GET['csf_page'] ) ) {
	$current_page = max( 1, intval( $_GET['csf_page'] ) );
}

// Get database instance.
require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-database.php';
$database = new CSF_Parts_Database();

// Build filter array starting with defaults.
$filters = array();

// Start with editor's multi-value defaults.
if ( ! empty( $default_years ) ) {
	$filters['years'] = $default_years;
}
if ( ! empty( $default_makes ) ) {
	$filters['makes'] = $default_makes;
}
if ( ! empty( $default_models ) ) {
	$filters['models'] = $default_models;
}
if ( ! empty( $default_categories ) ) {
	$filters['categories'] = $default_categories;
}

// If filters shown, allow user to override with GET params (single values).
$selected_year     = '';
$selected_make     = '';
$selected_model    = '';
$selected_category = '';

if ( $show_filters ) {
	if ( isset( $_GET['csf_year'] ) && ! empty( $_GET['csf_year'] ) ) {
		$selected_year      = sanitize_text_field( wp_unslash( $_GET['csf_year'] ) );
		$filters['years']   = array( $selected_year );
	}
	if ( isset( $_GET['csf_make'] ) && ! empty( $_GET['csf_make'] ) ) {
		$selected_make      = sanitize_text_field( wp_unslash( $_GET['csf_make'] ) );
		$filters['makes']   = array( $selected_make );
	}
	if ( isset( $_GET['csf_model'] ) && ! empty( $_GET['csf_model'] ) ) {
		$selected_model     = sanitize_text_field( wp_unslash( $_GET['csf_model'] ) );
		$filters['models']  = array( $selected_model );
	}
	if ( isset( $_GET['csf_category'] ) && ! empty( $_GET['csf_category'] ) ) {
		$selected_category       = sanitize_text_field( wp_unslash( $_GET['csf_category'] ) );
		$filters['categories']   = array( $selected_category );
	}
}

// Query parts from database (V2).
$result      = $database->query_parts( $filters, $per_page, $current_page );
$parts       = $result['parts'] ?? array();
$total_parts = $result['total'] ?? 0;
$total_pages = $per_page > 0 ? ceil( $total_parts / $per_page ) : 1;

// Get filter options (for dropdowns).
$years      = array();
$makes      = array();
$models     = array();
$categories = array();

if ( $show_filters ) {
	if ( $show_year_filter ) {
		$years = $database->get_vehicle_years();
	}
	if ( $show_make_filter ) {
		$makes = $database->get_vehicle_makes();
	}
	if ( $show_model_filter ) {
		$models = $database->get_vehicle_models();
	}
	if ( $show_category_filter ) {
		$categories = $database->get_all_categories();
	}
}

// Generate unique ID for this instance.
$block_id = 'csf-product-catalog-' . wp_rand( 1000, 9999 );

// Enqueue pagination script for AJAX pagination types.
if ( $enable_ajax && in_array( $pagination_type, array( 'endless', 'loadmore' ), true ) ) {
	wp_enqueue_script(
		'csf-parts-pagination',
		plugins_url( 'pagination.js', __FILE__ ),
		array(),
		filemtime( __DIR__ . '/pagination.js' ),
		true
	);

	// Localize script with AJAX URL and nonce.
	wp_localize_script(
		'csf-parts-pagination',
		'csfPartsPagination',
		array(
			'ajaxUrl'         => admin_url( 'admin-ajax.php' ),
			'nonce'           => wp_create_nonce( 'csf_parts_pagination' ),
			'loadMoreSingle'  => __( 'Load More (%d page remaining)', 'csf-parts' ),
			'loadMorePlural'  => __( 'Load More (%d pages remaining)', 'csf-parts' ),
		)
	);
}

// Enqueue cascading filters script if filters are shown.
if ( $show_filters ) {
	wp_enqueue_script(
		'csf-parts-filters',
		plugins_url( 'filters.js', __FILE__ ),
		array(),
		filemtime( __DIR__ . '/filters.js' ),
		true
	);

	// Localize script with AJAX URL, nonce, and translation strings.
	wp_localize_script(
		'csf-parts-filters',
		'csfPartsFilters',
		array(
			'ajaxUrl'     => admin_url( 'admin-ajax.php' ),
			'nonce'       => wp_create_nonce( 'csf_parts_filter' ),
			'selectMake'  => __( 'Select Make', 'csf-parts' ),
			'selectModel' => __( 'Select Model', 'csf-parts' ),
			'loading'     => __( 'Loading...', 'csf-parts' ),
			'noMakes'     => __( 'No makes available', 'csf-parts' ),
			'noModels'    => __( 'No models available', 'csf-parts' ),
			'error'       => __( 'Error loading options', 'csf-parts' ),
		)
	);
}

// Helper function to generate part URL (V2 format: /parts/category-sku).
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

	// Return first image URL.
	$first_image = $images[0];
	if ( is_string( $first_image ) ) {
		return $first_image;
	}
	if ( is_array( $first_image ) && isset( $first_image['url'] ) ) {
		return $first_image['url'];
	}

	return null;
};
?>
<?php
// Helper: Get shadow CSS value.
$get_shadow_css = function( $shadow_type ) {
	switch ( $shadow_type ) {
		case 'none':
			return 'none';
		case 'sm':
			return '0 1px 2px 0 rgba(0, 0, 0, 0.05)';
		case 'md':
			return '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)';
		case 'lg':
			return '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)';
		case 'xl':
			return '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)';
		default:
			return 'none';
	}
};

// Helper: Get color scheme CSS.
$get_color_scheme_css = function( $scheme ) {
	switch ( $scheme ) {
		case 'light':
			return 'background: #ffffff; color: #1a202c;';
		case 'dark':
			return 'background: #2d3748; color: #f7fafc;';
		case 'brand':
			return 'background: #0073aa; color: #ffffff;';
		case 'default':
		default:
			return '';
	}
};

// Generate comprehensive CSS for this block instance.
$comprehensive_css = sprintf(
	'
	/* Block Container */
	#%1$s {
		padding: %2$dpx %3$dpx %4$dpx %5$dpx;
		margin: %6$dpx %7$dpx %8$dpx %9$dpx;
	}

	/* Grid Layout */
	#%1$s .csf-grid-items {
		display: grid;
		gap: %10$dpx;
		grid-template-columns: repeat(%11$d, 1fr);
	}

	/* Card Base Styles */
	#%1$s .csf-grid-item {
		border: %12$dpx solid %13$s;
		border-radius: %14$dpx;
		box-shadow: %15$s;
		transition: all 0.3s ease;
		%16$s
	}

	/* Image Aspect Ratio */
	#%1$s .csf-item-image img {
		width: 100%%;
		height: auto;
		object-fit: cover;
		%17$s
	}

	/* Hover Effects - Lift */
	%18$s

	/* Hover Effects - Zoom */
	%19$s

	/* Hover Effects - Shadow */
	%20$s

	/* Scroll Animation */
	%21$s

	/* Tablet Responsive */
	@media (min-width: 768px) {
		#%1$s .csf-grid-items {
			gap: %22$dpx;
			grid-template-columns: repeat(%23$d, 1fr);
		}
		%24$s
	}

	/* Desktop Responsive */
	@media (min-width: 1024px) {
		#%1$s .csf-grid-items {
			gap: %25$dpx;
			grid-template-columns: repeat(%26$d, 1fr);
		}
		%27$s
	}
	',
	// 1. Block ID
	esc_attr( $block_id ),
	// 2-5. Block padding
	absint( $block_padding['top'] ?? 0 ),
	absint( $block_padding['right'] ?? 0 ),
	absint( $block_padding['bottom'] ?? 0 ),
	absint( $block_padding['left'] ?? 0 ),
	// 6-9. Block margin
	absint( $block_margin['top'] ?? 0 ),
	absint( $block_margin['right'] ?? 0 ),
	absint( $block_margin['bottom'] ?? 0 ),
	absint( $block_margin['left'] ?? 0 ),
	// 10-11. Mobile grid
	absint( $gap['mobile'] ),
	absint( $columns['mobile'] ),
	// 12-14. Border
	$border_width,
	esc_attr( $border_color ),
	$border_radius,
	// 15. Shadow
	esc_attr( $get_shadow_css( $card_shadow ) ),
	// 16. Color scheme
	esc_attr( $get_color_scheme_css( $color_scheme ) ),
	// 17. Aspect ratio
	'auto' === $image_aspect_ratio ? '' : 'aspect-ratio: ' . esc_attr( $image_aspect_ratio ) . ';',
	// 18. Hover - Lift
	'lift' === $hover_effect ? '#' . esc_attr( $block_id ) . ' .csf-grid-item:hover { transform: translateY(-4px); box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.15); }' : '',
	// 19. Hover - Zoom
	'zoom' === $hover_effect ? '#' . esc_attr( $block_id ) . ' .csf-grid-item:hover img { transform: scale(1.05); } #' . esc_attr( $block_id ) . ' .csf-item-image { overflow: hidden; }' : '',
	// 20. Hover - Shadow
	'shadow' === $hover_effect ? '#' . esc_attr( $block_id ) . ' .csf-grid-item:hover { box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25); }' : '',
	// 21. Scroll animation
	'none' !== $scroll_animation ? '#' . esc_attr( $block_id ) . ' .csf-grid-item { opacity: 0; animation: csf-' . esc_attr( $scroll_animation ) . ' 0.6s ease forwards; } @keyframes csf-fade { from { opacity: 0; } to { opacity: 1; } } @keyframes csf-slideUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } } @keyframes csf-slideLeft { from { opacity: 0; transform: translateX(20px); } to { opacity: 1; transform: translateX(0); } }' : '',
	// 22-23. Tablet grid
	absint( $gap['tablet'] ),
	absint( $columns['tablet'] ),
	// 24. Hide on tablet
	$hide_on_tablet ? '#' . esc_attr( $block_id ) . ' { display: none !important; }' : '',
	// 25-26. Desktop grid
	absint( $gap['desktop'] ),
	absint( $columns['desktop'] ),
	// 27. Hide on desktop
	$hide_on_desktop ? '#' . esc_attr( $block_id ) . ' { display: none !important; }' : ''
);

// Mobile visibility.
if ( $hide_on_mobile ) {
	$comprehensive_css .= sprintf(
		'
		@media (max-width: 767px) {
			#%s { display: none !important; }
		}
		',
		esc_attr( $block_id )
	);
}

// Output CSS.
echo '<style>' . $comprehensive_css . '</style>';
?>
<div class="csf-product-catalog" id="<?php echo esc_attr( $block_id ); ?>" data-ajax="<?php echo esc_attr( $enable_ajax ? '1' : '0' ); ?>" data-pagination-type="<?php echo esc_attr( $pagination_type ); ?>" data-per-page="<?php echo esc_attr( $per_page ); ?>" data-columns-desktop="<?php echo esc_attr( $columns['desktop'] ); ?>">
	<?php if ( $show_filters ) : ?>
		<form class="csf-catalog-filters csf-filter-form" method="get" action="">
			<div class="csf-filter-controls" style="display: flex; gap: 12px; flex-wrap: wrap; align-items: end; margin-bottom: 24px;">
				<?php if ( $show_year_filter && ! empty( $years ) ) : ?>
					<div class="csf-filter-group" style="flex: 1; min-width: 150px;">
						<label for="<?php echo esc_attr( $block_id ); ?>-year" style="display: block; margin-bottom: 4px; font-weight: 600;">
							<?php esc_html_e( 'Year', 'csf-parts' ); ?>
						</label>
						<select
							name="csf_year"
							id="<?php echo esc_attr( $block_id ); ?>-year"
							class="csf-select"
							style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;"
						>
							<option value=""><?php esc_html_e( 'Select Year', 'csf-parts' ); ?></option>
							<?php foreach ( $years as $year ) : ?>
								<option value="<?php echo esc_attr( $year ); ?>" <?php selected( $selected_year, $year ); ?>>
									<?php echo esc_html( $year ); ?>
								</option>
							<?php endforeach; ?>
						</select>
					</div>
				<?php endif; ?>

				<?php if ( $show_make_filter && ! empty( $makes ) ) : ?>
					<div class="csf-filter-group" style="flex: 1; min-width: 150px;">
						<label for="<?php echo esc_attr( $block_id ); ?>-make" style="display: block; margin-bottom: 4px; font-weight: 600;">
							<?php esc_html_e( 'Make', 'csf-parts' ); ?>
						</label>
						<select
							name="csf_make"
							id="<?php echo esc_attr( $block_id ); ?>-make"
							class="csf-select"
							style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;"
						>
							<option value=""><?php esc_html_e( 'Select Make', 'csf-parts' ); ?></option>
							<?php foreach ( $makes as $make ) : ?>
								<option value="<?php echo esc_attr( $make ); ?>" <?php selected( $selected_make, $make ); ?>>
									<?php echo esc_html( $make ); ?>
								</option>
							<?php endforeach; ?>
						</select>
					</div>
				<?php endif; ?>

				<?php if ( $show_model_filter && ! empty( $models ) ) : ?>
					<div class="csf-filter-group" style="flex: 1; min-width: 150px;">
						<label for="<?php echo esc_attr( $block_id ); ?>-model" style="display: block; margin-bottom: 4px; font-weight: 600;">
							<?php esc_html_e( 'Model', 'csf-parts' ); ?>
						</label>
						<select
							name="csf_model"
							id="<?php echo esc_attr( $block_id ); ?>-model"
							class="csf-select"
							style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;"
						>
							<option value=""><?php esc_html_e( 'Select Model', 'csf-parts' ); ?></option>
							<?php foreach ( $models as $model ) : ?>
								<option value="<?php echo esc_attr( $model ); ?>" <?php selected( $selected_model, $model ); ?>>
									<?php echo esc_html( $model ); ?>
								</option>
							<?php endforeach; ?>
						</select>
					</div>
				<?php endif; ?>

				<?php if ( $show_category_filter && ! empty( $categories ) ) : ?>
					<div class="csf-filter-group" style="flex: 1; min-width: 150px;">
						<label for="<?php echo esc_attr( $block_id ); ?>-category" style="display: block; margin-bottom: 4px; font-weight: 600;">
							<?php esc_html_e( 'Category', 'csf-parts' ); ?>
						</label>
						<select
							name="csf_category"
							id="<?php echo esc_attr( $block_id ); ?>-category"
							class="csf-select"
							style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;"
						>
							<option value=""><?php esc_html_e( 'Select Category', 'csf-parts' ); ?></option>
							<?php foreach ( $categories as $category ) : ?>
								<option value="<?php echo esc_attr( $category ); ?>" <?php selected( $selected_category, $category ); ?>>
									<?php echo esc_html( $category ); ?>
								</option>
							<?php endforeach; ?>
						</select>
					</div>
				<?php endif; ?>

				<div class="csf-filter-submit">
					<button
						type="submit"
						class="csf-btn csf-btn-primary"
						style="padding: 8px 24px; background: #0073aa; color: #fff; border: none; border-radius: 4px; font-size: 14px; font-weight: 600; cursor: pointer;"
					>
						<?php echo esc_html( $button_text ); ?>
					</button>
				</div>
			</div>
		</form>
	<?php endif; ?>

	<div class="csf-catalog-results">
		<?php if ( ! empty( $parts ) ) : ?>
			<div class="csf-results-header" style="margin-bottom: 16px;">
				<h3 style="margin: 0; font-size: 18px;">
					<?php
					echo esc_html(
						sprintf(
							/* translators: %d: number of parts */
							_n( '%d Part Found', '%d Parts Found', $total_parts, 'csf-parts' ),
							$total_parts
						)
					);
					?>
				</h3>
			</div>

			<div class="csf-grid-items">
				<?php foreach ( $parts as $part ) : ?>
					<?php
					// Generate part URL.
					$part_url = $get_part_url( $part->category, $part->sku );

					// Get display title (fallback to category-SKU if name is empty).
					$display_title = ! empty( $part->name ) ? $part->name : $part->category . ' - ' . $part->sku;

					// Get primary image.
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
				<?php endforeach; ?>
			</div>
		<?php elseif ( $show_filters && ( $selected_year || $selected_make || $selected_model || $selected_category ) ) : ?>
			<div class="csf-no-results" style="padding: 24px; text-align: center; background: #f9f9f9; border-radius: 4px;">
				<p style="margin: 0;"><?php esc_html_e( 'No parts found matching your selection. Please try different filters.', 'csf-parts' ); ?></p>
			</div>
		<?php else : ?>
			<div class="csf-placeholder" style="padding: 48px 24px; text-align: center; background: #f9f9f9; border-radius: 4px;">
				<p style="margin: 0; font-size: 16px; color: #757575;">
					<?php
					if ( $show_filters ) {
						esc_html_e( 'Select filters to find parts.', 'csf-parts' );
					} else {
						esc_html_e( 'No parts match the configured filters.', 'csf-parts' );
					}
					?>
				</p>
			</div>
		<?php endif; ?>

		<?php
		// Pagination (only show if there are results and pagination is enabled).
		if ( ! empty( $parts ) && 'none' !== $pagination_type && $total_pages > 1 ) :
			// Helper function to build pagination URL.
			$get_page_url = function( $page ) use ( $selected_year, $selected_make, $selected_model, $selected_category ) {
				$params = array();
				if ( $selected_year ) {
					$params['csf_year'] = $selected_year;
				}
				if ( $selected_make ) {
					$params['csf_make'] = $selected_make;
				}
				if ( $selected_model ) {
					$params['csf_model'] = $selected_model;
				}
				if ( $selected_category ) {
					$params['csf_category'] = $selected_category;
				}
				$params['csf_page'] = $page;
				return add_query_arg( $params, get_permalink() );
			};
			?>

			<?php if ( 'numbered' === $pagination_type ) : ?>
				<!-- Numbered Pagination -->
				<div class="csf-pagination" style="margin-top: 32px; display: flex; justify-content: center; gap: 8px; flex-wrap: wrap;">
					<?php if ( $current_page > 1 ) : ?>
						<a
							href="<?php echo esc_url( $get_page_url( $current_page - 1 ) ); ?>"
							class="csf-pagination-btn csf-pagination-prev"
							style="padding: 8px 16px; background: #0073aa; color: #fff; text-decoration: none; border-radius: 4px; font-size: 14px;"
						>
							<?php esc_html_e( '← Previous', 'csf-parts' ); ?>
						</a>
					<?php endif; ?>

					<?php
					// Show page numbers (with ellipsis for large ranges).
					$range = 2; // Show 2 pages before and after current.
					$start = max( 1, $current_page - $range );
					$end   = min( $total_pages, $current_page + $range );

					// Always show first page.
					if ( $start > 1 ) :
						?>
						<a
							href="<?php echo esc_url( $get_page_url( 1 ) ); ?>"
							class="csf-pagination-btn"
							style="padding: 8px 12px; background: #f0f0f0; color: #333; text-decoration: none; border-radius: 4px; font-size: 14px;"
						>
							1
						</a>
						<?php if ( $start > 2 ) : ?>
							<span style="padding: 8px 4px; color: #757575;">...</span>
						<?php endif; ?>
					<?php endif; ?>

					<?php for ( $i = $start; $i <= $end; $i++ ) : ?>
						<?php if ( $i === $current_page ) : ?>
							<span
								class="csf-pagination-btn csf-pagination-current"
								style="padding: 8px 12px; background: #0073aa; color: #fff; border-radius: 4px; font-size: 14px; font-weight: 600;"
							>
								<?php echo esc_html( $i ); ?>
							</span>
						<?php else : ?>
							<a
								href="<?php echo esc_url( $get_page_url( $i ) ); ?>"
								class="csf-pagination-btn"
								style="padding: 8px 12px; background: #f0f0f0; color: #333; text-decoration: none; border-radius: 4px; font-size: 14px;"
							>
								<?php echo esc_html( $i ); ?>
							</a>
						<?php endif; ?>
					<?php endfor; ?>

					<?php
					// Always show last page.
					if ( $end < $total_pages ) :
						?>
						<?php if ( $end < $total_pages - 1 ) : ?>
							<span style="padding: 8px 4px; color: #757575;">...</span>
						<?php endif; ?>
						<a
							href="<?php echo esc_url( $get_page_url( $total_pages ) ); ?>"
							class="csf-pagination-btn"
							style="padding: 8px 12px; background: #f0f0f0; color: #333; text-decoration: none; border-radius: 4px; font-size: 14px;"
						>
							<?php echo esc_html( $total_pages ); ?>
						</a>
					<?php endif; ?>

					<?php if ( $current_page < $total_pages ) : ?>
						<a
							href="<?php echo esc_url( $get_page_url( $current_page + 1 ) ); ?>"
							class="csf-pagination-btn csf-pagination-next"
							style="padding: 8px 16px; background: #0073aa; color: #fff; text-decoration: none; border-radius: 4px; font-size: 14px;"
						>
							<?php esc_html_e( 'Next →', 'csf-parts' ); ?>
						</a>
					<?php endif; ?>
				</div>

			<?php elseif ( 'loadmore' === $pagination_type ) : ?>
				<!-- Load More Button -->
				<?php if ( $current_page < $total_pages ) : ?>
					<div class="csf-pagination csf-load-more" style="margin-top: 32px; text-align: center;">
						<button
							class="csf-load-more-btn"
							data-block-id="<?php echo esc_attr( $block_id ); ?>"
							data-next-page="<?php echo esc_attr( $current_page + 1 ); ?>"
							data-total-pages="<?php echo esc_attr( $total_pages ); ?>"
							style="padding: 12px 32px; background: #0073aa; color: #fff; border: none; border-radius: 4px; font-size: 14px; font-weight: 600; cursor: pointer;"
						>
							<?php
							echo esc_html(
								sprintf(
									/* translators: %d: number of remaining pages */
									_n( 'Load More (%d page remaining)', 'Load More (%d pages remaining)', $total_pages - $current_page, 'csf-parts' ),
									$total_pages - $current_page
								)
							);
							?>
						</button>
					</div>
				<?php endif; ?>

			<?php elseif ( 'endless' === $pagination_type ) : ?>
				<!-- Endless Scroll Trigger -->
				<?php if ( $current_page < $total_pages ) : ?>
					<div
						class="csf-endless-trigger"
						data-block-id="<?php echo esc_attr( $block_id ); ?>"
						data-next-page="<?php echo esc_attr( $current_page + 1 ); ?>"
						data-total-pages="<?php echo esc_attr( $total_pages ); ?>"
						style="margin-top: 32px; text-align: center; padding: 24px;"
					>
						<span class="csf-loading-indicator" style="display: none; color: #757575;">
							<?php esc_html_e( 'Loading more parts...', 'csf-parts' ); ?>
						</span>
					</div>
				<?php endif; ?>

			<?php endif; ?>
		<?php endif; ?>
	</div>
</div>
