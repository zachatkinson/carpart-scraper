<?php
/**
 * The "current part" for part blocks.
 *
 * The URL handler sets the view for the part being rendered; part blocks read
 * it. In the block editor (or on a page with no part) a sample part is used so
 * the layout can be previewed.
 *
 * @package CSF_Parts_Catalog
 * @since   1.16.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

/**
 * Class CSF_Parts_Part_Context
 */
final class CSF_Parts_Part_Context {

	/** @var array<string, mixed>|null */
	private static ?array $view = null;

	/** @var array<string, mixed>|null|false Cached sample; false = none available. */
	private static $sample = null;

	/**
	 * Set the part view for the current request.
	 *
	 * @param array<string, mixed> $view View built by CSF_Parts_Part_Page::build_view().
	 */
	public static function set( array $view ): void {
		self::$view = $view;
	}

	/** Forget the current part. */
	public static function clear(): void {
		self::$view = null;
	}

	/**
	 * The part view for the current request, or null when none is set.
	 *
	 * @return array<string, mixed>|null
	 */
	public static function get(): ?array {
		return self::$view;
	}

	/**
	 * The current part, falling back to a sample part outside part pages.
	 *
	 * @return array<string, mixed>|null
	 */
	public static function current(): ?array {
		if ( null !== self::$view ) {
			return self::$view;
		}
		return self::sample();
	}

	/**
	 * A representative part (recently updated, with images when possible) for previews.
	 *
	 * @return array<string, mixed>|null
	 */
	public static function sample(): ?array {
		if ( null !== self::$sample ) {
			return false === self::$sample ? null : self::$sample;
		}
		if ( ! class_exists( 'CSF_Parts_Database' ) ) {
			self::$sample = false;
			return null;
		}
		$database = new CSF_Parts_Database();
		$result   = $database->query_parts( array( 'orderby' => 'latest', 'order' => 'desc' ), 8, 1 );
		$parts    = $result['parts'] ?? array();
		if ( empty( $parts ) ) {
			self::$sample = false;
			return null;
		}
		$chosen = $parts[0];
		foreach ( $parts as $part ) {
			if ( ! empty( $part->images ) && '[]' !== $part->images && ! empty( $part->specifications ) ) {
				$chosen = $part;
				break;
			}
		}
		self::$sample = CSF_Parts_Part_Page::build_view( $chosen, '', '', '', $database );
		return self::$sample;
	}
}
