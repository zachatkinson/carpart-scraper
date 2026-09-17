<?php
/**
 * Server-side render for the Part Finder block.
 *
 * A plain GET form pointed at the Parts page, so it works without JavaScript;
 * view.js adds the Year → Make → Model cascade and strips empty fields from
 * the URL. Field names match the query parameters the Product Catalog block
 * reads (csf_search, csf_year, csf_make, csf_model).
 *
 * @package CSF_Parts_Catalog
 * @since   1.11.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

$finder = CSF_Parts_Part_Finder::from_attributes( $attributes );

$database = new CSF_Parts_Database();
$years    = $finder['show_year'] ? CSF_Parts_Part_Finder::option_values( $database->get_vehicle_years(), 'year' ) : array();
$makes    = $finder['show_make'] ? CSF_Parts_Part_Finder::option_values( $database->get_vehicle_makes(), 'make' ) : array();
$count    = $finder['show_footnote'] ? $database->get_total_parts() : 0;
$footnote = $finder['show_footnote'] ? CSF_Parts_Part_Finder::footnote( $finder['footnote_text'], $count ) : '';
$target   = '' !== $finder['target_url'] ? $finder['target_url'] : csf_find_catalog_page_url();
$block_id = wp_unique_id( 'csf-part-finder-' );
$heading  = 'h' . $finder['heading_level'];

// AJAX data for the cascade script (registered by block.json as the view script).
wp_localize_script(
	'csf-parts-part-finder-view-script',
	'csfPartFinder',
	array(
		'ajaxUrl'     => admin_url( 'admin-ajax.php' ),
		'nonce'       => wp_create_nonce( 'csf_parts_filter' ),
		'selectMake'  => __( 'Make', 'csf-parts' ),
		'selectModel' => __( 'Model', 'csf-parts' ),
		'loading'     => __( 'Loading…', 'csf-parts' ),
		'none'        => __( 'None available', 'csf-parts' ),
		'error'       => __( 'Could not load options', 'csf-parts' ),
	)
);

$wrapper_attributes = get_block_wrapper_attributes( array( 'class' => 'csf-part-finder' ) );
?>
<div <?php echo $wrapper_attributes; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Escaped by core. ?>>
	<form class="csf-part-finder__form" method="get" action="<?php echo esc_url( $target ); ?>" data-target="<?php echo esc_url( $target ); ?>">
		<?php if ( '' !== $finder['eyebrow'] ) : ?>
			<p class="csf-part-finder__eyebrow"><?php echo esc_html( $finder['eyebrow'] ); ?></p>
		<?php endif; ?>
		<?php if ( '' !== $finder['heading'] ) : ?>
			<<?php echo esc_attr( $heading ); ?> class="csf-part-finder__heading"><?php echo esc_html( $finder['heading'] ); ?></<?php echo esc_attr( $heading ); ?>>
		<?php endif; ?>

		<?php if ( $finder['show_search'] ) : ?>
			<div class="csf-part-finder__search">
				<label for="<?php echo esc_attr( $block_id ); ?>-search" class="screen-reader-text"><?php esc_html_e( 'Part number', 'csf-parts' ); ?></label>
				<input
					type="search"
					id="<?php echo esc_attr( $block_id ); ?>-search"
					name="csf_search"
					class="csf-part-finder__input"
					placeholder="<?php echo esc_attr( $finder['search_placeholder'] ); ?>"
					autocomplete="off"
				/>
				<svg class="csf-part-finder__search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
			</div>
		<?php endif; ?>

		<?php if ( $finder['show_search'] && ( $finder['show_year'] || $finder['show_make'] || $finder['show_model'] ) ) : ?>
			<div class="csf-part-finder__divider"><span><?php esc_html_e( 'or', 'csf-parts' ); ?></span></div>
		<?php endif; ?>

		<?php if ( $finder['show_year'] || $finder['show_make'] ) : ?>
			<div class="csf-part-finder__row">
				<?php if ( $finder['show_year'] ) : ?>
					<div class="csf-part-finder__field">
						<label for="<?php echo esc_attr( $block_id ); ?>-year" class="screen-reader-text"><?php esc_html_e( 'Year', 'csf-parts' ); ?></label>
						<select id="<?php echo esc_attr( $block_id ); ?>-year" name="csf_year" class="csf-select csf-part-finder__select" data-role="year">
							<option value=""><?php esc_html_e( 'Year', 'csf-parts' ); ?></option>
							<?php foreach ( $years as $year ) : ?>
								<option value="<?php echo esc_attr( $year ); ?>"><?php echo esc_html( $year ); ?></option>
							<?php endforeach; ?>
						</select>
					</div>
				<?php endif; ?>
				<?php if ( $finder['show_make'] ) : ?>
					<div class="csf-part-finder__field">
						<label for="<?php echo esc_attr( $block_id ); ?>-make" class="screen-reader-text"><?php esc_html_e( 'Make', 'csf-parts' ); ?></label>
						<select id="<?php echo esc_attr( $block_id ); ?>-make" name="csf_make" class="csf-select csf-part-finder__select" data-role="make">
							<option value=""><?php esc_html_e( 'Make', 'csf-parts' ); ?></option>
							<?php foreach ( $makes as $make ) : ?>
								<option value="<?php echo esc_attr( $make ); ?>"><?php echo esc_html( $make ); ?></option>
							<?php endforeach; ?>
						</select>
					</div>
				<?php endif; ?>
			</div>
		<?php endif; ?>

		<?php if ( $finder['show_model'] ) : ?>
			<div class="csf-part-finder__row">
				<div class="csf-part-finder__field">
					<label for="<?php echo esc_attr( $block_id ); ?>-model" class="screen-reader-text"><?php esc_html_e( 'Model', 'csf-parts' ); ?></label>
					<select id="<?php echo esc_attr( $block_id ); ?>-model" name="csf_model" class="csf-select csf-part-finder__select" data-role="model" disabled>
						<option value=""><?php esc_html_e( 'Model', 'csf-parts' ); ?></option>
					</select>
				</div>
			</div>
		<?php endif; ?>

		<button type="submit" class="csf-btn csf-part-finder__submit"><?php echo esc_html( $finder['button_text'] ); ?></button>

		<?php if ( '' !== $footnote ) : ?>
			<p class="csf-part-finder__footnote"><?php echo esc_html( $footnote ); ?></p>
		<?php endif; ?>
	</form>
</div>
