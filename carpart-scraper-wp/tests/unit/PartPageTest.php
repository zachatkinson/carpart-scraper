<?php
/**
 * Unit tests for CSF_Parts_Part_Page.
 *
 * @package CSF_Parts_Catalog
 */

use PHPUnit\Framework\TestCase;

require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-part-card.php';
require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-part-page.php';

/**
 * Test the part page view model.
 */
final class PartPageTest extends TestCase {

	private function part( array $overrides = array() ): object {
		return (object) array_merge( array( 'sku' => 'CSF-4037', 'category' => 'Radiator', 'compatibility' => '' ), $overrides );
	}

	public function test_eyebrow_and_title_use_category_construction_and_fitment(): void {
		// Arrange
		$rows = json_encode( array(
			array( 'year' => 2024, 'make' => 'Toyota', 'model' => 'Tacoma', 'engine' => '2.4L L4 turbo' ),
			array( 'year' => 2026, 'make' => 'Toyota', 'model' => 'Tacoma', 'engine' => '2.4L L4 turbo' ),
		) );
		$part  = $this->part( array( 'compatibility' => $rows ) );
		$specs = array( 'Construction' => 'PLASTIC-TANK ALUMINUM' );

		// Act & Assert
		$this->assertSame( 'Radiator · Plastic-tank Aluminum · CSF 4037', CSF_Parts_Part_Page::eyebrow( $part, $specs ) );
		$this->assertSame( 'Radiator for 2024 to 2026 Toyota Tacoma, 2.4L L4 turbo', CSF_Parts_Part_Page::title( $part ) );
		$this->assertSame( 'Radiator CSF 4037', CSF_Parts_Part_Page::title( $this->part() ) );
	}

	public function test_fitment_rows_group_by_vehicle_and_engine_with_year_ranges(): void {
		// Arrange
		$compat = array(
			array( 'year' => 2006, 'make' => 'Chevrolet', 'model' => 'Colorado', 'engine' => '2.9L L4' ),
			array( 'year' => 2004, 'make' => 'Chevrolet', 'model' => 'Colorado', 'engine' => '2.9L L4' ),
			array( 'year' => 2005, 'make' => 'Chevrolet', 'model' => 'Colorado', 'engine' => '2.9L L4' ),
			array( 'year' => 2005, 'make' => 'Chevrolet', 'model' => 'Colorado', 'engine' => '3.7L L5', 'qualifiers' => array( 'Z71' ) ),
			array( 'year' => 2004, 'make' => 'Gmc', 'model' => 'Canyon', 'engine' => '2.9L L4' ),
		);

		// Act
		$rows = CSF_Parts_Part_Page::fitment_rows( $compat );

		// Assert
		$this->assertCount( 3, $rows );
		$this->assertSame( array( 'Chevrolet', 'Colorado', '2004, 2005, 2006', '2.9L L4', '' ), array( $rows[0]['make'], $rows[0]['model'], $rows[0]['years_text'], $rows[0]['engine'], $rows[0]['notes'] ) );
		$this->assertSame( 'Z71', $rows[1]['notes'] );
		$this->assertSame( 'Gmc', $rows[2]['make'] );
		$this->assertSame( '2 makes · 2 models · 3 model years · 2 engines', CSF_Parts_Part_Page::fitment_counts( $rows ) );
	}

	public function test_year_ranges_collapse_long_runs_only(): void {
		$this->assertSame( '2004–2012', CSF_Parts_Part_Page::year_ranges( range( 2004, 2012 ) ) );
		$this->assertSame( '2024, 2025, 2026', CSF_Parts_Part_Page::year_ranges( array( 2024, 2025, 2026 ) ) );
		$this->assertSame( '1998, 1999, 2003–2007', CSF_Parts_Part_Page::year_ranges( array( 1998, 1999, 2003, 2004, 2005, 2006, 2007 ) ) );
	}

	public function test_row_matches_visitor_vehicle(): void {
		// Arrange
		$row = array( 'make' => 'Toyota', 'model' => 'Tacoma', 'years' => array( 2024, 2025 ), 'engine' => '', 'notes' => '', 'years_text' => '' );

		// Act & Assert
		$this->assertTrue( CSF_Parts_Part_Page::row_matches( $row, '2025', 'toyota', 'TACOMA' ) );
		$this->assertTrue( CSF_Parts_Part_Page::row_matches( $row, '', 'Toyota', 'Tacoma' ) );
		$this->assertFalse( CSF_Parts_Part_Page::row_matches( $row, '2020', 'Toyota', 'Tacoma' ) );
		$this->assertFalse( CSF_Parts_Part_Page::row_matches( $row, '2025', '', '' ) );
	}

	public function test_spec_groups_route_known_keys_and_keep_the_rest(): void {
		// Arrange
		$specs = array(
			'10589'               => 'A/C Condenser',
			'Box Height (in)'     => '23',
			'Box Length (in)'     => '29 1/7',
			'Box Width (in)'      => '5 1/3',
			'Box Weight (lbs)'    => '8',
			'Construction'        => 'parallel flow',
			'Core Length (in)'    => '20 (in)',
			'Core Thickness (in)' => '5/8 (in)',
			'Core Width (in)'     => '17 3/4 (in)',
			'Hazardous Material'  => 'No',
			'Inlet Tube'          => 'Block Fitting',
			'Outlet Tube'         => 'Block Fitting',
			'Fin Density'         => '18 fpi',
		);

		// Act
		$groups = CSF_Parts_Part_Page::spec_groups( $specs );

		// Assert
		$this->assertSame( array( 'Core' => '20 × 17 3/4 × 5/8 in', 'Inlet' => 'Block Fitting', 'Outlet' => 'Block Fitting' ), $groups['key'] );
		$this->assertSame( array( 'Overall' => '29 1/7 × 5 1/3 × 23 in', 'Core length' => '20 in', 'Core width' => '17 3/4 in', 'Core thickness' => '5/8 in', 'Weight' => '8 lb' ), $groups['dimensions'] );
		$this->assertSame( array( 'Core' => 'Parallel Flow', 'Hazardous material' => 'No' ), $groups['construction'] );
		$this->assertSame( array( 'Fin density' => '18 fpi' ), $groups['more'] );
	}

	public function test_cta_url_fills_placeholders(): void {
		$this->assertSame( 'https://x.test/contact/?part=CSF-4037&d=CSF%204037', CSF_Parts_Part_Page::cta_url( 'https://x.test/contact/?part={sku}&d={sku_display}', 'CSF-4037' ) );
		$this->assertSame( '', CSF_Parts_Part_Page::cta_url( '  ', 'CSF-4037' ) );
	}
}
