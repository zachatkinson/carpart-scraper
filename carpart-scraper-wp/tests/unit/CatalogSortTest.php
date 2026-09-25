<?php
/**
 * Unit tests for CSF_Parts_Catalog_Sort and the SKU display helper.
 *
 * @package CSF_Parts_Catalog
 */

use PHPUnit\Framework\TestCase;

require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-catalog-sort.php';

/**
 * Test visitor sort options.
 */
final class CatalogSortTest extends TestCase {

	/**
	 * Keys resolve to whitelisted orderby/order pairs and round-trip via key_for().
	 */
	public function test_resolve_and_key_for_round_trip(): void {
		foreach ( CSF_Parts_Catalog_Sort::options() as $key => $option ) {
			// Act
			$pair = CSF_Parts_Catalog_Sort::resolve( $key );

			// Assert
			$this->assertSame( array( 'orderby' => $option['orderby'], 'order' => $option['order'] ), $pair );
			$this->assertSame( $key, CSF_Parts_Catalog_Sort::key_for( $option['orderby'], strtoupper( $option['order'] ) ) );
		}
		$this->assertNull( CSF_Parts_Catalog_Sort::resolve( 'bogus' ) );
		$this->assertFalse( CSF_Parts_Catalog_Sort::is_valid( 'bogus' ) );
		$this->assertSame( '', CSF_Parts_Catalog_Sort::key_for( 'created_at', 'asc' ) );
		$this->assertSame( 'newest', CSF_Parts_Catalog_Sort::key_for( 'updated_at', 'desc' ), 'Blocks defaulting to updated_at still pre-select Newest first' );
		$this->assertSame( 'newest', CSF_Parts_Catalog_Sort::key_for( 'created_at', 'desc' ) );
	}

	/**
	 * SKUs display as "CSF 3680" whatever the stored form.
	 */
	public function test_sku_display_inserts_brand_space(): void {
		$this->assertSame( 'CSF 3680', csf_format_sku_display( 'CSF-3680' ) );
		$this->assertSame( 'CSF 3680', csf_format_sku_display( 'csf3680' ) );
		$this->assertSame( 'CSF 3680', csf_format_sku_display( 'CSF 3680' ) );
	}
}
