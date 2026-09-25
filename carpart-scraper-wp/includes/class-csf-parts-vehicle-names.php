<?php
/**
 * Human casing for makes, models and engines.
 *
 * The scraper title-cases everything ("Gmc", "Tt Quattro", "2.4L L4 2393cc").
 * These helpers turn that into how people write it ("GMC", "TT Quattro",
 * "2.4 L turbo"). Overrides can be extended with the csf_parts_vehicle_name_overrides filter.
 *
 * @package CSF_Parts_Catalog
 * @since   1.17.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

/**
 * Class CSF_Parts_Vehicle_Names
 */
final class CSF_Parts_Vehicle_Names {

	/**
	 * Lowercase stored make => display form, for names the word rules get wrong:
	 * initialisms, mixed-case brands and hyphenated names. Extend with the
	 * csf_parts_vehicle_make_overrides filter.
	 */
	private const MAKE_OVERRIDES = array(
		'bmw'           => 'BMW',
		'gmc'           => 'GMC',
		'mini'          => 'MINI',
		'vw'            => 'VW',
		'infiniti'      => 'INFINITI',
		'am general'    => 'AM General',
		'mercedes-benz' => 'Mercedes-Benz',
		'mercedes benz' => 'Mercedes-Benz',
		'mclaren'       => 'McLaren',
		'rolls-royce'   => 'Rolls-Royce',
		'rolls royce'   => 'Rolls-Royce',
		'delorean'      => 'DeLorean',
	);

	/** Lowercase token => display form. Applies to makes and model tokens. */
	private const OVERRIDES = array(
		'gmc'        => 'GMC',
		'bmw'        => 'BMW',
		'mini'       => 'MINI',
		'vw'         => 'VW',
		'kia'        => 'Kia',
		'ram'        => 'Ram',
		'fiat'       => 'Fiat',
		'mercedes'   => 'Mercedes',
		'benz'       => 'Benz',
		'rav4'       => 'RAV4',
		'4runner'    => '4Runner',
		'cr-v'       => 'CR-V',
		'hr-v'       => 'HR-V',
		'cx-5'       => 'CX-5',
		'cx-9'       => 'CX-9',
		'mx-5'       => 'MX-5',
		'e-tron'     => 'e-tron',
		'i3'         => 'i3',
		'i4'         => 'i4',
		'i8'         => 'i8',
		'ix'         => 'iX',
		'gti'        => 'GTI',
		'gli'        => 'GLI',
		'gt'         => 'GT',
		'tt'         => 'TT',
		'cc'         => 'CC',
		'id.4'       => 'ID.4',
		'sl'         => 'SL',
		'slk'        => 'SLK',
		'clk'        => 'CLK',
		'amg'        => 'AMG',
		'suv'        => 'SUV',
		'ev'         => 'EV',
		'phev'       => 'PHEV',
		'hd'         => 'HD',
		'srt'        => 'SRT',
		'zr2'        => 'ZR2',
		'z71'        => 'Z71',
		'trd'        => 'TRD',
		'xse'        => 'XSE',
		'sxt'        => 'SXT',
		'ecoboost'   => 'EcoBoost',
		'powerstroke' => 'Power Stroke',
	);

	/**
	 * Display form of a make.
	 *
	 * @param string $make Stored make.
	 * @return string
	 */
	public static function make( string $make ): string {
		$key       = strtolower( trim( preg_replace( '/\s+/', ' ', $make ) ?? $make ) );
		$overrides = self::make_overrides();
		return $overrides[ $key ] ?? self::words( $make );
	}

	/**
	 * Display form of a model.
	 *
	 * @param string $model Stored model.
	 * @return string
	 */
	public static function model( string $model ): string {
		return self::words( $model );
	}

	/**
	 * Short engine description for headings: "2.4 L turbo".
	 *
	 * Litres with a space; displacement in cc dropped when litres are known;
	 * turbo / supercharged / diesel / hybrid appended when the data says so.
	 * Falls back to the stored string when no litres are found.
	 *
	 * @param string $engine     Stored engine, e.g. "2.4L L4 2393cc".
	 * @param string $aspiration Stored aspiration, e.g. "Turbocharged".
	 * @return string
	 */
	public static function engine_short( string $engine, string $aspiration = '' ): string {
		$parsed = self::parse_engine( $engine, $aspiration );
		if ( null === $parsed['litres'] ) {
			return trim( $engine );
		}
		return trim( $parsed['litres'] . ' L' . $parsed['qualifier'] );
	}

