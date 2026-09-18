<?php
/**
 * Unit tests for CSF_Parts_Part_Types.
 *
 * @package CSF_Parts_Catalog
 */

use PHPUnit\Framework\TestCase;
use Brain\Monkey;
use Brain\Monkey\Functions;

require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-part-types.php';

/**
 * Test category → product line mapping.
 */
final class PartTypesTest extends TestCase {

	protected function setUp(): void {
		parent::setUp();
		Monkey\setUp();
		Functions\when( 'get_option' )->justReturn( array() );
	}

	protected function tearDown(): void {
		Monkey\tearDown();
		parent::tearDown();
	}

	/**
	 * The catalogue's raw categories fold into the six lines or Other.
	 */
	public function test_raw_categories_map_to_lines(): void {
		$expected = array(
			'Radiator'                            => 'radiators',
			'Radiator And A/C Condenser Assembly' => 'radiators',
			'Cooling Module'                      => 'radiators',
			'A/C Condenser'                       => 'condensers',
			'Intercooler'                         => 'intercoolers',
			'Inverter Cooler'                     => 'inverter-coolers',
			'Automatic Transmission Oil Cooler'   => 'transmission-oil-coolers',
			'Radiator Cap'                        => 'pressure-caps',
			'Engine Oil Cooler'                   => 'other',
			'Fuel Cooler'                         => 'other',
			'Power Steering Cooler'               => 'other',
		);
		foreach ( $expected as $category => $line ) {
			$this->assertSame( $line, CSF_Parts_Part_Types::line_for_category( $category ), $category );
		}
	}

	/**
	 * Chips sum counts per line, keep display order, and drop empty lines.
	 */
	public function test_chips_sum_counts_in_display_order(): void {
		// Arrange
		$counts = array( 'A/C Condenser' => 575, 'Radiator' => 986, 'Radiator And A/C Condenser Assembly' => 3, 'Radiator Cap' => 8, 'Engine Oil Cooler' => 2, 'Fuel Cooler' => 1 );

		// Act
		$chips = CSF_Parts_Part_Types::chips( $counts );

		// Assert
		$this->assertSame( array( 'radiators', 'condensers', 'pressure-caps', 'other' ), array_keys( $chips ) );
		$this->assertSame( 989, $chips['radiators']['count'] );
		$this->assertSame( 3, $chips['other']['count'] );
		$this->assertSame( array( 'Radiator', 'Radiator And A/C Condenser Assembly' ), CSF_Parts_Part_Types::categories_for_line( 'radiators', array_keys( $counts ) ) );
	}

	/**
	 * Every line has built-in intro copy and Other is the fallback.
	 */
	public function test_intros_cover_every_line(): void {
		foreach ( array_keys( CSF_Parts_Part_Types::lines() ) as $slug ) {
			$this->assertNotSame( '', CSF_Parts_Part_Types::intro( $slug ), $slug );
		}
		$this->assertSame( CSF_Parts_Part_Types::default_intros()['other'], CSF_Parts_Part_Types::intro( 'nonsense' ) );
		$this->assertTrue( CSF_Parts_Part_Types::is_valid( 'other' ) );
		$this->assertFalse( CSF_Parts_Part_Types::is_valid( 'nonsense' ) );
	}
}
