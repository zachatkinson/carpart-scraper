<?php
/**
 * Render: CSF Part Features block.
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
<div <?php echo get_block_wrapper_attributes( array( 'class' => 'csf-part-block csf-part-block--features' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Escaped by core. ?>>
	<!-- Features -->
	<?php if ( ! empty( $features ) ) : ?>
		<section class="csf-section">
			<div class="csf-section__header">
				<h2 class="csf-section__title"><?php echo esc_html( '' !== trim( (string) ( $block_attrs['title'] ?? '' ) ) ? $block_attrs['title'] : __( 'Features & benefits', 'csf-parts' ) ); ?></h2>
			</div>
			<ul class="csf-features-list">
				<?php foreach ( $features as $feature ) : ?>
					<li>
						<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>
						<?php echo esc_html( $feature ); ?>
					</li>
				<?php endforeach; ?>
			</ul>
		</section>
	<?php endif; ?>


</div>
