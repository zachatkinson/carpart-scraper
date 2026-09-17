<?php
/**
 * Render: CSF Part Specifications block.
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
<div <?php echo get_block_wrapper_attributes( array( 'class' => 'csf-part-block csf-part-block--spec-cards' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Escaped by core. ?>>
	<!-- Dimensions & construction -->
	<?php $show_dimensions = ( $block_attrs['showDimensions'] ?? true ) && ! empty( $spec_groups['dimensions'] ); $show_construction = ( $block_attrs['showConstruction'] ?? true ) && ! empty( $spec_groups['construction'] ); ?>
	<?php if ( $show_dimensions || $show_construction ) : ?>
		<section class="csf-section csf-spec-cards">
			<?php foreach ( array( 'dimensions' => __( 'Dimensions', 'csf-parts' ), 'construction' => __( 'Construction', 'csf-parts' ) ) as $group_key => $group_label ) : ?>
				<?php if ( ( 'dimensions' === $group_key && $show_dimensions ) || ( 'construction' === $group_key && $show_construction ) ) : ?>
					<div class="csf-spec-card">
						<h3 class="csf-spec-card__title"><?php echo esc_html( $group_label ); ?></h3>
						<dl class="csf-spec-card__list">
							<?php foreach ( $spec_groups[ $group_key ] as $spec_label => $spec_value ) : ?>
								<div class="csf-spec-card__row">
									<dt><?php echo esc_html( $spec_label ); ?></dt>
									<dd><?php echo wp_kses( csf_format_dimension_fractions( $spec_value ), array( 'sup' => array(), 'sub' => array() ) ); ?></dd>
								</div>
							<?php endforeach; ?>
						</dl>
					</div>
				<?php endif; ?>
			<?php endforeach; ?>
		</section>
	<?php endif; ?>

	<!-- Remaining specifications -->
	<?php if ( ( $block_attrs['showMore'] ?? true ) && ! empty( $spec_groups['more'] ) ) : ?>
		<section class="csf-section">
			<div class="csf-section__header">
				<h2 class="csf-section__title"><?php esc_html_e( 'More specifications', 'csf-parts' ); ?></h2>
			</div>
			<div class="csf-specs-grid">
				<?php foreach ( $spec_groups['more'] as $spec_label => $spec_value ) : ?>
					<div class="csf-spec-row">
						<dt class="spec-label"><?php echo esc_html( $spec_label ); ?></dt>
						<dd class="spec-value"><?php echo wp_kses( csf_format_dimension_fractions( $spec_value ), array( 'sup' => array(), 'sub' => array() ) ); ?></dd>
					</div>
				<?php endforeach; ?>
			</div>
		</section>
	<?php endif; ?>


</div>
