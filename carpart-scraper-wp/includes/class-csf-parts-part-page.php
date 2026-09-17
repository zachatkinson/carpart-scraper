<?php
/**
 * Part page view model.
 *
 * Pure helpers that turn a part row into the pieces the single-part template
 * renders: eyebrow line, descriptive title, fitment table rows, grouped
 * specifications, CTA URLs. No WordPress calls except escaping in the
 * template, so everything here is unit-testable.
 *
 * @package CSF_Parts_Catalog
 * @since   1.15.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

/**
 * Class CSF_Parts_Part_Page
 */
final class CSF_Parts_Part_Page {

	/** Consecutive-year runs longer than this collapse to "2004–2012". */
	private const RANGE_MIN_RUN = 4;

	/**
	 * Eyebrow line: "Radiator · Parallel Flow · CSF 4037".
	 *
	 * @param object               $part  Part row.
	 * @param array<string, mixed> $specs Decoded specifications.
	 * @return string
	 */
	public static function eyebrow( object $part, array $specs ): string {
		$pieces = array();
		if ( ! empty( $part->category ) ) {
			$pieces[] = (string) $part->category;
		}
		$construction = self::spec_value( $specs, array( 'Construction' ) );
		if ( null !== $construction ) {
			$pieces[] = ucwords( strtolower( $construction ) );
		}
		$pieces[] = csf_format_sku_display( (string) $part->sku );

		return implode( ' · ', $pieces );
	}

	/**
	 * Descriptive title: "Radiator for 2024 to 2026 Toyota Tacoma, 2.4L L4 turbo".
	 *
	 * Falls back to the SKU when there is no compatibility data.
	 *
	 * @param object $part Part row.
	 * @return string
	 */
	public static function title( object $part ): string {
		$summary  = CSF_Parts_Part_Card::fitment_summary( (string) ( $part->compatibility ?? '' ) );
		$category = trim( (string) ( $part->category ?? '' ) );
		if ( '' === $summary ) {
			return '' !== $category ? $category . ' ' . csf_format_sku_display( (string) $part->sku ) : csf_format_sku_display( (string) $part->sku );
		}
		return ( '' !== $category ? $category : 'Part' ) . ' for ' . $summary;
	}

	/**
	 * Fitment rows for the table: one per make/model/engine, years collapsed.
	 *
	 * @param array<int, array<string, mixed>> $compatibility Decoded compatibility rows.
	 * @return array<int, array{make: string, model: string, years: int[], years_text: string, engine: string, notes: string}>
	 */
	public static function fitment_rows( array $compatibility ): array {
		$groups = array();
		foreach ( $compatibility as $vehicle ) {
			if ( ! is_array( $vehicle ) || empty( $vehicle['make'] ) ) {
				continue;
			}
			$make   = trim( (string) $vehicle['make'] );
			$model  = trim( (string) ( $vehicle['model'] ?? '' ) );
			$engine = trim( (string) ( $vehicle['engine'] ?? '' ) );
			$notes  = array();
			$aspiration = trim( (string) ( $vehicle['aspiration'] ?? '' ) );
			if ( '' !== $aspiration && 0 !== strcasecmp( 'None', $aspiration ) ) {
				$notes[] = $aspiration;
			}
			$submodel = trim( (string) ( $vehicle['submodel'] ?? '' ) );
			if ( '' !== $submodel ) {
				$notes[] = $submodel;
			}
			foreach ( (array) ( $vehicle['qualifiers'] ?? array() ) as $qualifier ) {
				$qualifier = trim( (string) $qualifier );
				if ( '' !== $qualifier ) {
					$notes[] = $qualifier;
				}
			}
			$key = strtolower( $make . '|' . $model . '|' . $engine . '|' . implode( '|', $notes ) );
			if ( ! isset( $groups[ $key ] ) ) {
				$groups[ $key ] = array(
					'make'   => $make,
					'model'  => $model,
					'years'  => array(),
					'engine' => $engine,
					'notes'  => implode( ', ', array_unique( $notes ) ),
				);
			}
			if ( ! empty( $vehicle['year'] ) ) {
				$groups[ $key ]['years'][] = (int) $vehicle['year'];
			}
		}

		$rows = array_values( $groups );
		foreach ( $rows as &$row ) {
			$row['years'] = array_values( array_unique( $row['years'] ) );
			sort( $row['years'] );
			$row['years_text'] = self::year_ranges( $row['years'] );
		}
		unset( $row );

		usort(
			$rows,
			static function ( array $a, array $b ): int {
				return strcasecmp( $a['make'], $b['make'] )
					?: strcasecmp( $a['model'], $b['model'] )
					?: ( ( $a['years'][0] ?? 0 ) <=> ( $b['years'][0] ?? 0 ) )
					?: strcasecmp( $a['engine'], $b['engine'] );
			}
		);

		return $rows;
	}

