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
$show_results_count   = $attributes['showResultsCount'] ?? true;
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

$order_by            = $attributes['orderBy'] ?? 'name';
$order_direction     = $attributes['orderDirection'] ?? 'asc';
$button_text         = $attributes['buttonText'] ?? 'Find Parts';
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
$search_query      = '';

if ( $show_filters ) {
	if ( isset( $_GET['csf_search'] ) && ! empty( $_GET['csf_search'] ) ) {
		$search_query         = sanitize_text_field( wp_unslash( $_GET['csf_search'] ) );
		$filters['search']    = $search_query;
	}
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

// Pass sort options.
$filters['orderby'] = $order_by;
$filters['order']   = $order_direction;

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
		$years_data = $database->get_vehicle_years();
		$years = array_map( function( $item ) { return $item->year; }, $years_data );
	}
	if ( $show_make_filter ) {
		$makes_data = $database->get_vehicle_makes();
		$makes = array_map( function( $item ) { return $item->make; }, $makes_data );
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
			'loadMoreSingle'  => 'Load More (%d page remaining)',
			'loadMorePlural'  => 'Load More (%d pages remaining)',
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
			'ajaxUrl'        => admin_url( 'admin-ajax.php' ),
			'nonce'          => wp_create_nonce( 'csf_parts_filter' ),
			'selectMake'     => 'Select Make',
			'selectModel'    => 'Select Model',
			'loading'        => 'Loading...',
			'loadingResults' => 'Loading results...',
			'noMakes'        => 'No makes available',
			'noModels'       => 'No models available',
			'error'          => 'Error loading options',
			'resultSingular' => 'Part Found',
			'resultPlural'   => 'Parts Found',
		)
	);
}

