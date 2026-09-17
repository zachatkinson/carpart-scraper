<?php
/**
 * Render: CSF Related Parts block.
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
<div <?php echo get_block_wrapper_attributes( array( 'class' => 'csf-part-block csf-part-block--related' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Escaped by core. ?>>
	<!-- Other parts for this vehicle -->
	<?php
	$related_limit = isset( $block_attrs['count'] ) && is_numeric( $block_attrs['count'] ) ? (int) $block_attrs['count'] : count( $related_parts['parts'] );
	$related_list  = array_slice( $related_parts['parts'], 0, max( 0, $related_limit ) );
	?>
	<?php if ( ! empty( $related_list ) ) : ?>
		<section class="csf-section csf-related">
			<div class="csf-section__header">
				<div>
					<h2 class="csf-section__title"><?php echo esc_html( '' !== trim( (string) ( $block_attrs['title'] ?? '' ) ) ? $block_attrs['title'] : $related_parts['heading'] ); ?></h2>
					<?php if ( '' !== $related_parts['meta'] ) : ?>
						<p class="csf-section__meta"><?php echo esc_html( $related_parts['meta'] ); ?></p>
					<?php endif; ?>
				</div>
				<?php if ( '' !== $related_parts['url'] ) : ?>
					<a class="csf-section__link" href="<?php echo esc_url( $related_parts['url'] ); ?>"><?php echo esc_html( $related_parts['link_label'] ); ?></a>
				<?php endif; ?>
			</div>
			<div class="csf-related__grid csf-grid-items">
				<?php foreach ( $related_list as $related ) : ?>
					<?php echo CSF_Parts_Part_Card::render( $related, csf_get_part_url( (string) $related->sku ), array( 'show_fitment_line' => true ) ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Escaped in the renderer. ?>
				<?php endforeach; ?>
			</div>
		</section>
	<?php endif; ?>


</div>
