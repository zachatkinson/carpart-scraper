<?php
/**
 * Server-side render for Vehicle Selector block.
 *
 * @package CSF_Parts_Catalog
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

$show_year        = $attributes['showYear'] ?? true;
$show_make        = $attributes['showMake'] ?? true;
$show_model       = $attributes['showModel'] ?? true;
$results_per_page = $attributes['resultsPerPage'] ?? 12;
$columns          = $attributes['columns'] ?? 3;
$button_text      = $attributes['buttonText'] ?? __( 'Find Parts', 'csf-parts' );
$enable_ajax      = $attributes['enableAjax'] ?? true;

// Get unique taxonomy terms for filters
$years  = array();
$makes  = array();
$models = array();

if ( $show_year ) {
	$year_terms = get_terms(
		array(
			'taxonomy'   => CSF_Parts_Constants::TAXONOMY_YEAR,
			'hide_empty' => true,
			'orderby'    => 'name',
			'order'      => 'DESC',
		)
	);
	if ( ! is_wp_error( $year_terms ) ) {
		$years = $year_terms;
	}
}

if ( $show_make ) {
	$make_terms = get_terms(
		array(
			'taxonomy'   => CSF_Parts_Constants::TAXONOMY_MAKE,
			'hide_empty' => true,
			'orderby'    => 'name',
			'order'      => 'ASC',
		)
	);
	if ( ! is_wp_error( $make_terms ) ) {
		$makes = $make_terms;
	}
}

if ( $show_model ) {
	$model_terms = get_terms(
		array(
			'taxonomy'   => CSF_Parts_Constants::TAXONOMY_MODEL,
			'hide_empty' => true,
			'orderby'    => 'name',
			'order'      => 'ASC',
		)
	);
	if ( ! is_wp_error( $model_terms ) ) {
		$models = $model_terms;
	}
}

// Generate unique ID for this instance
$block_id = 'csf-vehicle-selector-' . wp_rand( 1000, 9999 );
?>
<div class="csf-vehicle-selector" id="<?php echo esc_attr( $block_id ); ?>" data-ajax="<?php echo esc_attr( $enable_ajax ? '1' : '0' ); ?>">
	<form class="csf-selector-form" method="get" action="">
		<div class="csf-selector-filters">
			<?php if ( $show_year && ! empty( $years ) ) : ?>
				<div class="csf-filter-group">
					<label for="<?php echo esc_attr( $block_id ); ?>-year">
						<?php esc_html_e( 'Year', 'csf-parts' ); ?>
					</label>
					<select
						name="csf_year"
						id="<?php echo esc_attr( $block_id ); ?>-year"
						class="csf-select csf-year-select"
					>
						<option value=""><?php esc_html_e( 'Select Year', 'csf-parts' ); ?></option>
						<?php foreach ( $years as $year ) : ?>
							<option value="<?php echo esc_attr( $year->slug ); ?>">
								<?php echo esc_html( $year->name ); ?>
							</option>
						<?php endforeach; ?>
					</select>
				</div>
			<?php endif; ?>

			<?php if ( $show_make && ! empty( $makes ) ) : ?>
				<div class="csf-filter-group">
					<label for="<?php echo esc_attr( $block_id ); ?>-make">
						<?php esc_html_e( 'Make', 'csf-parts' ); ?>
					</label>
					<select
						name="csf_make"
						id="<?php echo esc_attr( $block_id ); ?>-make"
						class="csf-select csf-make-select"
						<?php echo $show_year ? 'disabled' : ''; ?>
					>
						<option value=""><?php esc_html_e( 'Select Make', 'csf-parts' ); ?></option>
						<?php foreach ( $makes as $make ) : ?>
							<option value="<?php echo esc_attr( $make->slug ); ?>">
								<?php echo esc_html( $make->name ); ?>
							</option>
						<?php endforeach; ?>
					</select>
				</div>
			<?php endif; ?>

			<?php if ( $show_model && ! empty( $models ) ) : ?>
				<div class="csf-filter-group">
					<label for="<?php echo esc_attr( $block_id ); ?>-model">
						<?php esc_html_e( 'Model', 'csf-parts' ); ?>
					</label>
					<select
						name="csf_model"
						id="<?php echo esc_attr( $block_id ); ?>-model"
						class="csf-select csf-model-select"
						<?php echo $show_make ? 'disabled' : ''; ?>
					>
						<option value=""><?php esc_html_e( 'Select Model', 'csf-parts' ); ?></option>
						<?php foreach ( $models as $model ) : ?>
							<option value="<?php echo esc_attr( $model->slug ); ?>">
								<?php echo esc_html( $model->name ); ?>
							</option>
						<?php endforeach; ?>
					</select>
				</div>
			<?php endif; ?>

			<div class="csf-filter-group csf-filter-submit">
				<button type="submit" class="csf-btn csf-btn-primary">
					<?php echo esc_html( $button_text ); ?>
				</button>
			</div>
		</div>
	</form>

	<div class="csf-selector-results" data-per-page="<?php echo esc_attr( $results_per_page ); ?>" data-columns="<?php echo esc_attr( $columns ); ?>">
		<?php
		// Check if filters are applied via GET params
		$selected_year  = isset( $_GET['csf_year'] ) ? sanitize_text_field( wp_unslash( $_GET['csf_year'] ) ) : '';
		$selected_make  = isset( $_GET['csf_make'] ) ? sanitize_text_field( wp_unslash( $_GET['csf_make'] ) ) : '';
		$selected_model = isset( $_GET['csf_model'] ) ? sanitize_text_field( wp_unslash( $_GET['csf_model'] ) ) : '';

		if ( $selected_year || $selected_make || $selected_model ) :
			// Build query args
			$args = array(
				'post_type'      => CSF_Parts_Constants::POST_TYPE,
				'post_status'    => 'publish',
				'posts_per_page' => $results_per_page,
			);

			$tax_query = array();

			if ( $selected_year ) {
				$tax_query[] = array(
					'taxonomy' => CSF_Parts_Constants::TAXONOMY_YEAR,
					'field'    => 'slug',
					'terms'    => $selected_year,
				);
			}

			if ( $selected_make ) {
				$tax_query[] = array(
					'taxonomy' => CSF_Parts_Constants::TAXONOMY_MAKE,
					'field'    => 'slug',
					'terms'    => $selected_make,
				);
			}

			if ( $selected_model ) {
				$tax_query[] = array(
					'taxonomy' => CSF_Parts_Constants::TAXONOMY_MODEL,
					'field'    => 'slug',
					'terms'    => $selected_model,
				);
			}

			if ( ! empty( $tax_query ) ) {
				$args['tax_query'] = $tax_query;
			}

			$query = new WP_Query( $args );

			if ( $query->have_posts() ) :
				?>
				<div class="csf-results-header">
					<h3><?php echo esc_html( sprintf( _n( '%d Part Found', '%d Parts Found', $query->found_posts, 'csf-parts' ), $query->found_posts ) ); ?></h3>
				</div>

				<div class="csf-grid-items" style="grid-template-columns: repeat(<?php echo esc_attr( $columns ); ?>, 1fr);">
					<?php
					while ( $query->have_posts() ) :
						$query->the_post();
						$post_id = get_the_ID();
						$sku     = get_post_meta( $post_id, CSF_Parts_Constants::META_SKU, true );
						$price   = get_post_meta( $post_id, CSF_Parts_Constants::META_PRICE, true );
						?>
						<div class="csf-grid-item">
							<?php if ( has_post_thumbnail() ) : ?>
								<div class="csf-item-image">
									<a href="<?php the_permalink(); ?>">
										<?php the_post_thumbnail( 'medium' ); ?>
									</a>
								</div>
							<?php endif; ?>
							<div class="csf-item-content">
								<h3 class="csf-item-title">
									<a href="<?php the_permalink(); ?>"><?php the_title(); ?></a>
								</h3>
								<p class="csf-item-sku"><?php echo esc_html( $sku ); ?></p>
								<?php if ( $price ) : ?>
									<p class="csf-item-price">$<?php echo esc_html( number_format( $price, 2 ) ); ?></p>
								<?php endif; ?>
								<a href="<?php the_permalink(); ?>" class="csf-item-link">
									<?php esc_html_e( 'View Details', 'csf-parts' ); ?>
								</a>
							</div>
						</div>
					<?php endwhile; ?>
				</div>

				<?php wp_reset_postdata(); ?>
			<?php else : ?>
				<div class="csf-no-results">
					<p><?php esc_html_e( 'No parts found matching your selection. Please try different filters.', 'csf-parts' ); ?></p>
				</div>
			<?php
			endif;
		else :
			?>
			<div class="csf-placeholder">
				<p><?php esc_html_e( 'Select your vehicle to find compatible parts.', 'csf-parts' ); ?></p>
			</div>
		<?php endif; ?>
	</div>
</div>
