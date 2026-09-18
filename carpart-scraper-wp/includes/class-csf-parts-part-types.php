<?php
/**
 * Part types: the six product lines the site talks about, mapped from the
 * scraped categories.
 *
 * The catalogue stores a dozen raw categories ("Radiator And A/C Condenser
 * Assembly", "Power Steering Cooler", …). Visitors filter by line
 * (Radiators, Condensers, Intercoolers, Inverter coolers, Transmission oil
 * coolers, Pressure caps); one-offs fold into the nearest line or Other.
 * Extend or override with the csf_parts_part_types filter.
 *
 * @package CSF_Parts_Catalog
 * @since   1.18.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

/**
 * Class CSF_Parts_Part_Types
 */
final class CSF_Parts_Part_Types {

	/** Query parameter carrying the chosen line. */
	public const PARAM = 'csf_type';

	public const OTHER = 'other';

	/**
	 * Lines in display order: slug => [label, singular, keyword patterns].
	 * The first line whose pattern matches a category claims it.
	 *
	 * @return array<string, array{label: string, singular: string, match: string}>
	 */
	public static function lines(): array {
		$lines = array(
			'pressure-caps'            => array( 'label' => 'Pressure caps', 'singular' => 'Pressure cap', 'match' => '/\b(radiator|pressure)\s*cap/i' ),
			'condensers'               => array( 'label' => 'Condensers', 'singular' => 'Condenser', 'match' => '/^(?!.*radiator).*condenser/i' ),
			'intercoolers'             => array( 'label' => 'Intercoolers', 'singular' => 'Intercooler', 'match' => '/intercooler|charge\s*air/i' ),
			'inverter-coolers'         => array( 'label' => 'Inverter coolers', 'singular' => 'Inverter cooler', 'match' => '/inverter|hybrid\s*cool/i' ),
			'transmission-oil-coolers' => array( 'label' => 'Transmission oil coolers', 'singular' => 'Transmission oil cooler', 'match' => '/transmission|trans\.?\s*oil/i' ),
			'radiators'                => array( 'label' => 'Radiators', 'singular' => 'Radiator', 'match' => '/radiator|cooling\s*module/i' ),
		);
		if ( function_exists( 'apply_filters' ) ) {
			$filtered = apply_filters( 'csf_parts_part_types', $lines );
			if ( is_array( $filtered ) && ! empty( $filtered ) ) {
				$lines = $filtered;
			}
		}
		// Display order (Other is always last).
		$order = array( 'radiators', 'condensers', 'intercoolers', 'inverter-coolers', 'transmission-oil-coolers', 'pressure-caps' );
		$rank = static function ( string $slug ) use ( $order ): int {
			$pos = array_search( $slug, $order, true );
			return false === $pos ? 99 : (int) $pos;
		};
		uksort( $lines, static fn( $a, $b ) => $rank( (string) $a ) <=> $rank( (string) $b ) );
		return $lines;
	}

	/**
	 * Label for a line slug (Other included).
	 *
	 * @param string $slug Line slug.
	 * @return string
	 */
	public static function label( string $slug ): string {
		if ( self::OTHER === $slug ) {
			return 'Other';
		}
		return self::lines()[ $slug ]['label'] ?? '';
	}

	/**
	 * Which line a raw category belongs to.
	 *
	 * Matching order is the precise lines first (caps, condensers, …) so
	 * "Radiator Cap" is a cap and "Radiator And A/C Condenser Assembly" is a
	 * radiator, not a condenser.
	 *
	 * @param string $category Raw category.
	 * @return string Line slug, or 'other'.
	 */
	public static function line_for_category( string $category ): string {
		$lines = self::lines();
		foreach ( array( 'pressure-caps', 'condensers', 'intercoolers', 'inverter-coolers', 'transmission-oil-coolers', 'radiators' ) as $slug ) {
			if ( isset( $lines[ $slug ] ) && preg_match( $lines[ $slug ]['match'], $category ) ) {
				return $slug;
			}
		}
		foreach ( $lines as $slug => $line ) {
			if ( preg_match( $line['match'], $category ) ) {
				return $slug;
			}
		}
		return self::OTHER;
	}

	/**
	 * Raw categories that make up a line.
	 *
	 * @param string   $slug       Line slug (or 'other').
	 * @param string[] $categories All raw categories in the catalogue.
	 * @return string[]
	 */
	public static function categories_for_line( string $slug, array $categories ): array {
		return array_values( array_filter( $categories, static fn( $category ) => self::line_for_category( (string) $category ) === $slug ) );
	}

	/**
	 * Chip data: slug => [label, count], in display order, only lines with parts.
	 *
	 * @param array<string, int> $category_counts Raw category => count.
	 * @return array<string, array{label: string, count: int}>
	 */
	public static function chips( array $category_counts ): array {
		$chips = array();
		foreach ( self::lines() as $slug => $line ) {
			$chips[ $slug ] = array( 'label' => $line['label'], 'count' => 0 );
		}
		$chips[ self::OTHER ] = array( 'label' => 'Other', 'count' => 0 );
		foreach ( $category_counts as $category => $count ) {
			$chips[ self::line_for_category( (string) $category ) ]['count'] += (int) $count;
		}
		return array_filter( $chips, static fn( $chip ) => $chip['count'] > 0 );
	}

	/**
	 * Whether a slug is a known line (or Other).
	 *
	 * @param string $slug Candidate.
	 * @return bool
	 */
	public static function is_valid( string $slug ): bool {
		return self::OTHER === $slug || array_key_exists( $slug, self::lines() );
	}

	/**
	 * Standard introduction paragraph for a line, from settings or the built-in copy.
	 *
	 * @param string $slug Line slug.
	 * @return string
	 */
	public static function intro( string $slug ): string {
		$saved = function_exists( 'get_option' ) ? get_option( CSF_Parts_Constants::OPTION_PART_TYPE_INTROS, array() ) : array();
		if ( is_array( $saved ) && ! empty( $saved[ $slug ] ) ) {
			return trim( (string) $saved[ $slug ] );
		}
		return self::default_intros()[ $slug ] ?? self::default_intros()[ self::OTHER ];
	}

	/**
	 * Built-in introduction copy per line.
	 *
	 * @return array<string, string>
	 */
	public static function default_intros(): array {
		return array(
			'radiators'                => 'Direct-fit replacement radiator with an aluminum core and tanks matched to the original, leak tested before it ships.',
			'condensers'               => 'Direct-fit replacement condenser with a parallel-flow aluminum core, sized and connected to match the original.',
			'intercoolers'             => 'Direct-fit replacement intercooler with an aluminum core built for higher heat rejection than the original.',
			'inverter-coolers'         => 'Direct-fit replacement inverter cooler for hybrid and electric vehicles, matched to the original mounting and connections.',
			'transmission-oil-coolers' => 'Direct-fit replacement transmission oil cooler with an aluminum core and fittings that match the original.',
			'pressure-caps'            => 'Replacement pressure cap matched to the system pressure of the original.',
			self::OTHER                => 'Direct-fit replacement matched to the mounting and connections of the original part.',
		);
	}
}