	/**
	 * Collapse years: "2024, 2025, 2026" (short runs) or "2004–2012" (4+ consecutive).
	 *
	 * @param int[] $years Sorted, unique years.
	 * @return string
	 */
	public static function year_ranges( array $years ): string {
		if ( empty( $years ) ) {
			return '';
		}
		$ranges = array();
		$start  = $years[0];
		$end    = $years[0];
		$flush  = static function () use ( &$ranges, &$start, &$end ): void {
			$ranges[] = ( $end - $start + 1 ) >= self::RANGE_MIN_RUN ? $start . '–' . $end : implode( ', ', range( $start, $end ) );
		};
		for ( $i = 1, $n = count( $years ); $i < $n; $i++ ) {
			if ( $years[ $i ] === $end + 1 ) {
				$end = $years[ $i ];
				continue;
			}
			$flush();
			$start = $years[ $i ];
			$end   = $years[ $i ];
		}
		$flush();

		return implode( ', ', $ranges );
	}

	/**
	 * "1 make · 1 model · 3 model years · 1 engine".
	 *
	 * @param array<int, array<string, mixed>> $rows Rows from fitment_rows().
	 * @return string
	 */
	public static function fitment_counts( array $rows ): string {
		$makes = array();
		$models = array();
		$years = array();
		$engines = array();
		foreach ( $rows as $row ) {
			$makes[ strtolower( $row['make'] ) ]                          = true;
			$models[ strtolower( $row['make'] . '|' . $row['model'] ) ]   = true;
			foreach ( $row['years'] as $year ) {
				$years[ $year ] = true;
			}
			if ( '' !== $row['engine'] ) {
				$engines[ strtolower( $row['engine'] ) ] = true;
			}
		}
		$pieces = array(
			self::plural( count( $makes ), 'make', 'makes' ),
			self::plural( count( $models ), 'model', 'models' ),
			self::plural( count( $years ), 'model year', 'model years' ),
		);
		if ( ! empty( $engines ) ) {
			$pieces[] = self::plural( count( $engines ), 'engine', 'engines' );
		}
		return implode( ' · ', $pieces );
	}

	/**
	 * Whether a row is the visitor's vehicle (from the URL).
	 *
	 * @param array<string, mixed> $row   Fitment row.
	 * @param string               $year  Searched year or ''.
	 * @param string               $make  Searched make or ''.
	 * @param string               $model Searched model or ''.
	 * @return bool
	 */
	public static function row_matches( array $row, string $year, string $make, string $model ): bool {
		if ( '' === $make || '' === $model ) {
			return false;
		}
		if ( 0 !== strcasecmp( $row['make'], $make ) || 0 !== strcasecmp( $row['model'], $model ) ) {
			return false;
		}
		return '' === $year || in_array( (int) $year, $row['years'], true );
	}

