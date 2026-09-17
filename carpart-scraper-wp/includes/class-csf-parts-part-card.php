<?php
/**
 * Part card renderer.
 *
 * Single source of the catalog card markup, used by the Product Catalog
 * block's initial render and by every AJAX response that appends or replaces
 * cards (filtering, load more, endless scroll). Keeping one renderer means
 * block-level card styling and design tokens apply identically everywhere.
 *
 * @package CSF_Parts_Catalog
 * @since   1.10.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

/**
 * Class CSF_Parts_Part_Card
 */
final class CSF_Parts_Part_Card {

	/** Maximum make badges shown before a "+N" badge. */
	private const MAX_MAKE_BADGES = 4;

	/**
	 * Render one card.
	 *
	 * @param object $part     Part row from the custom table.
	 * @param string $part_url Link target (already includes any filter params).
	 * @return string HTML.
	 */
	public static function render( object $part, string $part_url ): string {
		$display_title = csf_format_sku_display( (string) $part->sku );
		$primary_image = self::primary_image( (string) ( $part->images ?? '' ) );
		$dimensions    = self::dimensions( (string) ( $part->specifications ?? '' ) );
		$makes         = self::makes( (string) ( $part->compatibility ?? '' ) );
		$category      = (string) ( $part->category ?? '' );

		ob_start();
		?>
		<article class="csf-part-card">
			<a href="<?php echo esc_url( $part_url ); ?>" class="csf-part-card__link">
				<?php if ( $primary_image ) : ?>
					<div class="csf-part-card__image">
						<img
							src="<?php echo esc_url( $primary_image ); ?>"
							alt="<?php echo esc_attr( $display_title ); ?>"
							loading="lazy"
						/>
						<?php if ( '' !== $category ) : ?>
							<span class="csf-part-card__badge"><?php echo esc_html( $category ); ?></span>
						<?php endif; ?>
					</div>
				<?php else : ?>
					<div class="csf-part-card__image csf-part-card__image--placeholder">
						<svg width="48" height="48" viewBox="0 0 20 20" fill="currentColor" opacity="0.2" aria-hidden="true">
							<path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd"/>
						</svg>
						<?php if ( '' !== $category ) : ?>
							<span class="csf-part-card__badge"><?php echo esc_html( $category ); ?></span>
						<?php endif; ?>
					</div>
				<?php endif; ?>
				<div class="csf-part-card__content">
					<h3 class="csf-part-card__title"><?php echo esc_html( $display_title ); ?></h3>
					<?php if ( null !== $dimensions ) : ?>
						<div class="csf-dimensions-section">
							<p class="csf-dimensions-section__label"><?php esc_html_e( 'Dimensions', 'csf-parts' ); ?></p>
							<p class="csf-dimensions-section__value"><?php echo wp_kses( $dimensions, array( 'sup' => array(), 'sub' => array() ) ); ?></p>
						</div>
					<?php endif; ?>
					<?php if ( ! empty( $makes ) ) : ?>
						<div class="csf-fitment-section">
							<p class="csf-fitment-section__label"><?php esc_html_e( 'Fits Models By', 'csf-parts' ); ?></p>
							<div class="csf-part-card__makes">
								<?php foreach ( array_slice( $makes, 0, self::MAX_MAKE_BADGES ) as $make ) : ?>
									<span class="csf-part-card__make-badge"><?php echo esc_html( $make ); ?></span>
								<?php endforeach; ?>
								<?php if ( count( $makes ) > self::MAX_MAKE_BADGES ) : ?>
									<span class="csf-part-card__make-badge csf-part-card__make-badge--more">+<?php echo esc_html( (string) ( count( $makes ) - self::MAX_MAKE_BADGES ) ); ?></span>
								<?php endif; ?>
							</div>
						</div>
					<?php endif; ?>
				</div>
			</a>
		</article>
		<?php
		return (string) ob_get_clean();
	}

	/**
	 * Primary image URL: prefer the product photo (second image) over the
	 * technical drawing (first). Null when the part has no usable image.
	 *
	 * @param string $images_json JSON array of URLs or {url} objects.
	 * @return string|null
	 */
	public static function primary_image( string $images_json ): ?string {
		$images = json_decode( $images_json, true );
		if ( ! is_array( $images ) || empty( $images ) ) {
			return null;
		}

		$image   = $images[ isset( $images[1] ) ? 1 : 0 ];
		$raw_url = is_string( $image ) ? $image : ( is_array( $image ) ? ( $image['url'] ?? null ) : null );

		return $raw_url ? csf_resolve_image_url( $raw_url ) : null;
	}

	/**
	 * Box dimensions as "L × W × H" with typographic fractions, or null.
	 *
	 * @param string $specifications_json JSON object of specifications.
	 * @return string|null HTML-safe string that may contain <sup>/<sub>.
	 */
	public static function dimensions( string $specifications_json ): ?string {
		$specs = json_decode( $specifications_json, true );
		if ( ! is_array( $specs ) ) {
			return null;
		}

		$length = $specs['Box Length (in)'] ?? null;
		$width  = $specs['Box Width (in)'] ?? null;
		$height = $specs['Box Height (in)'] ?? null;
		if ( ! $length || ! $width || ! $height ) {
			return null;
		}

		return sprintf(
			'%s" × %s" × %s"',
			csf_format_dimension_fractions( (string) $length ),
			csf_format_dimension_fractions( (string) $width ),
			csf_format_dimension_fractions( (string) $height )
		);
	}

	/**
	 * Distinct vehicle makes from compatibility data, in first-seen order.
	 *
	 * @param string $compatibility_json JSON array of {make, ...} rows.
	 * @return string[]
	 */
	public static function makes( string $compatibility_json ): array {
		$rows = json_decode( $compatibility_json, true );
		if ( ! is_array( $rows ) ) {
			return array();
		}

		$makes = array();
		foreach ( $rows as $vehicle ) {
			if ( is_array( $vehicle ) && isset( $vehicle['make'] ) && ! in_array( $vehicle['make'], $makes, true ) ) {
				$makes[] = (string) $vehicle['make'];
			}
		}

		return $makes;
	}
}
