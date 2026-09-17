<?php
/**
 * Render: CSF Part Key Specs block.
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
<div <?php echo get_block_wrapper_attributes( array( 'class' => 'csf-part-block csf-part-block--key-specs' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Escaped by core. ?>>
			<!-- Key specifications -->
			<?php if ( ! empty( $spec_groups['key'] ) ) : ?>
				<div class="csf-quick-specs">
					<h3><?php echo esc_html( '' !== trim( (string) ( $block_attrs['title'] ?? '' ) ) ? $block_attrs['title'] : __( 'Key specifications', 'csf-parts' ) ); ?></h3>
					<ul>
						<?php foreach ( array_slice( $spec_groups['key'], 0, max( 1, (int) ( $block_attrs['maxRows'] ?? 8 ) ), true ) as $spec_label => $spec_value ) : ?>
							<li>
								<span class="spec-label"><?php echo esc_html( $spec_label ); ?></span>
								<span class="spec-value"><?php echo wp_kses( csf_format_dimension_fractions( $spec_value ), array( 'sup' => array(), 'sub' => array() ) ); ?></span>
							</li>
						<?php endforeach; ?>
					</ul>
				</div>
			<?php endif; ?>


</div>
