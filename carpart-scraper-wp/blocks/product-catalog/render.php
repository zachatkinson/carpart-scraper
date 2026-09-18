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
$show_sort_control    = $attributes['showSortControl'] ?? true;
$card_options         = CSF_Parts_Part_Card::sanitize_options(
	array(
		'new_badge_days'    => $attributes['newBadgeDays'] ?? 30,
		'show_fitment_line' => $attributes['showFitmentLine'] ?? true,
		'show_meta_line'    => $attributes['showMetaLine'] ?? true,
	)
);
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

$order_by            = $attributes['orderBy'] ?? 'updated_at';
$order_direction     = $attributes['orderDirection'] ?? 'desc';

// Visitor sort (csf_sort) overrides the block default when valid.
$sort_key = isset( $_GET[ CSF_Parts_Catalog_Sort::PARAM ] ) ? sanitize_key( wp_unslash( $_GET[ CSF_Parts_Catalog_Sort::PARAM ] ) ) : '';
$sort_key = CSF_Parts_Catalog_Sort::is_valid( $sort_key ) ? $sort_key : CSF_Parts_Catalog_Sort::key_for( $order_by, $order_direction );
if ( '' !== $sort_key ) {
	$resolved        = CSF_Parts_Catalog_Sort::resolve( $sort_key );
	$order_by        = $resolved['orderby'];
	$order_direction = $resolved['order'];
}
$button_text         = $attributes['buttonText'] ?? 'Find Parts';
$enable_ajax         = $attributes['enableAjax'] ?? true;
$pagination_type     = $attributes['paginationType'] ?? 'numbered';
// Card styling, aspect ratio, hover, animation, visibility and colour scheme are
// resolved by CSF_Parts_Block_Styles into wrapper custom properties/classes and
// a small per-instance stylesheet (see the wrapper below).

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
$selected_type     = '';
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
	// Part-type line (csf_type) expands to its raw categories; csf_category still works for direct links.
	$selected_type = isset( $_GET[ CSF_Parts_Part_Types::PARAM ] ) ? sanitize_key( wp_unslash( $_GET[ CSF_Parts_Part_Types::PARAM ] ) ) : '';
	$selected_type = CSF_Parts_Part_Types::is_valid( $selected_type ) ? $selected_type : '';
	if ( '' !== $selected_type ) {
		$filters['categories'] = CSF_Parts_Part_Types::categories_for_line( $selected_type, $database->get_all_categories() );
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
		$categories = $database->get_category_counts(); // category => count
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
			'partsLabel'     => __( 'parts', 'csf-parts' ),
			'partLabel'      => __( 'part', 'csf-parts' ),
			'showingLabel'   => __( 'showing', 'csf-parts' ),
			'toLabel'        => __( 'to', 'csf-parts' ),
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

?>
<?php
// Per-instance CSS: only the responsive grid and image aspect ratio vary per block.
echo '<style>' . CSF_Parts_Block_Styles::instance_css( $block_id, $attributes ) . '</style>';

// Get block wrapper attributes (includes alignment classes like alignfull, alignwide).
$wrapper_style   = CSF_Parts_Block_Styles::card_style_vars( $attributes ) . CSF_Parts_Block_Styles::legacy_spacing_style( $attributes );
$wrapper_classes = trim( 'csf-product-catalog ' . CSF_Parts_Block_Styles::wrapper_classes( $attributes ) );

$wrapper_attributes = get_block_wrapper_attributes(
	array(
		'class'                   => $wrapper_classes,
		'style'                   => $wrapper_style,
		'id'                      => $block_id,
		'data-ajax'               => $enable_ajax ? '1' : '0',
		'data-pagination-type'    => $pagination_type,
		'data-per-page'           => $per_page,
		'data-order-by'           => $order_by,
		'data-order-direction'    => $order_direction,
		'data-card-options'       => wp_json_encode( $card_options ),
		'data-columns-desktop'    => $columns['desktop'],
		'data-default-categories' => ! empty( $default_categories ) ? esc_attr( wp_json_encode( $default_categories ) ) : '',
	)
);
?>
<div <?php echo $wrapper_attributes; ?>>
	<?php if ( $show_filters ) : ?>
		<form class="csf-catalog-filters csf-filter-form csf-filter-card" id="<?php echo esc_attr( $block_id ); ?>-form" method="get" action="">
			<div class="csf-filter-controls">
				<!-- Search Box -->
				<div class="csf-filter-group csf-filter-group--search csf-search-box">
					<label for="<?php echo esc_attr( $block_id ); ?>-search" class="csf-filter-group__label">
						<?php esc_html_e( 'Part number', 'csf-parts' ); ?>
						<span class="csf-filter-group__hint"><?php esc_html_e( 'CSF, OEM or Partslink', 'csf-parts' ); ?></span>
					</label>
					<div class="csf-search-box__field">
						<input
							type="search"
							name="csf_search"
							id="<?php echo esc_attr( $block_id ); ?>-search"
							class="csf-search-box__input"
							placeholder="<?php esc_attr_e( 'Type a number, results update as you go', 'csf-parts' ); ?>"
							autocomplete="off"
							value="<?php echo esc_attr( isset( $_GET['csf_search'] ) ? sanitize_text_field( wp_unslash( $_GET['csf_search'] ) ) : '' ); ?>"
						/>
						<svg class="csf-search-box__icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
					</div>
				</div>

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

				<div class="csf-filter-submit">
					<button type="button" class="csf-btn-link csf-btn-reset"><?php esc_html_e( 'Clear', 'csf-parts' ); ?></button>
				</div>
			</div>

			<?php $type_chips = $show_category_filter ? CSF_Parts_Part_Types::chips( $categories ) : array(); ?>
			<?php if ( ! empty( $type_chips ) ) : ?>
				<?php $chip_base = remove_query_arg( array( CSF_Parts_Part_Types::PARAM, 'csf_category', 'csf_page' ) ); ?>
				<div class="csf-part-types">
					<span class="csf-part-types__label"><?php esc_html_e( 'Part type', 'csf-parts' ); ?></span>
					<div class="csf-part-types__chips" role="group" aria-label="<?php esc_attr_e( 'Part type', 'csf-parts' ); ?>">
						<a href="<?php echo esc_url( $chip_base ); ?>" class="csf-chip<?php echo '' === $selected_type ? ' is-active' : ''; ?>" data-type="" <?php echo '' === $selected_type ? 'aria-current="true"' : ''; ?>>
							<?php esc_html_e( 'All', 'csf-parts' ); ?> <span class="csf-chip__count"><?php echo esc_html( number_format_i18n( array_sum( $categories ) ) ); ?></span>
						</a>
						<?php foreach ( $type_chips as $type_slug => $chip ) : ?>
							<a href="<?php echo esc_url( add_query_arg( CSF_Parts_Part_Types::PARAM, $type_slug, $chip_base ) ); ?>" class="csf-chip<?php echo $selected_type === $type_slug ? ' is-active' : ''; ?>" data-type="<?php echo esc_attr( $type_slug ); ?>" <?php echo $selected_type === $type_slug ? 'aria-current="true"' : ''; ?>>
								<?php echo esc_html( $chip['label'] ); ?> <span class="csf-chip__count"><?php echo esc_html( number_format_i18n( $chip['count'] ) ); ?></span>
							</a>
						<?php endforeach; ?>
					</div>
					<input type="hidden" name="<?php echo esc_attr( CSF_Parts_Part_Types::PARAM ); ?>" value="<?php echo esc_attr( $selected_type ); ?>" />
				</div>
			<?php endif; ?>
		</form>
	<?php endif; ?>

	<div class="csf-catalog-results">
		<?php if ( ! empty( $parts ) ) : ?>
			<?php if ( $show_results_count || ( $show_sort_control && $show_filters ) ) : ?>
				<?php
				$showing_from = ( $current_page - 1 ) * $per_page + 1;
				$showing_to   = min( $total_parts, $current_page * $per_page );
				?>
				<div class="csf-results-header">
					<?php if ( $show_results_count ) : ?>
						<p class="csf-results-header__title" data-from="<?php echo esc_attr( (string) $showing_from ); ?>" data-to="<?php echo esc_attr( (string) $showing_to ); ?>">
							<strong><?php echo esc_html( number_format_i18n( $total_parts ) . ' ' . _n( 'part', 'parts', $total_parts, 'csf-parts' ) ); ?></strong>
							<span class="csf-results-header__range">· <?php echo esc_html( sprintf( /* translators: 1: first index, 2: last index */ __( 'showing %1$s to %2$s', 'csf-parts' ), number_format_i18n( $showing_from ), number_format_i18n( $showing_to ) ) ); ?></span>
						</p>
					<?php endif; ?>
					<?php if ( $show_sort_control && $show_filters ) : ?>
						<label class="csf-sort">
							<span class="csf-sort__label"><?php esc_html_e( 'Sort', 'csf-parts' ); ?></span>
							<select name="<?php echo esc_attr( CSF_Parts_Catalog_Sort::PARAM ); ?>" class="csf-select csf-sort__select" form="<?php echo esc_attr( $block_id ); ?>-form">
								<?php foreach ( CSF_Parts_Catalog_Sort::options() as $key => $option ) : ?>
									<option value="<?php echo esc_attr( $key ); ?>" data-orderby="<?php echo esc_attr( $option['orderby'] ); ?>" data-order="<?php echo esc_attr( $option['order'] ); ?>" <?php selected( $sort_key, $key ); ?>><?php echo esc_html( $option['label'] ); ?></option>
								<?php endforeach; ?>
							</select>
						</label>
					<?php endif; ?>
				</div>
			<?php endif; ?>

			<div class="csf-grid-items">
				<?php foreach ( $parts as $part ) : ?>
					<?php
					// Generate part URL.
					$part_url = $get_part_url( $part->category, $part->sku );

					echo CSF_Parts_Part_Card::render( $part, $part_url, $card_options ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Escaped in the renderer.
					?>
				<?php endforeach; ?>
			</div>
		<?php elseif ( $show_filters && ( $selected_year || $selected_make || $selected_model || $selected_category ) ) : ?>
			<div class="csf-no-results">
				<p class="csf-no-results__text"><?php esc_html_e( 'No parts found matching your selection. Please try different filters.', 'csf-parts' ); ?></p>
			</div>
		<?php else : ?>
			<div class="csf-placeholder">
				<p class="csf-placeholder__text">
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
				<div class="csf-pagination">
					<?php if ( $current_page > 1 ) : ?>
						<a
							href="<?php echo esc_url( $get_page_url( $current_page - 1 ) ); ?>"
							class="csf-pagination-btn csf-pagination-prev"
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
						>
							1
						</a>
						<?php if ( $start > 2 ) : ?>
							<span class="csf-pagination-ellipsis">...</span>
						<?php endif; ?>
					<?php endif; ?>

					<?php for ( $i = $start; $i <= $end; $i++ ) : ?>
						<?php if ( $i === $current_page ) : ?>
							<span
								class="csf-pagination-btn csf-pagination-current"
							>
								<?php echo esc_html( $i ); ?>
							</span>
						<?php else : ?>
							<a
								href="<?php echo esc_url( $get_page_url( $i ) ); ?>"
								class="csf-pagination-btn"
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
							<span class="csf-pagination-ellipsis">...</span>
						<?php endif; ?>
						<a
							href="<?php echo esc_url( $get_page_url( $total_pages ) ); ?>"
							class="csf-pagination-btn"
						>
							<?php echo esc_html( $total_pages ); ?>
						</a>
					<?php endif; ?>

					<?php if ( $current_page < $total_pages ) : ?>
						<a
							href="<?php echo esc_url( $get_page_url( $current_page + 1 ) ); ?>"
							class="csf-pagination-btn csf-pagination-next"
						>
							<?php esc_html_e( 'Next →', 'csf-parts' ); ?>
						</a>
					<?php endif; ?>
				</div>

			<?php elseif ( 'loadmore' === $pagination_type ) : ?>
				<!-- Load More Button -->
				<?php if ( $current_page < $total_pages ) : ?>
					<div class="csf-pagination csf-load-more">
						<button
							class="csf-load-more-btn"
							data-block-id="<?php echo esc_attr( $block_id ); ?>"
							data-next-page="<?php echo esc_attr( $current_page + 1 ); ?>"
							data-total-pages="<?php echo esc_attr( $total_pages ); ?>"
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
					>
						<span class="csf-loading-indicator">
							<?php esc_html_e( 'Loading more parts...', 'csf-parts' ); ?>
						</span>
					</div>
				<?php endif; ?>

			<?php endif; ?>
		<?php endif; ?>
	</div>
</div>
