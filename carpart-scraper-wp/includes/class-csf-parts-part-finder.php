<?php
/**
 * Part Finder block: attribute normalisation and text helpers.
 *
 * Kept separate from render.php so the pure parts can be unit tested.
 *
 * @package CSF_Parts_Catalog
 * @since   1.11.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

/**
 * Class CSF_Parts_Part_Finder
 */
final class CSF_Parts_Part_Finder {

	/** Query parameters the Product Catalog block understands. */
	public const FILTER_PARAMS = array( 'csf_search', 'csf_year', 'csf_make', 'csf_model' );

	/**
	 * Normalise block attributes into a typed array with defaults.
	 *
	 * @param array<string, mixed> $attributes Raw block attributes.
	 * @return array<string, mixed>
	 */
	public static function from_attributes( array $attributes ): array {
		$level = (int) ( $attributes['headingLevel'] ?? 2 );

		return array(
			'eyebrow'            => trim( (string) ( $attributes['eyebrow'] ?? 'Find your part' ) ),
			'heading'            => trim( (string) ( $attributes['heading'] ?? 'Search by vehicle or number' ) ),
			'heading_level'      => min( 6, max( 1, $level ) ),
			'show_search'        => (bool) ( $attributes['showSearch'] ?? true ),
			'search_placeholder' => (string) ( $attributes['searchPlaceholder'] ?? 'CSF, OEM or Partslink number' ),
			'show_year'          => (bool) ( $attributes['showYear'] ?? true ),
			'show_make'          => (bool) ( $attributes['showMake'] ?? true ),
			'show_model'         => (bool) ( $attributes['showModel'] ?? true ),
			'button_text'        => (string) ( $attributes['buttonText'] ?? 'Show parts' ),
			'target_url'         => trim( (string) ( $attributes['targetUrl'] ?? '' ) ),
			'show_footnote'      => (bool) ( $attributes['showFootnote'] ?? true ),
			'footnote_text'      => (string) ( $attributes['footnoteText'] ?? '{count} parts in the catalogue.' ),
		);
	}

	/**
	 * Flatten lookup rows ({year, count} / {make, count} objects or arrays) to
	 * a list of distinct scalar option values, preserving order.
	 *
	 * @param array<int, mixed> $rows  Rows from the database lookups.
	 * @param string            $field Field holding the value ('year' or 'make').
	 * @return array<int, string>
	 */
	public static function option_values( array $rows, string $field ): array {
		$values = array();
		foreach ( $rows as $row ) {
			if ( is_object( $row ) ) {
				$value = $row->{$field} ?? null;
			} elseif ( is_array( $row ) ) {
				$value = $row[ $field ] ?? null;
			} else {
				$value = $row;
			}
			$value = trim( (string) $value );
			if ( '' !== $value && '0' !== $value && ! in_array( $value, $values, true ) ) {
				$values[] = $value;
			}
		}
		return $values;
	}

	/**
	 * Substitute {count} in the footnote template.
	 *
	 * @param string $template Footnote text with optional {count}.
	 * @param int    $count    Number of parts.
	 * @return string
	 */
	public static function footnote( string $template, int $count ): string {
		$formatted = function_exists( 'number_format_i18n' ) ? number_format_i18n( $count ) : number_format( $count );
		return trim( str_replace( '{count}', $formatted, $template ) );
	}

	/**
	 * Build the destination URL the form would produce, for a set of filters.
	 *
	 * Empty values are dropped so the URL carries only chosen filters.
	 *
	 * @param string                $base    Parts page URL.
	 * @param array<string, string> $filters Filter name => value.
	 * @return string
	 */
	public static function build_url( string $base, array $filters ): string {
		$query = array();
		foreach ( self::FILTER_PARAMS as $param ) {
			$value = trim( (string) ( $filters[ $param ] ?? '' ) );
			if ( '' !== $value ) {
				$query[ $param ] = $value;
			}
		}
		if ( empty( $query ) ) {
			return $base;
		}
		$separator = false === strpos( $base, '?' ) ? '?' : '&';
		return $base . $separator . http_build_query( $query );
	}
}
