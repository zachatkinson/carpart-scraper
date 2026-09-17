<?php
/**
 * Render: CSF Part Fitment block.
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
<div <?php echo get_block_wrapper_attributes( array( 'class' => 'csf-part-block csf-part-block--fitment' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Escaped by core. ?>>
	<!-- Fits these vehicles -->
	<?php if ( ! empty( $compatibility ) ) : ?>
		<section class="csf-section csf-fitment">
			<div class="csf-section__header">
				<h2 class="csf-section__title"><?php echo esc_html( '' !== trim( (string) ( $block_attrs['title'] ?? '' ) ) ? $block_attrs['title'] : __( 'Fits these vehicles', 'csf-parts' ) ); ?></h2>
				<?php if ( $block_attrs['showSummary'] ?? true ) : ?>
				<p class="csf-section__meta"><?php echo esc_html( CSF_Parts_Part_Page::fitment_counts( $fitment_rows ) ); ?></p>
				<?php endif; ?>
			</div>
			<?php $effective_layout = in_array( (string) ( $block_attrs['layout'] ?? '' ), CSF_Parts_Constants::FITMENT_LAYOUTS, true ) ? (string) $block_attrs['layout'] : $fitment_layout; ?>
			<?php if ( CSF_Parts_Constants::FITMENT_LAYOUT_CARDS === $effective_layout ) : ?>
				<?php include CSF_PARTS_PLUGIN_DIR . 'templates/parts/fitment-cards.php'; ?>
			<?php else : ?>
				<div class="csf-fitment-table-wrap">
					<table class="csf-fitment-table">
						<thead>
							<tr>
								<th scope="col"><?php esc_html_e( 'Make', 'csf-parts' ); ?></th>
								<th scope="col"><?php esc_html_e( 'Model', 'csf-parts' ); ?></th>
								<th scope="col"><?php esc_html_e( 'Years', 'csf-parts' ); ?></th>
								<th scope="col"><?php esc_html_e( 'Engine', 'csf-parts' ); ?></th>
								<th scope="col"><?php esc_html_e( 'Notes', 'csf-parts' ); ?></th>
							</tr>
						</thead>
						<tbody>
							<?php foreach ( $fitment_rows as $row ) : ?>
								<?php $row_is_yours = CSF_Parts_Part_Page::row_matches( $row, (string) $searched_year, (string) $searched_make, (string) $searched_model ); ?>
								<tr class="csf-fitment-row<?php echo $row_is_yours ? ' is-yours' : ''; ?>" data-make="<?php echo esc_attr( strtolower( $row['make'] ) ); ?>" data-model="<?php echo esc_attr( strtolower( $row['model'] ) ); ?>" data-engine="<?php echo esc_attr( $row['engine'] ); ?>">
									<td class="csf-fitment-row__make"><?php echo esc_html( $row['make'] ); ?></td>
									<td><?php echo esc_html( $row['model'] ); ?></td>
									<td><?php echo esc_html( $row['years_text'] ); ?></td>
									<td><?php echo esc_html( '' !== $row['engine'] ? $row['engine'] : '—' ); ?></td>
									<td class="csf-fitment-row__notes">
										<?php if ( $row_is_yours ) : ?>
											<span class="csf-fitment-yours"><?php esc_html_e( 'Your vehicle', 'csf-parts' ); ?></span>
										<?php endif; ?>
										<?php echo esc_html( '' !== $row['notes'] ? $row['notes'] : __( 'All trims', 'csf-parts' ) ); ?>
									</td>
								</tr>
							<?php endforeach; ?>
						</tbody>
					</table>
				</div>
			<?php endif; ?>
		</section>
	<?php endif; ?>


</div>
