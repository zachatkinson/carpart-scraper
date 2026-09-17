<?php
/**
 * Unit tests for CSF_Parts_Part_Finder.
 *
 * @package CSF_Parts_Catalog
 */

use PHPUnit\Framework\TestCase;

require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-part-finder.php';

/**
 * Test the part finder helpers.
 */
final class PartFinderTest extends TestCase {

	/**
	 * Defaults fill in and the heading level is clamped.
	 */
	public function test_from_attributes_applies_defaults_and_clamps_heading(): void {
		// Arrange
		$attributes = array( 'headingLevel' => 9, 'eyebrow' => '  ' );

		// Act
		$finder = CSF_Parts_Part_Finder::from_attributes( $attributes );

		// Assert
		$this->assertSame( 6, $finder['heading_level'] );
		$this->assertSame( '', $finder['eyebrow'] );
		$this->assertSame( 'Show parts', $finder['button_text'] );
		$this->assertTrue( $finder['show_model'] );
	}

	/**
	 * The footnote substitutes the formatted count.
	 */
	public function test_footnote_substitutes_count(): void {
		// Act
		$text = CSF_Parts_Part_Finder::footnote( '{count} parts in the catalogue.', 1759 );

		// Assert
		$this->assertSame( '1,759 parts in the catalogue.', $text );
	}

	/**
	 * Only chosen filters end up in the destination URL.
	 */
	public function test_build_url_drops_empty_filters_and_unknown_keys(): void {
		// Arrange
		$filters = array( 'csf_year' => '2015', 'csf_make' => '', 'csf_model' => ' F-150 ', 'csf_search' => '', 'evil' => 'x' );

		// Act
		$url = CSF_Parts_Part_Finder::build_url( 'https://example.com/parts/', $filters );

		// Assert
		$this->assertSame( 'https://example.com/parts/?csf_year=2015&csf_model=F-150', $url );
		$this->assertSame( 'https://example.com/parts/', CSF_Parts_Part_Finder::build_url( 'https://example.com/parts/', array() ) );
		$this->assertSame( 'https://example.com/p?x=1&csf_search=CSF-3000', CSF_Parts_Part_Finder::build_url( 'https://example.com/p?x=1', array( 'csf_search' => 'CSF-3000' ) ) );
	}

	/**
	 * Lookup rows (objects with counts) flatten to distinct scalar options.
	 */
	public function test_option_values_flattens_rows_and_dedupes(): void {
		// Arrange
		$rows = array(
			(object) array( 'year' => 2020, 'count' => 5 ),
			(object) array( 'year' => 2019, 'count' => 2 ),
			array( 'year' => '2020' ),
			(object) array( 'year' => 0 ),
			'2018',
		);

		// Act
		$years = CSF_Parts_Part_Finder::option_values( $rows, 'year' );

		// Assert
		$this->assertSame( array( '2020', '2019', '2018' ), $years );
	}
}
