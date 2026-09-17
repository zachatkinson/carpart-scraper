<?php
/**
 * Visitor-facing sort options for the Product Catalog block.
 *
 * A short list of named sorts (the block's Sort By attribute stays the
 * editor-side default). Each maps to an orderby/order pair the database
 * layer already validates.
 *
 * @package CSF_Parts_Catalog
 * @since   1.14.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

/**
 * Class CSF_Parts_Catalog_Sort
 */
final class CSF_Parts_Catalog_Sort {

	/** Query parameter carrying the visitor's choice. */
	public const PARAM = 'csf_sort';

	/**
	 * Sort options in display order.
	 *
	 * @return array<string, array{label: string, orderby: string, order: string}>
	 */
	public static function options(): array {
		return array(
			'newest'   => array( 'label' => 'Newest first', 'orderby' => 'updated_at', 'order' => 'desc' ),
			'name'     => array( 'label' => 'Name A–Z', 'orderby' => 'name', 'order' => 'asc' ),
			'sku'      => array( 'label' => 'Part number', 'orderby' => 'sku', 'order' => 'asc' ),
			'category' => array( 'label' => 'Part type', 'orderby' => 'category', 'order' => 'asc' ),
		);
	}

	/**
	 * Whether a key names a known sort.
	 *
	 * @param string $key Candidate key.
	 * @return bool
	 */
	public static function is_valid( string $key ): bool {
		return array_key_exists( $key, self::options() );
	}

	/**
	 * Orderby/order pair for a key.
	 *
	 * @param string $key Sort key.
	 * @return array{orderby: string, order: string}|null Null for unknown keys.
	 */
	public static function resolve( string $key ): ?array {
		$options = self::options();
		if ( ! isset( $options[ $key ] ) ) {
			return null;
		}
		return array( 'orderby' => $options[ $key ]['orderby'], 'order' => $options[ $key ]['order'] );
	}

	/**
	 * Key whose pair matches the given orderby/order, or '' when none does.
	 *
	 * Used to pre-select the visitor control from the block's default sort.
	 *
	 * @param string $orderby Column.
	 * @param string $order   asc|desc.
	 * @return string
	 */
	public static function key_for( string $orderby, string $order ): string {
		foreach ( self::options() as $key => $option ) {
			if ( $option['orderby'] === $orderby && $option['order'] === strtolower( $order ) ) {
				return $key;
			}
		}
		return '';
	}
}