	/**
	 * Detailed engine description for tables: "2.4 L L4 turbo, 2393 cc".
	 *
	 * @param string $engine     Stored engine.
	 * @param string $aspiration Stored aspiration.
	 * @return string
	 */
	public static function engine_detailed( string $engine, string $aspiration = '' ): string {
		$parsed = self::parse_engine( $engine, $aspiration );
		if ( null === $parsed['litres'] ) {
			return trim( $engine );
		}
		$out = $parsed['litres'] . ' L';
		if ( '' !== $parsed['cylinders'] ) {
			$out .= ' ' . $parsed['cylinders'];
		}
		$out .= $parsed['qualifier'];
		if ( '' !== $parsed['cc'] ) {
			$out .= ', ' . $parsed['cc'] . ' cc';
		}
		return $out;
	}

	/**
	 * Break an engine string into litres, cylinder layout, cc and a qualifier.
	 *
	 * @param string $engine     Stored engine.
	 * @param string $aspiration Stored aspiration.
	 * @return array{litres: string|null, cylinders: string, cc: string, qualifier: string}
	 */
	private static function parse_engine( string $engine, string $aspiration ): array {
		$litres = preg_match( '/(\d+(?:\.\d+)?)\s*L\b/i', $engine, $m ) ? $m[1] : null;
		$cyl    = preg_match( '/\b([VLIHWB]\d{1,2}|Flat-?\d)\b/i', $engine, $m ) ? strtoupper( $m[1] ) : '';
		$cc     = preg_match( '/(\d{3,5})\s*cc\b/i', $engine, $m ) ? $m[1] : '';
		$text   = strtolower( $engine . ' ' . $aspiration );
		$qual   = '';
		if ( preg_match( '/turbo/', $text ) ) {
			$qual .= ' turbo';
		} elseif ( preg_match( '/supercharg/', $text ) ) {
			$qual .= ' supercharged';
		}
		if ( preg_match( '/diesel|tdi|duramax|power ?stroke|cummins/', $text ) ) {
			$qual .= ' diesel';
		}
		if ( preg_match( '/hybrid/', $text ) ) {
			$qual .= ' hybrid';
		}
		if ( preg_match( '/electric|\bev\b/', $text ) && null === $litres ) {
			$qual .= ' electric';
		}
		return array( 'litres' => $litres, 'cylinders' => $cyl, 'cc' => $cc, 'qualifier' => $qual );
	}

	/**
	 * Case each word of a name.
	 *
	 * @param string $name Stored name.
	 * @return string
	 */
	private static function words( string $name ): string {
		$overrides = self::overrides();
		$tokens    = preg_split( '/\s+/', trim( $name ) ) ?: array();
		foreach ( $tokens as &$token ) {
			$key = strtolower( $token );
			if ( isset( $overrides[ $key ] ) ) {
				$token = $overrides[ $key ];
			} elseif ( preg_match( '/^i\d+[a-z]{0,2}$/i', $token ) ) {
				$token = 'i' . strtolower( substr( $token, 1 ) ); // BMW i3, i3s, i4, i8
			} elseif ( preg_match( '/^[a-z]{1,3}$/i', $token ) ) {
				$token = strtoupper( $token ); // TT, CC, RS, XL
			} elseif ( preg_match( '/^[a-z]{1,2}\d{1,3}[a-z]{0,2}$/i', $token ) ) {
				$token = strtoupper( $token ); // Q5, X5, RS3, E350, S4
			} elseif ( preg_match( '/^[a-z]{1,2}-[a-z]{1,2}$/i', $token ) ) {
				$token = strtoupper( $token ); // CR-V, HR-V
			} elseif ( preg_match( '/^[a-z]-\d{2,4}$/i', $token ) ) {
				$token = strtoupper( $token ); // F-150, I-280
			} else {
				// Case each hyphenated segment: "mercedes-benz" → "Mercedes-Benz".
				$token = implode( '-', array_map( static fn( string $s ): string => ucfirst( strtolower( $s ) ), explode( '-', $token ) ) );
			}
		}
		unset( $token );
		return implode( ' ', $tokens );
	}

	/**
	 * Whole-make override map, filterable.
	 *
	 * @return array<string, string>
	 */
	private static function make_overrides(): array {
		$map = self::MAKE_OVERRIDES;
		if ( function_exists( 'apply_filters' ) ) {
			$filtered = apply_filters( 'csf_parts_vehicle_make_overrides', $map );
			if ( is_array( $filtered ) ) {
				$map = $filtered;
			}
		}
		return $map;
	}

	/**
	 * Override map, filterable.
	 *
	 * @return array<string, string>
	 */
	private static function overrides(): array {
		$map = self::OVERRIDES;
		if ( function_exists( 'apply_filters' ) ) {
			$filtered = apply_filters( 'csf_parts_vehicle_name_overrides', $map );
			if ( is_array( $filtered ) ) {
				$map = $filtered;
			}
		}
		return $map;
	}
}
