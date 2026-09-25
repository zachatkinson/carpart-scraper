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

	/** Maximum vehicles (or makes, in the breadth form) named in the fitment summary before "and others". */
	private const MAX_SUMMARY_VEHICLES = 3;

	/** Dimensions a fitment context can narrow on; each is a list of stored values. */
	private const CONTEXT_KEYS = array( 'makes', 'models', 'years' );

	/** Render options and their defaults. */
	private const DEFAULT_OPTIONS = array(
		'new_badge_days'    => 30,
		'show_fitment_line' => true,
		'show_meta_line'    => true,
		'fitment_context'   => array(),
	);

	/**
	 * Coerce render options (from block attributes or an AJAX payload).
	 *
	 * @param array<string, mixed> $options Raw options.
	 * @return array{new_badge_days: int, show_fitment_line: bool, show_meta_line: bool, fitment_context: array{makes: string[], models: string[], years: string[]}}
	 */
	public static function sanitize_options( array $options ): array {
		return array(
			'new_badge_days'    => max( 0, min( 365, (int) ( $options['new_badge_days'] ?? self::DEFAULT_OPTIONS['new_badge_days'] ) ) ),
			'show_fitment_line' => (bool) ( $options['show_fitment_line'] ?? self::DEFAULT_OPTIONS['show_fitment_line'] ),
			'show_meta_line'    => (bool) ( $options['show_meta_line'] ?? self::DEFAULT_OPTIONS['show_meta_line'] ),
			'fitment_context'   => self::sanitize_context( $options['fitment_context'] ?? self::DEFAULT_OPTIONS['fitment_context'] ),
		);
	}

	/**
	 * Coerce a fitment context: the vehicles a page or filter is about.
	 *
	 * @param mixed $context Raw context, e.g. ['makes' => ['Ford'], 'models' => [], 'years' => ['2015']].
	 * @return array{makes: string[], models: string[], years: string[]}
	 */
	public static function sanitize_context( $context ): array {
		$clean = array_fill_keys( self::CONTEXT_KEYS, array() );
		if ( ! is_array( $context ) ) {
			return $clean;
		}
		foreach ( self::CONTEXT_KEYS as $key ) {
			foreach ( (array) ( $context[ $key ] ?? array() ) as $value ) {
				$value = is_scalar( $value ) ? trim( (string) $value ) : '';
				if ( '' !== $value && ! in_array( $value, $clean[ $key ], true ) ) {
					$clean[ $key ][] = $value;
				}
			}
		}
		return $clean;
	}

	/**
	 * The fitment context implied by a catalog query's vehicle filters, so the
	 * summary describes the same vehicles the results were narrowed to.
	 *
	 * @param array<string, mixed> $filters Filters as passed to CSF_Parts_Database::query_parts().
	 * @return array{makes: string[], models: string[], years: string[]}
	 */
	public static function context_from_filters( array $filters ): array {
		return self::sanitize_context( array_intersect_key( $filters, array_flip( self::CONTEXT_KEYS ) ) );
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
		$badge         = self::activity_badge( $part, $options['new_badge_days'] );
		$fitment       = $options['show_fitment_line'] ? self::fitment_summary( (string) ( $part->compatibility ?? '' ), $options['fitment_context'] ) : '';
		$meta          = $options['show_meta_line'] ? self::meta_line( $part ) : '';

		ob_start();
		?>
		<article class="csf-part-card">
			<a href="<?php echo esc_url( $part_url ); ?>" class="csf-part-card__link">
				<?php if ( $primary_image ) : ?>
					<div class="csf-part-card__image">
						<?php if ( 'new' === $badge ) : ?>
							<span class="csf-part-card__new"><?php esc_html_e( 'New', 'csf-parts' ); ?></span>
						<?php elseif ( 'updated' === $badge ) : ?>
							<span class="csf-part-card__new csf-part-card__new--updated"><?php esc_html_e( 'Updated', 'csf-parts' ); ?></span>
						<?php endif; ?>
						<img
							src="<?php echo esc_url( $primary_image ); ?>"
							alt="<?php echo esc_attr( $display_title ); ?>"
							loading="lazy"
						/>
					</div>
				<?php else : ?>
					<div class="csf-part-card__image csf-part-card__image--placeholder">
						<?php if ( 'new' === $badge ) : ?>
							<span class="csf-part-card__new"><?php esc_html_e( 'New', 'csf-parts' ); ?></span>
						<?php elseif ( 'updated' === $badge ) : ?>
							<span class="csf-part-card__new csf-part-card__new--updated"><?php esc_html_e( 'Updated', 'csf-parts' ); ?></span>
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
	 * Which activity badge a card shows.
	 *
	 * 'new' when the import first saw the part within the window, 'updated'
	 * when its content last changed within it, '' otherwise. Both timestamps
	 * are set by the import only when CSF's data differs, so the badge tracks
	 * catalog activity rather than database writes.
	 *
	 * @since 1.20.0
	 * @param object $part Part row with created_at and updated_at.
	 * @param int    $days Window in days; 0 disables the badge.
	 * @return string 'new', 'updated' or ''.
	 */
	public static function activity_badge( object $part, int $days ): string {
		if ( self::is_new( (string) ( $part->created_at ?? '' ), $days ) ) {
			return 'new';
		}
		if ( self::is_recent( (string) ( $part->updated_at ?? '' ), $days ) ) {
			return 'updated';
		}
		return '';
	}

	/**
	 * Whether the part was added within the badge window.
	 *
	 * @param string $created_at MySQL datetime.
	 * @param int    $days       Window in days; 0 disables the badge.
	 * @return bool
	 */
	public static function is_new( string $created_at, int $days ): bool {
		return self::is_recent( $created_at, $days );
	}

	/**
	 * Whether a timestamp falls within the last N days.
	 *
	 * @since 1.20.0
	 * @param string $datetime MySQL datetime.
	 * @param int    $days     Window in days; 0 always returns false.
	 * @return bool
	 */
	public static function is_recent( string $datetime, int $days ): bool {
		if ( $days <= 0 || '' === $datetime ) {
			return false;
		}
		$timestamp = strtotime( $datetime );
		return false !== $timestamp && ( time() - $timestamp ) <= $days * DAY_IN_SECONDS;
	}

	/**
	 * One-line fitment summary, e.g. "2024 to 2026 Toyota Tacoma, 2.4 L turbo".
	 *
	 * With a context (the vehicles a page or filter is about), vehicles matching
	 * it lead the line: the year range and engine come from their rows, and
	 * anything else only contributes to "and others". A vehicle matches when its
	 * make and model are in the context (empty lists match anything) and, when
	 * years are given, it fits at least one of them; the range then spans every
	 * year that vehicle fits, so a visitor with a 2015 van still learns the part
	 * covers 2015 to 2019.
	 *
	 * Vehicles are named by most model-years first, then alphabetically, so the
	 * vehicle a part is mainly for comes first. When the vehicles to name span
	 * more than MAX_SUMMARY_VEHICLES makes (no context, a context matching
	 * nothing, or a context that wide), the part is described by breadth
	 * instead: "Fits 18 makes including Ford, Chevrolet and Toyota, 1970 to 2014".
	 *
	 * @param string               $compatibility_json JSON array of {year, make, model, engine} rows.
	 * @param array<string, mixed> $context            Optional ['makes' => [], 'models' => [], 'years' => []].
	 * @return string Empty when there is no compatibility data.
	 */
	public static function fitment_summary( string $compatibility_json, array $context = array() ): string {
		$rows = json_decode( $compatibility_json, true );
		if ( ! is_array( $rows ) || empty( $rows ) ) {
			return '';
		}

		$context  = self::sanitize_context( $context );
		$vehicles = self::vehicles( $rows, $context );
		if ( empty( $vehicles ) ) {
			return '';
		}

		// Only a non-empty context can single out vehicles; an empty one is "no context", not "everything".
		$matched = empty( array_filter( $context ) ) ? array() : array_values( array_filter( $vehicles, static fn( array $v ): bool => $v['matches'] ) );
		$lead    = ! empty( $matched ) ? $matched : $vehicles;
		usort( $lead, array( self::class, 'compare_vehicles' ) );

		$years   = array();
		$engines = array();
		foreach ( $lead as $vehicle ) {
			$years   = array_merge( $years, $vehicle['years'] );
			$engines = array_unique( array_merge( $engines, $vehicle['engines'] ) );
		}
		$range = self::year_range( $years );

		// Too many makes to name vehicles usefully (the make badges show them anyway): describe breadth.
		$lead_makes = array_unique( array_map( static fn( array $v ): string => strtolower( $v['make'] ), $lead ) );
		if ( count( $lead_makes ) > self::MAX_SUMMARY_VEHICLES ) {
			$summary = self::breadth_summary( $vehicles, $lead, $range );
		} else {
			$named   = array_slice( $lead, 0, self::MAX_SUMMARY_VEHICLES );
			$summary = trim( $range . ' ' . self::vehicle_list( $named ) . ( count( $vehicles ) > count( $named ) ? ' and others' : '' ) );
		}

		if ( 1 === count( $engines ) ) {
			$summary .= ( '' !== $summary ? ', ' : '' ) . reset( $engines );
		}

		return $summary;
	}

	/**
	 * Distinct vehicles (make + model) with their model-years, engines and
	 * whether they match the context.
	 *
	 * @param array<int, mixed>                                        $rows    Decoded compatibility rows.
	 * @param array{makes: string[], models: string[], years: string[]} $context Sanitised context.
	 * @return array<int, array{make: string, model: string, years: int[], engines: string[], matches: bool}>
	 */
	private static function vehicles( array $rows, array $context ): array {
		$vehicles = array();
		foreach ( $rows as $row ) {
			if ( ! is_array( $row ) ) {
				continue;
			}
			$make  = trim( (string) ( $row['make'] ?? '' ) );
			$model = trim( (string) ( $row['model'] ?? '' ) );
			if ( '' === $make ) {
				continue;
			}
			$key = strtolower( $make . '|' . $model );
			$vehicles[ $key ] = $vehicles[ $key ] ?? array( 'make' => $make, 'model' => $model, 'years' => array(), 'engines' => array(), 'matches' => false );

			$year = (int) ( $row['year'] ?? 0 );
			if ( $year > 0 && ! in_array( $year, $vehicles[ $key ]['years'], true ) ) {
				$vehicles[ $key ]['years'][] = $year;
			}
			$engine = CSF_Parts_Vehicle_Names::engine_short( (string) ( $row['engine'] ?? '' ), (string) ( $row['aspiration'] ?? '' ) );
			if ( '' !== $engine && ! in_array( $engine, $vehicles[ $key ]['engines'], true ) ) {
				$vehicles[ $key ]['engines'][] = $engine;
			}
		}

		$makes  = array_map( 'strtolower', $context['makes'] );
		$models = array_map( 'strtolower', $context['models'] );
		$years  = array_map( 'intval', $context['years'] );
		foreach ( $vehicles as $key => $vehicle ) {
			$vehicles[ $key ]['matches'] = ( empty( $makes ) || in_array( strtolower( $vehicle['make'] ), $makes, true ) )
				&& ( empty( $models ) || in_array( strtolower( $vehicle['model'] ), $models, true ) )
				&& ( empty( $years ) || ! empty( array_intersect( $vehicle['years'], $years ) ) );
		}

		return array_values( $vehicles );
	}

	/**
	 * Order vehicles by most model-years, then make, then model.
	 *
	 * @param array{make: string, model: string, years: int[]} $a First vehicle.
	 * @param array{make: string, model: string, years: int[]} $b Second vehicle.
	 * @return int
	 */
	private static function compare_vehicles( array $a, array $b ): int {
		return ( count( $b['years'] ) <=> count( $a['years'] ) )
			?: strcasecmp( $a['make'], $b['make'] )
			?: strnatcasecmp( $a['model'], $b['model'] );
	}

	/**
	 * "1992 to 1996", "2015", or '' when no years are known.
	 *
	 * @param int[] $years Model years, any order, duplicates allowed.
	 * @return string
	 */
	private static function year_range( array $years ): string {
		if ( empty( $years ) ) {
			return '';
		}
		$min = min( $years );
		$max = max( $years );
		return $min === $max ? (string) $min : sprintf( '%d to %d', $min, $max );
	}

	/**
	 * Vehicles grouped by make in the order given: "Ford E-350 Econoline, Econoline Super Duty, GMC Canyon".
	 *
	 * @param array<int, array{make: string, model: string}> $vehicles Vehicles to name.
	 * @return string
	 */
	private static function vehicle_list( array $vehicles ): string {
		$groups = array(); // make => [models]
		foreach ( $vehicles as $vehicle ) {
			$groups[ $vehicle['make'] ] = $groups[ $vehicle['make'] ] ?? array();
			if ( '' !== $vehicle['model'] ) {
				$groups[ $vehicle['make'] ][] = CSF_Parts_Vehicle_Names::model( $vehicle['model'] );
			}
		}
		$names = array();
		foreach ( $groups as $make => $models ) {
			$names[] = trim( CSF_Parts_Vehicle_Names::make( (string) $make ) . ' ' . implode( ', ', $models ) );
		}
		return implode( ', ', $names );
	}

	/**
	 * Breadth form for parts fitting many makes: "Fits 18 makes including Ford, Chevrolet and Toyota, 1970 to 2014".
	 *
	 * @param array<int, array{make: string, years: int[]}> $all   Every vehicle the part fits.
	 * @param array<int, array{make: string, years: int[]}> $lead  Vehicles to draw the named makes from, best first.
	 * @param string                                        $range Year range for the lead vehicles.
	 * @return string
	 */
	private static function breadth_summary( array $all, array $lead, string $range ): string {
		$total = count( array_unique( array_map( static fn( array $v ): string => strtolower( $v['make'] ), $all ) ) );

		$model_years = array(); // make => model-years
		foreach ( $lead as $vehicle ) {
			$model_years[ $vehicle['make'] ] = ( $model_years[ $vehicle['make'] ] ?? 0 ) + count( $vehicle['years'] );
		}
		uksort( $model_years, static fn( string $a, string $b ): int => ( $model_years[ $b ] <=> $model_years[ $a ] ) ?: strcasecmp( $a, $b ) );
		$named = array_map( array( CSF_Parts_Vehicle_Names::class, 'make' ), array_slice( array_keys( $model_years ), 0, self::MAX_SUMMARY_VEHICLES ) );
		$last  = array_pop( $named );
		$list  = empty( $named ) ? $last : implode( ', ', $named ) . ' and ' . $last;

		return sprintf( 'Fits %d makes including %s', $total, $list ) . ( '' !== $range ? ', ' . $range : '' );
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
			if ( ! is_array( $vehicle ) || empty( $vehicle['make'] ) ) {
				continue;
			}
			$make = CSF_Parts_Vehicle_Names::make( (string) $vehicle['make'] );
			if ( ! in_array( $make, $makes, true ) ) {
				$makes[] = $make;
			}
		}

		return $makes;
	}
}
