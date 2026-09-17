<?php
/**
 * Render: CSF Part Replaces block.
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
<div <?php echo get_block_wrapper_attributes( array( 'class' => 'csf-part-block csf-part-block--replaces' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Escaped by core. ?>>
			<!-- Replaces (interchange numbers) -->
			<?php if ( ! empty( $interchange_numbers ) ) : ?>
				<?php
				usort(
					$interchange_numbers,
					static function ( $a, $b ) {
						$type_compare = strcmp( $a['reference_type'] ?? '', $b['reference_type'] ?? '' );
						return 0 !== $type_compare ? $type_compare : strcmp( $a['reference_number'] ?? '', $b['reference_number'] ?? '' );
					}
				);
				?>
				<div class="csf-replaces">
					<span class="csf-replaces__label"><?php echo esc_html( '' !== trim( (string) ( $block_attrs['label'] ?? '' ) ) ? $block_attrs['label'] : __( 'Replaces', 'csf-parts' ) ); ?></span>
					<div class="csf-interchange-grid">
						<?php foreach ( $interchange_numbers as $reference ) : ?>
							<div class="csf-interchange-card">
								<span class="interchange-type"><?php echo esc_html( $reference['reference_type'] ?? 'OEM' ); ?></span>
								<span class="interchange-number"><?php echo esc_html( $reference['reference_number'] ?? '' ); ?></span>
							</div>
						<?php endforeach; ?>
					</div>
				</div>
			<?php endif; ?>


</div>
