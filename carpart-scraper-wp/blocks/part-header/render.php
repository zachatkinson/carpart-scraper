<?php
/**
 * Render: CSF Part Header block.
 *
 * Reads the current part from CSF_Parts_Part_Context (set by the URL handler on
 * part pages; a sample part in the editor). Markup mirrors the pre-1.16 template.
 *
 * @package CSF_Parts_Catalog
 * @since   1.16.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

$view = CSF_Parts_Part_Context::current();
if ( null === $view ) {
	return '';
}
extract( $view ); // phpcs:ignore WordPress.PHP.DontExtract.extract_extract -- Template variables.
$block_attrs = $attributes ?? array();
?>
<div <?php echo get_block_wrapper_attributes( array( 'class' => 'csf-part-block csf-part-block--header' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Escaped by core. ?>>
			<?php if ( $block_attrs['showEyebrow'] ?? true ) : ?>
			<p class="csf-product-eyebrow">
				<a href="<?php echo esc_url( home_url( '/parts/?csf_category=' . rawurlencode( $part->category ) ) ); ?>" class="csf-product-eyebrow__link"><?php echo esc_html( $eyebrow ); ?></a>
				<?php if ( ! empty( $part->discontinued ) && 1 === (int) $part->discontinued ) : ?>
					<span class="csf-badge csf-discontinued-badge csf-discontinued-badge--inline">DISCONTINUED</span>
				<?php endif; ?>
			</p>
			<?php endif; ?>

			<h1 class="csf-product-title"><?php echo esc_html( $heading ); ?></h1>

			<?php if ( '' !== $intro && ( $block_attrs['showIntro'] ?? true ) ) : ?>
				<p class="csf-product-intro"><?php echo esc_html( $intro ); ?></p>
			<?php endif; ?>

			<?php if ( ( $block_attrs['showActions'] ?? true ) && ( '' !== $distributor_url || '' !== $tech_service_url ) ) : ?>
				<div class="csf-product-actions">
					<?php if ( '' !== $distributor_url ) : ?>
						<a class="csf-btn csf-product-actions__primary" href="<?php echo esc_url( $distributor_url ); ?>"><?php esc_html_e( 'Find a distributor', 'csf-parts' ); ?></a>
					<?php endif; ?>
					<?php if ( '' !== $tech_service_url ) : ?>
						<a class="csf-btn csf-btn--outline csf-product-actions__secondary" href="<?php echo esc_url( $tech_service_url ); ?>"><?php esc_html_e( 'Ask technical service', 'csf-parts' ); ?></a>
					<?php endif; ?>
				</div>
			<?php endif; ?>

			<?php $note_text = '' !== trim( (string) ( $block_attrs['noteText'] ?? '' ) ) ? (string) $block_attrs['noteText'] : $part_page_note; ?>
			<?php if ( ( $block_attrs['showActions'] ?? true ) && '' !== trim( $note_text ) ) : ?>
				<p class="csf-reference-note"><?php echo esc_html( $note_text ); ?></p>
			<?php endif; ?>

			<!-- Your Vehicle Box (if applicable) -->
			<?php if ( $is_vehicle_specific && ( $block_attrs['showVehicleBox'] ?? true ) ) : ?>
				<?php
				// Extract unique engine variants for this specific YMM
				$engine_variants = array();
				if ( ! empty( $compatibility ) && is_array( $compatibility ) ) {
					foreach ( $compatibility as $vehicle ) {
						// Match the searched YMM
						$year_match  = empty( $year ) || (string) $vehicle['year'] === (string) $year;
						$make_match  = empty( $make ) || strcasecmp( $vehicle['make'], $make ) === 0;
						$model_match = empty( $model ) || strcasecmp( $vehicle['model'], $model ) === 0;

						if ( $year_match && $make_match && $model_match ) {
							$engine = isset( $vehicle['engine'] ) && ! empty( $vehicle['engine'] ) ? $vehicle['engine'] : '';
							if ( $engine && ! in_array( $engine, $engine_variants, true ) ) {
								$engine_variants[] = $engine;
							}
						}
					}
				}

				// Sort engine variants naturally
				sort( $engine_variants );
				?>
				<div class="csf-your-vehicle-box">
					<div class="your-vehicle-header">
						<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
							<path d="M5 17h14v-5H5v5z"></path>
							<path d="M7 18v2"></path>
							<path d="M17 18v2"></path>
							<path d="M2 8l2-3h16l2 3"></path>
						</svg>
						<strong>Your Vehicle</strong>
					</div>
					<div class="your-vehicle-ymm">
						<?php echo esc_html( "$year $make $model" ); ?>
					</div>
					<?php if ( count( $engine_variants ) > 1 ) : ?>
						<div class="your-vehicle-engine-selector">
						<div class="engine-notice">
							<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
								<circle cx="12" cy="12" r="10"></circle>
								<line x1="12" y1="16" x2="12" y2="12"></line>
								<line x1="12" y1="8" x2="12.01" y2="8"></line>
							</svg>
							<div class="engine-notice__body">
								<strong class="engine-notice__title">Please select your vehicle's engine.</strong>
								<span class="engine-notice__hint">Unsure? Contact your local dealer or distributor to verify this part fits your specific vehicle configuration.</span>
							</div>
						</div>
							<label for="csf-engine-variant">Select Engine:</label>
							<?php
							// Use helper function for consistent dropdown rendering.
							echo csf_render_select(
								array(
									'id'           => 'csf-engine-variant',
									'name'         => 'csf_engine',
									'options'      => array_combine( $engine_variants, $engine_variants ),
									'placeholder'  => 'Not Sure / Don\'t Know',
									'class'        => 'csf-engine-variant-dropdown',
									'show_wrapper' => false,
								)
							);
							?>
						</div>
					<?php elseif ( count( $engine_variants ) === 1 ) : ?>
						<div class="your-vehicle-engine-single">
							<span class="engine-label">Engine:</span>
							<span class="engine-value"><?php echo esc_html( $engine_variants[0] ); ?></span>
						</div>
						<div class="engine-verify-notice">
							Please verify this matches your vehicle's engine before purchasing.
						</div>
					<?php endif; ?>
				</div>
			<?php endif; ?>


</div>