// Helper function to generate part URL (V2 format: /parts/csf{sku}).
$get_part_url = function( $category, $sku ) use ( $selected_year, $selected_make, $selected_model ) {
	// Use shared helper for base URL generation.
	$base_url = csf_get_part_url( $sku );

	// Preserve filter parameters for vehicle highlighting on part page
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

// Helper function to get primary image from JSON.
$get_primary_image = function( $images_json ) {
	if ( empty( $images_json ) ) {
		return null;
	}

	$images = json_decode( $images_json, true );
	if ( ! is_array( $images ) || empty( $images ) ) {
		return null;
	}

	// Prefer second image (product photo) if available, otherwise use first (technical drawing).
	$image_index = isset( $images[1] ) ? 1 : 0;
	$image = $images[ $image_index ];

	$raw_url = null;
	if ( is_string( $image ) ) {
		$raw_url = $image;
	} elseif ( is_array( $image ) && isset( $image['url'] ) ) {
		$raw_url = $image['url'];
	}

	return $raw_url ? csf_resolve_image_url( $raw_url ) : null;
};

// Helper function to extract dimensions from specifications.
$get_dimensions = function( $specifications_json ) {
	if ( empty( $specifications_json ) ) {
		return null;
	}

	$specs = json_decode( $specifications_json, true );
	if ( ! is_array( $specs ) || empty( $specs ) ) {
		return null;
	}

	$length = $specs['Core Length (in)'] ?? null;
	$width  = $specs['Core Width (in)'] ?? null;
	$height = $specs['Core Thickness (in)'] ?? null;

	if ( ! $length || ! $width || ! $height ) {
		return null;
	}

	// Strip " (in)" from values since we add " in the format string
	$length = str_replace( ' (in)', '', $length );
	$width  = str_replace( ' (in)', '', $width );
	$height = str_replace( ' (in)', '', $height );

	// Convert fractions to HTML entities using shared helper function.
	$length = csf_format_dimension_fractions( $length );
	$width  = csf_format_dimension_fractions( $width );
	$height = csf_format_dimension_fractions( $height );

	// Format: L × W × H.
	return sprintf( '%s" × %s" × %s"', $length, $width, $height );
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
			return 'background: var(--global-palette2, #0099CC); color: var(--global-palette3, #0A0A0A);';
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

// Pagination hover styles.
$comprehensive_css .= sprintf(
	'
	/* Pagination button base styles with transition */
	#%1$s .csf-pagination-btn {
		transition: all 0.3s ease;
	}

	/* Pagination hover - all buttons except current page */
	#%1$s .csf-pagination-btn:not(.csf-pagination-current):hover {
		background: var(--global-palette10, #E7E5E4) !important;
		color: var(--global-palette9, #FAFAF9) !important;
	}

	/* Current page - no background change on hover, just add subtle shadow */
	#%1$s .csf-pagination-current:hover {
		background: transparent !important;
		color: var(--global-palette1, #C41C10) !important;
		border-color: var(--global-palette1, #C41C10) !important;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
	}
	',
	esc_attr( $block_id )
);

// Output CSS.
echo '<style>' . $comprehensive_css . '</style>';

// Get block wrapper attributes (includes alignment classes like alignfull, alignwide).
$wrapper_attributes = get_block_wrapper_attributes(
	array(
		'class'                   => 'csf-product-catalog',
		'id'                      => $block_id,
		'data-ajax'               => $enable_ajax ? '1' : '0',
		'data-pagination-type'    => $pagination_type,
		'data-per-page'           => $per_page,
		'data-columns-desktop'    => $columns['desktop'],
		'data-default-categories' => ! empty( $default_categories ) ? esc_attr( wp_json_encode( $default_categories ) ) : '',
	)
);
?>
<div <?php echo $wrapper_attributes; ?>>
	<?php if ( $show_filters ) : ?>
		<form class="csf-catalog-filters csf-filter-form" method="get" action="">
			<!-- Search Box -->
			<div class="csf-search-box">
				<label for="<?php echo esc_attr( $block_id ); ?>-search" class="csf-search-box__label">
					<?php esc_html_e( 'Search by Part Number or OEM', 'csf-parts' ); ?>
				</label>
				<input
					type="text"
					name="csf_search"
					id="<?php echo esc_attr( $block_id ); ?>-search"
					class="csf-search-box__input"
					placeholder="<?php esc_attr_e( 'Enter SKU, OEM, or Partslink number...', 'csf-parts' ); ?>"
					value="<?php echo esc_attr( isset( $_GET['csf_search'] ) ? sanitize_text_field( wp_unslash( $_GET['csf_search'] ) ) : '' ); ?>"
				/>
				<p class="csf-search-box__help-text">
					<?php esc_html_e( 'Search for parts by CSF part number, OEM number, or Partslink number. Results update automatically as you type.', 'csf-parts' ); ?>
				</p>
			</div>

			<div class="csf-filter-controls">
				<?php if ( $show_year_filter && ! empty( $years ) ) : ?>
					<?php
					// Use helper function for consistent dropdown rendering.
					echo csf_render_select(
						array(
							'id'          => $block_id . '-year',
							'name'        => 'csf_year',
							'options'     => array_combine( $years, $years ),
							'selected'    => $selected_year,
							'label'       => __( 'Year', 'csf-parts' ),
							'placeholder' => __( 'Select Year', 'csf-parts' ),
						)
					);
					?>
				<?php endif; ?>

				<?php if ( $show_make_filter && ! empty( $makes ) ) : ?>
					<?php
					// Use helper function for consistent dropdown rendering.
					echo csf_render_select(
						array(
							'id'          => $block_id . '-make',
							'name'        => 'csf_make',
							'options'     => array_combine( $makes, $makes ),
							'selected'    => $selected_make,
							'label'       => __( 'Make', 'csf-parts' ),
							'placeholder' => __( 'Select Make', 'csf-parts' ),
						)
					);
					?>
				<?php endif; ?>

				<?php if ( $show_model_filter && ! empty( $models ) ) : ?>
					<?php
					// Use helper function for consistent dropdown rendering.
					echo csf_render_select(
						array(
							'id'          => $block_id . '-model',
							'name'        => 'csf_model',
							'options'     => array_combine( $models, $models ),
							'selected'    => $selected_model,
							'label'       => __( 'Model', 'csf-parts' ),
							'placeholder' => __( 'Select Model', 'csf-parts' ),
						)
					);
					?>
				<?php endif; ?>

				<?php if ( $show_category_filter && ! empty( $categories ) ) : ?>
					<?php
					// Use helper function for consistent dropdown rendering.
					echo csf_render_select(
						array(
							'id'          => $block_id . '-category',
							'name'        => 'csf_category',
							'options'     => array_combine( $categories, $categories ),
							'selected'    => $selected_category,
							'label'       => __( 'Category', 'csf-parts' ),
							'placeholder' => __( 'Select Category', 'csf-parts' ),
						)
					);
					?>
				<?php endif; ?>

				<div class="csf-filter-submit">
					<button
						type="button"
						class="csf-btn csf-btn-reset"
					>
						<?php esc_html_e( 'Reset Filters', 'csf-parts' ); ?>
					</button>
				</div>
			</div>
		</form>
	<?php endif; ?>

	<div class="csf-catalog-results">
		<?php if ( ! empty( $parts ) ) : ?>
			<?php if ( $show_results_count ) : ?>
				<div class="csf-results-header" style="margin-bottom: 16px;">
					<h3 class="csf-results-header__title">
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
			<?php endif; ?>

			<div class="csf-grid-items">
				<?php foreach ( $parts as $part ) : ?>
					<?php
					// Generate part URL.
					$part_url = $get_part_url( $part->category, $part->sku );

					// Display title: Use shared helper for consistent formatting.
					$display_title = csf_format_sku_display( $part->sku );

					// Get primary image.
					$primary_image = $get_primary_image( $part->images );
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
								<?php
								// Display dimensions if available.
								$dimensions = $get_dimensions( $part->specifications );
								if ( ! empty( $dimensions ) ) :
								?>
									<div class="csf-dimensions-section">
										<p class="csf-dimensions-section__label"><?php esc_html_e( 'Dimensions', 'csf-parts' ); ?></p>
										<p class="csf-dimensions-section__value"><?php echo wp_kses( $dimensions, array( 'sup' => array(), 'sub' => array() ) ); ?></p>
									</div>
								<?php endif; ?>
								<?php
								// Display fitment section with make badges if compatibility data exists.
								$compatibility_data = ! empty( $part->compatibility ) ? json_decode( $part->compatibility, true ) : array();
								$part_makes = array();
								if ( is_array( $compatibility_data ) ) {
									foreach ( $compatibility_data as $vehicle ) {
										if ( isset( $vehicle['make'] ) && ! in_array( $vehicle['make'], $part_makes, true ) ) {
											$part_makes[] = $vehicle['make'];
										}
									}
								}
								if ( ! empty( $part_makes ) ) :
								?>
									<div class="csf-fitment-section">
										<p class="csf-fitment-section__label"><?php esc_html_e( 'Fits Models By', 'csf-parts' ); ?></p>
										<div class="csf-part-card__makes">
											<?php
											$max_badges = 4;
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
							style="padding: 8px 16px; background: var(--global-palette2, #0099CC); color: var(--global-palette9, #FAFAF9); text-decoration: none; border-radius: 4px; font-size: 14px; transition: all 0.3s ease;"
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
							style="padding: 8px 12px; background: var(--global-palette2, #0099CC); color: var(--global-palette9, #FAFAF9); text-decoration: none; border-radius: 4px; font-size: 14px; transition: all 0.3s ease;"
						>
							1
						</a>
						<?php if ( $start > 2 ) : ?>
							<span style="padding: 8px 4px; color: var(--global-palette3, #5A5A5A);">...</span>
						<?php endif; ?>
					<?php endif; ?>

					<?php for ( $i = $start; $i <= $end; $i++ ) : ?>
						<?php if ( $i === $current_page ) : ?>
							<span
								class="csf-pagination-btn csf-pagination-current"
								style="padding: 8px 12px; background: transparent; color: var(--global-palette2, #0099CC); border: 2px solid var(--global-palette2, #0099CC); border-radius: 4px; font-size: 14px; font-weight: 600; transition: all 0.3s ease;"
							>
								<?php echo esc_html( $i ); ?>
							</span>
						<?php else : ?>
							<a
								href="<?php echo esc_url( $get_page_url( $i ) ); ?>"
								class="csf-pagination-btn"
								style="padding: 8px 12px; background: var(--global-palette2, #0099CC); color: var(--global-palette9, #FAFAF9); text-decoration: none; border-radius: 4px; font-size: 14px; transition: all 0.3s ease;"
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
							<span style="padding: 8px 4px; color: var(--global-palette3, #5A5A5A);">...</span>
						<?php endif; ?>
						<a
							href="<?php echo esc_url( $get_page_url( $total_pages ) ); ?>"
							class="csf-pagination-btn"
							style="padding: 8px 12px; background: var(--global-palette2, #0099CC); color: var(--global-palette9, #FAFAF9); text-decoration: none; border-radius: 4px; font-size: 14px; transition: all 0.3s ease;"
						>
							<?php echo esc_html( $total_pages ); ?>
						</a>
					<?php endif; ?>

					<?php if ( $current_page < $total_pages ) : ?>
						<a
							href="<?php echo esc_url( $get_page_url( $current_page + 1 ) ); ?>"
							class="csf-pagination-btn csf-pagination-next"
							style="padding: 8px 16px; background: var(--global-palette2, #0099CC); color: var(--global-palette9, #FAFAF9); text-decoration: none; border-radius: 4px; font-size: 14px; transition: all 0.3s ease;"
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
							class="csf-search-box__button"
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
