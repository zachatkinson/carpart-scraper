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

	/** Maximum vehicles named in the fitment summary before "+N more". */
	private const MAX_SUMMARY_VEHICLES = 3;

	/** Render options and their defaults. */
	private const DEFAULT_OPTIONS = array(
		'new_badge_days'    => 30,
		'show_fitment_line' => true,
		'show_meta_line'    => true,
	);

	/**
	 * Coerce render options (from block attributes or an AJAX payload).
	 *
	 * @param array<string, mixed> $options Raw options.
	 * @return array{new_badge_days: int, show_fitment_line: bool, show_meta_line: bool}
	 */
	public static function sanitize_options( array $options ): array {
		return array(
			'new_badge_days'    => max( 0, min( 365, (int) ( $options['new_badge_days'] ?? self::DEFAULT_OPTIONS['new_badge_days'] ) ) ),
			'show_fitment_line' => (bool) ( $options['show_fitment_line'] ?? self::DEFAULT_OPTIONS['show_fitment_line'] ),
			'show_meta_line'    => (bool) ( $options['show_meta_line'] ?? self::DEFAULT_OPTIONS['show_meta_line'] ),
		);
	}

	/**
	 * Render one card.
	 *
	 * @param object $part     Part row from the custom table.
	 * @param string $part_url Link target (already includes any filter params).
	 * @return string HTML.
	 */
	public static function render( object $part, string $part_url, array $options = array() ): string {
		$options       = self::sanitize_options( $options );
		$display_title = csf_format_sku_display( (string) $part->sku );
		$primary_image = self::primary_image( (string) ( $part->images ?? '' ) );
		$makes         = self::makes( (string) ( $part->compatibility ?? '' ) );
		$category      = (string) ( $part->category ?? '' );
		$is_new        = self::is_new( (string) ( $part->created_at ?? '' ), $options['new_badge_days'] );
		$fitment       = $options['show_fitment_line'] ? self::fitment_summary( (string) ( $part->compatibility ?? '' ) ) : '';
		$meta          = $options['show_meta_line'] ? self::meta_line( $part ) : '';

		ob_start();
		?>
		<article class="csf-part-card">
			<a href="<?php echo esc_url( $part_url ); ?>" class="csf-part-card__link">
				<?php if ( $primary_image ) : ?>
					<div class="csf-part-card__image">
						<?php if ( $is_new ) : ?>
							<span class="csf-part-card__new"><?php esc_html_e( 'New', 'csf-parts' ); ?></span>
						<?php endif; ?>
						<img
							src="<?php echo esc_url( $primary_image ); ?>"
							alt="<?php echo esc_attr( $display_title ); ?>"
							loading="lazy"
						/>
					</div>
				<?php else : ?>
					<div class="csf-part-card__image csf-part-card__image--placeholder">
						<?php if ( $is_new ) : ?>
							<span class="csf-part-card__new"><?php esc_html_e( 'New', 'csf-parts' ); ?></span>
						<?php endif; ?>
						<svg width="48" height="48" viewBox="0 0 20 20" fill="currentColor" opacity="0.2" aria-hidden="true">
							<path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd"/>
						</svg>
					</div>
				<?php endif; ?>
				<div class="csf-part-card__content">
					<?php if ( '' !== $category ) : ?>
						<p class="csf-part-card__badge"><?php echo esc_html( $category ); ?></p>
					<?php endif; ?>
					<h3 class="csf-part-card__title"><?php echo esc_html( $display_title ); ?></h3>
					<?php if ( '' !== $fitment ) : ?>
						<p class="csf-part-card__fitment"><?php echo esc_html( $fitment ); ?></p>
					<?php endif; ?>
					<?php if ( '' !== $meta ) : ?>
						<p class="csf-part-card__meta"><?php echo wp_kses( $meta, array( 'sup' => array(), 'sub' => array() ) ); ?></p>
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
			'%s × %s × %s in',
			csf_format_dimension_fractions( (string) $length ),
			csf_format_dimension_fractions( (string) $width ),
			csf_format_dimension_fractions( (string) $height )
		);
	}

	/**
	 * Whether the part was added within the badge window.
	 *
	 * @param string $created_at MySQL datetime.
	 * @param int    $days       Window in days; 0 disables the badge.
	 * @return bool
	 */
	public static function is_new( string $created_at, int $days ): bool {
		if ( $days <= 0 || '' === $created_at ) {
			return false;
		}
		$created = strtotime( $created_at );
		return false !== $created && ( time() - $created ) <= $days * DAY_IN_SECONDS;
	}

	/**
	 * One-line fitment summary, e.g. "2024 to 2026 Toyota Tacoma, 2.4L L4 turbo".
	 *
	 * Year range, then vehicles grouped by make (capped), then the engine when
	 * every row agrees on one.
	 *
	 * @param string $compatibility_json JSON array of {year, make, model, engine} rows.
	 * @return string Empty when there is no compatibility data.
	 */
	public static function fitment_summary( string $compatibility_json ): string {
		$rows = json_decode( $compatibility_json, true );
		if ( ! is_array( $rows ) || empty( $rows ) ) {
			return '';
		}

		$years    = array();
		$vehicles = array(); // make => [models]
		$engines  = array();
		foreach ( $rows as $row ) {
			if ( ! is_array( $row ) ) {
				continue;
			}
			if ( ! empty( $row['year'] ) ) {
				$years[] = (int) $row['year'];
			}
			$make  = trim( (string) ( $row['make'] ?? '' ) );
			$model = trim( (string) ( $row['model'] ?? '' ) );
			if ( '' !== $make ) {
				$vehicles[ $make ] = $vehicles[ $make ] ?? array();
				if ( '' !== $model && ! in_array( $model, $vehicles[ $make ], true ) ) {
					$vehicles[ $make ][] = $model;
				}
			}
			$engine = CSF_Parts_Vehicle_Names::engine_short( (string) ( $row['engine'] ?? '' ), (string) ( $row['aspiration'] ?? '' ) );
			if ( '' !== $engine && ! in_array( $engine, $engines, true ) ) {
				$engines[] = $engine;
			}
		}

		$parts = array();
		if ( ! empty( $years ) ) {
			$min = min( $years );
			$max = max( $years );
			$parts[] = $min === $max ? (string) $min : sprintf( '%d to %d', $min, $max );
		}

		// Name up to MAX_SUMMARY_VEHICLES vehicles ("Audi A3, TT, Volkswagen Golf"), then "and others".
		$names = array();
		$named = 0; // vehicles (make+model) already named
		$more  = false;
		foreach ( $vehicles as $make => $models ) {
			if ( $named >= self::MAX_SUMMARY_VEHICLES ) {
				$more = true;
				break;
			}
			$make_name = CSF_Parts_Vehicle_Names::make( $make );
			if ( empty( $models ) ) {
				$names[] = $make_name;
				$named++;
				continue;
			}
			$shown  = array_slice( $models, 0, self::MAX_SUMMARY_VEHICLES - $named );
			$named += count( $shown );
			$more   = $more || count( $models ) > count( $shown );
			$names[] = $make_name . ' ' . implode( ', ', array_map( array( CSF_Parts_Vehicle_Names::class, 'model' ), $shown ) );
		}
		if ( ! empty( $names ) ) {
			$parts[] = implode( ', ', $names ) . ( $more ? ' and others' : '' );
		}

		$summary = implode( ' ', $parts );
		if ( 1 === count( $engines ) ) {
			$summary .= ( '' !== $summary ? ', ' : '' ) . $engines[0];
		}

		return $summary;
	}

	/**
	 * Meta line: dimensions and the primary OE number, e.g.
	 * "31 ⅝ × 21 × 4 ⅞ in · OE 16400-AK030". Either half may be absent.
	 *
	 * @param object $part Part row.
	 * @return string HTML-safe string that may contain <sup>/<sub>.
	 */
	public static function meta_line( object $part ): string {
		$pieces = array();

		$dimensions = self::dimensions( (string) ( $part->specifications ?? '' ) );
		if ( null !== $dimensions ) {
			$pieces[] = $dimensions;
		}

		$oe = self::primary_oe_number( (string) ( $part->interchange_numbers ?? '' ) );
		if ( '' !== $oe ) {
			$pieces[] = 'OE ' . $oe;
		}

		return implode( ' · ', $pieces );
	}

	/**
	 * The first OEM interchange number, falling back to the first of any type.
	 *
	 * @param string $interchange_json JSON array of {reference_type, reference_number}.
	 * @return string
	 */
	public static function primary_oe_number( string $interchange_json ): string {
		$refs = json_decode( $interchange_json, true );
		if ( ! is_array( $refs ) || empty( $refs ) ) {
			return '';
		}
		$first = '';
		foreach ( $refs as $ref ) {
			if ( ! is_array( $ref ) || empty( $ref['reference_number'] ) ) {
				continue;
			}
			$number = trim( (string) $ref['reference_number'] );
			if ( '' === $first ) {
				$first = $number;
			}
			if ( 0 === strcasecmp( (string) ( $ref['reference_type'] ?? '' ), 'OEM' ) ) {
				return $number;
			}
		}
		return $first;
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
				$makes[] = CSF_Parts_Vehicle_Names::make( (string) $vehicle['make'] );
			}
		}

		return $makes;
	}
}
