<?php
/**
 * Render: CSF Part Gallery block.
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
<div <?php echo get_block_wrapper_attributes( array( 'class' => 'csf-part-block csf-part-block--gallery' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Escaped by core. ?>>
		<!-- Left Column: Image Gallery -->
		<div class="csf-product-gallery">
			<?php if ( ! empty( $images ) ) : ?>
				<?php
				$first_image_url = $get_image_url( $images[0] );
				$first_image_alt = $get_image_alt( $images[0], $title );
				?>

				<!-- Main Image -->
				<div class="csf-gallery-main">
					<?php if ( ! empty( $first_image_url ) ) : ?>
						<img
							id="csf-main-image"
							src="<?php echo esc_url( $first_image_url ); ?>"
							alt="<?php echo esc_attr( $first_image_alt ); ?>"
							class="csf-main-image"
						>
					<?php else : ?>
						<div class="csf-no-image-placeholder">
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
								<rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
								<circle cx="8.5" cy="8.5" r="1.5"></circle>
								<polyline points="21 15 16 10 5 21"></polyline>
							</svg>
							<p>No image available</p>
						</div>
					<?php endif; ?>
				</div>

				<!-- Thumbnail Gallery -->
				<?php if ( count( $images ) > 1 && ( $block_attrs['showThumbnails'] ?? true ) ) : ?>
					<div class="csf-gallery-thumbs">
						<?php foreach ( $images as $index => $image ) : ?>
							<?php
							$thumb_url = $get_image_url( $image );
							$thumb_alt = $get_image_alt( $image, $title );
							?>
							<?php if ( ! empty( $thumb_url ) ) : ?>
								<button
									class="csf-thumb <?php echo 0 === $index ? 'active' : ''; ?>"
									type="button"
									data-src="<?php echo esc_url( $thumb_url ); ?>"
									aria-label="View image <?php echo esc_attr( $index + 1 ); ?>"
								>
									<img
										src="<?php echo esc_url( $thumb_url ); ?>"
										alt="<?php echo esc_attr( $thumb_alt ); ?>"
									>
								</button>
							<?php endif; ?>
						<?php endforeach; ?>
					</div>
				<?php endif; ?>
			<?php else : ?>
				<div class="csf-no-image-placeholder">
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
						<circle cx="8.5" cy="8.5" r="1.5"></circle>
						<polyline points="21 15 16 10 5 21"></polyline>
					</svg>
					<p>No image available</p>
				</div>
			<?php endif; ?>
		</div>


</div>