	/**
	 * Group specifications for the page.
	 *
	 * Returns four ordered label => value maps: key (the card beside the
	 * gallery), dimensions, construction, and more (everything unclaimed).
	 * Values are plain strings; the template formats fractions.
	 *
	 * @param array<string, mixed> $specs Decoded specifications.
	 * @return array{key: array<string, string>, dimensions: array<string, string>, construction: array<string, string>, more: array<string, string>}
	 */
	public static function spec_groups( array $specs ): array {
		$used = array();
		$take = static function ( array $names ) use ( $specs, &$used ): ?string {
			foreach ( $names as $name ) {
				foreach ( $specs as $key => $value ) {
					if ( 0 === strcasecmp( (string) $key, $name ) && '' !== trim( (string) $value ) ) {
						$used[ (string) $key ] = true;
						return trim( (string) $value );
					}
				}
			}
			return null;
		};
		$inches = static function ( ?string $value ): ?string {
			return null === $value ? null : trim( preg_replace( '/\s*\(in\)\s*$/i', '', $value ) );
		};

		$core_l = $inches( $take( array( 'Core Length (in)', 'Core Length' ) ) );
		$core_w = $inches( $take( array( 'Core Width (in)', 'Core Width' ) ) );
		$core_t = $inches( $take( array( 'Core Thickness (in)', 'Core Thickness' ) ) );
		$box_l  = $inches( $take( array( 'Box Length (in)', 'Length (in)', 'Overall Length (in)' ) ) );
		$box_w  = $inches( $take( array( 'Box Width (in)', 'Width (in)', 'Overall Width (in)' ) ) );
		$box_h  = $inches( $take( array( 'Box Height (in)', 'Height (in)', 'Overall Height (in)' ) ) );
		$weight = $take( array( 'Box Weight (lbs)', 'Weight (lbs)', 'Weight' ) );

		$key = array();
		if ( $core_l && $core_w && $core_t ) {
			$key['Core'] = sprintf( '%s × %s × %s in', $core_l, $core_w, $core_t );
		}
		$rows = $take( array( 'Number of Rows', '# of Rows', 'Rows', 'Row Count', 'No. Of Rows' ) );
		if ( null !== $rows ) {
			$key['Rows'] = $rows;
		}
		foreach ( array( 'Inlet', 'Outlet' ) as $port ) {
			$value = $take( array( $port . ' Size', $port . ' Tube', $port ) );
			if ( null === $value ) {
				$len = $inches( $take( array( $port . ' Length (in)' ) ) );
				$wid = $inches( $take( array( $port . ' Width (in)' ) ) );
				$value = $len && $wid ? $len . ' × ' . $wid . ' in' : ( $len ?: $wid );
			}
			if ( null !== $value && '' !== $value ) {
				$key[ $port ] = ucwords( strtolower( $value ) );
			}
		}
		$tank = $take( array( 'Tank Material' ) );
		if ( null !== $tank ) {
			$key['Tank material'] = ucwords( strtolower( $tank ) );
		}
		$trans = $take( array( 'Transmission Cooler', 'Trans Oil Cooler', 'Transmission Oil Cooler', 'Oil Cooler' ) );
		if ( null !== $trans ) {
			$key['Transmission cooler'] = ucwords( strtolower( $trans ) );
		}

		$dimensions = array();
		if ( $box_l && $box_w && $box_h ) {
			$dimensions['Overall'] = sprintf( '%s × %s × %s in', $box_l, $box_w, $box_h );
		}
		if ( $core_l ) {
			$dimensions['Core length'] = $core_l . ' in';
		}
		if ( $core_w ) {
			$dimensions['Core width'] = $core_w . ' in';
		}
		if ( $core_t ) {
			$dimensions['Core thickness'] = $core_t . ' in';
		}
		if ( null !== $weight ) {
			$dimensions['Weight'] = preg_match( '/[a-z]/i', $weight ) ? $weight : $weight . ' lb';
		}

		$construction = array();
		$core_type = $take( array( 'Construction', 'Core Type', 'Core' ) );
		if ( null !== $core_type ) {
			$construction['Core'] = ucwords( strtolower( $core_type ) );
		}
		if ( null !== $tank ) {
			$construction['Tanks'] = ucwords( strtolower( $tank ) );
		}
		foreach ( array( 'Fin type' => array( 'Fin Type', 'Fins' ), 'Flow' => array( 'Flow', 'Flow Type', 'Flow Direction', 'Cross-flow/Down-flow' ), 'Pressure cap' => array( 'Pressure Cap', 'Cap' ), 'Warranty' => array( 'Warranty' ), 'Hazardous material' => array( 'Hazardous Material' ) ) as $label => $names ) {
			$value = $take( $names );
			if ( null !== $value ) {
				$construction[ $label ] = ucwords( strtolower( $value ) );
			}
		}

		$more = array();
		foreach ( $specs as $spec_key => $value ) {
			$spec_key = (string) $spec_key;
			if ( isset( $used[ $spec_key ] ) || preg_match( '/^(CSF-?)?\d+$/', $spec_key ) || '' === trim( (string) $value ) ) {
				continue;
			}
			$more[ ucfirst( strtolower( str_replace( '_', ' ', $spec_key ) ) ) ] = trim( (string) $value );
		}

		return compact( 'key', 'dimensions', 'construction', 'more' );
	}

	/**
	 * Fill a URL template: {sku} → stored SKU, {sku_display} → "CSF 3680".
	 *
	 * @param string $template URL with optional placeholders.
	 * @param string $sku      Stored SKU.
	 * @return string Empty when the template is empty.
	 */
	public static function cta_url( string $template, string $sku ): string {
		$template = trim( $template );
		if ( '' === $template ) {
			return '';
		}
		return str_replace(
			array( '{sku}', '{sku_display}' ),
			array( rawurlencode( $sku ), rawurlencode( csf_format_sku_display( $sku ) ) ),
			$template
		);
	}

	/**
	 * First spec value matching any of the names (case-insensitive), or null.
	 *
	 * @param array<string, mixed> $specs Specifications.
	 * @param string[]             $names Candidate keys.
	 * @return string|null
	 */
	private static function spec_value( array $specs, array $names ): ?string {
		foreach ( $names as $name ) {
			foreach ( $specs as $key => $value ) {
				if ( 0 === strcasecmp( (string) $key, $name ) && '' !== trim( (string) $value ) ) {
					return trim( (string) $value );
				}
			}
		}
		return null;
	}

	/**
	 * "3 model years".
	 *
	 * @param int    $count    Count.
	 * @param string $singular Singular noun.
	 * @param string $plural   Plural noun.
	 * @return string
	 */
	private static function plural( int $count, string $singular, string $plural ): string {
		return $count . ' ' . ( 1 === $count ? $singular : $plural );
	}
}
