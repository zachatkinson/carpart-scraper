<?php
/**
 * Unit tests for CSF_Parts_Part_Card.
 *
 * @package CSF_Parts_Catalog
 */

use PHPUnit\Framework\TestCase;
use Brain\Monkey;
use Brain\Monkey\Functions;

require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-vehicle-names.php';
require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-part-card.php';

/**
 * Test the shared part card renderer.
 */
final class PartCardTest extends TestCase {

	protected function setUp(): void {
		parent::setUp();
		Monkey\setUp();
		Functions\when( 'esc_html' )->returnArg();
		Functions\when( 'esc_attr' )->returnArg();
		Functions\when( 'esc_url' )->returnArg();
		Functions\when( 'esc_html_e' )->alias( static function ( $text ) { echo $text; } );
		Functions\when( 'wp_kses' )->returnArg();
		Functions\when( 'home_url' )->returnArg();
	}

	protected function tearDown(): void {
		Monkey\tearDown();
		parent::tearDown();
	}

	/**
	 * Build a part row.
	 *
	 * @param array<string, mixed> $overrides Field overrides.
	 * @return object
	 */
	private function part( array $overrides = array() ): object {
		return (object) array_merge(
			array(
				'sku'            => 'CSF-3000',
				'category'       => 'Radiator',
				'images'         => '',
				'specifications' => '',
				'compatibility'  => '',
			),
			$overrides
		);
	}

	/**
	 * A part with no image, specs or fitment renders a placeholder card.
	 */
	public function test_render_minimal_part_uses_placeholder_and_badge(): void {
		// Arrange
		$part = $this->part();

		// Act
		$html = CSF_Parts_Part_Card::render( $part, 'https://example.com/parts/csf3000' );

		// Assert
		$this->assertStringContainsString( '<article class="csf-part-card">', $html );
		$this->assertStringContainsString( 'csf-part-card__image--placeholder', $html );
		$this->assertMatchesRegularExpression( '#<p class="csf-part-card__badge">Radiator</p>\s*<h3 class="csf-part-card__title">#', $html );
		$this->assertStringNotContainsString( 'csf-fitment-section', $html );
		$this->assertStringNotContainsString( 'style=', $html );
	}

	/**
	 * The product photo (second image) is preferred over the drawing.
	 */
	public function test_primary_image_prefers_second_image(): void {
		// Arrange
		$json = wp_json_encode( array( array( 'url' => '/a.jpg' ), '/b.jpg' ) );

		// Act
		$url = CSF_Parts_Part_Card::primary_image( $json );

		// Assert
		$this->assertStringEndsWith( '/b.jpg', (string) $url );
		$this->assertNull( CSF_Parts_Part_Card::primary_image( '[]' ) );
	}

	/**
	 * Dimensions need all three box measures and get typographic fractions.
	 */
	public function test_dimensions_require_all_three_and_format_fractions(): void {
		// Arrange
		$full    = json_encode( array( 'Box Length (in)' => '28 1/2', 'Box Width (in)' => '20', 'Box Height (in)' => '2 1/4' ) );
		$partial = json_encode( array( 'Box Length (in)' => '28' ) );

		// Act
		$dims = CSF_Parts_Part_Card::dimensions( $full );

		// Assert
		$this->assertSame( '28 ½ × 20 × 2 ¼ in', $dims );
		$this->assertNull( CSF_Parts_Part_Card::dimensions( $partial ) );
	}

	/**
	 * Makes are distinct and capped at four badges with a "+N" overflow badge.
	 */
	public function test_render_caps_make_badges_with_overflow(): void {
		// Arrange
		$rows = array();
		foreach ( array( 'Honda', 'HONDA', 'honda', 'Acura', 'Toyota', 'Ford', 'Mazda', 'Kia' ) as $make ) { // casing variants must dedupe
			$rows[] = array( 'make' => $make, 'model' => 'X' );
		}
		$part = $this->part( array( 'compatibility' => json_encode( $rows ) ) );

		// Act
		$html = CSF_Parts_Part_Card::render( $part, '/p' );

		// Assert
		$this->assertSame( 4, substr_count( $html, '<span class="csf-part-card__make-badge">' ) );
		$this->assertStringContainsString( 'csf-part-card__make-badge--more">+2<', $html );
	}

	/**
	 * Fitment summary: year range, vehicles grouped by make, single engine appended.
	 */
	public function test_fitment_summary_builds_range_vehicles_and_engine(): void {
		// Arrange
		$rows = json_encode( array(
			array( 'year' => 2024, 'make' => 'Toyota', 'model' => 'Tacoma', 'engine' => '2.4L L4 turbo' ),
			array( 'year' => 2026, 'make' => 'Toyota', 'model' => 'Tacoma', 'engine' => '2.4L L4 turbo' ),
			array( 'year' => 2025, 'make' => 'Toyota', 'model' => 'Tacoma', 'engine' => '2.4L L4 turbo' ),
		) );
		$mixed = json_encode( array(
			array( 'year' => 2004, 'make' => 'Chevrolet', 'model' => 'Colorado', 'engine' => '2.9L' ),
			array( 'year' => 2006, 'make' => 'Gmc', 'model' => 'Canyon', 'engine' => '3.7L' ),
		) );

		// Act & Assert
		$this->assertSame( '2024 to 2026 Toyota Tacoma, 2.4 L turbo', CSF_Parts_Part_Card::fitment_summary( $rows ) );
		$this->assertSame( '2004 to 2006 Chevrolet Colorado, GMC Canyon', CSF_Parts_Part_Card::fitment_summary( $mixed ) );
		$this->assertSame( '', CSF_Parts_Part_Card::fitment_summary( '' ) );
	}

	/**
	 * Meta line joins dimensions and the OEM number, tolerating either being absent.
	 */
	public function test_meta_line_prefers_oem_reference(): void {
		// Arrange
		$part = $this->part( array(
			'specifications'      => json_encode( array( 'Box Length (in)' => '31', 'Box Width (in)' => '21', 'Box Height (in)' => '4' ) ),
			'interchange_numbers' => json_encode( array(
				array( 'reference_type' => 'Partslink', 'reference_number' => 'TO3010367' ),
				array( 'reference_type' => 'OEM', 'reference_number' => '16400-AK030' ),
			) ),
		) );
		$no_dims = $this->part( array( 'interchange_numbers' => json_encode( array( array( 'reference_type' => 'DPI', 'reference_number' => '3014' ) ) ) ) );

		// Act & Assert
		$this->assertSame( '31 × 21 × 4 in · OE 16400-AK030', CSF_Parts_Part_Card::meta_line( $part ) );
		$this->assertSame( 'OE 3014', CSF_Parts_Part_Card::meta_line( $no_dims ) );
		$this->assertSame( '', CSF_Parts_Part_Card::meta_line( $this->part() ) );
	}

	/**
	 * The New badge respects the window and can be switched off.
	 */
	public function test_is_new_honours_window(): void {
		// Arrange
		$recent = gmdate( 'Y-m-d H:i:s', time() - 5 * DAY_IN_SECONDS );
		$old    = gmdate( 'Y-m-d H:i:s', time() - 90 * DAY_IN_SECONDS );

		// Act & Assert
		$this->assertTrue( CSF_Parts_Part_Card::is_new( $recent, 30 ) );
		$this->assertFalse( CSF_Parts_Part_Card::is_new( $old, 30 ) );
		$this->assertFalse( CSF_Parts_Part_Card::is_new( $recent, 0 ) );
	}

	/**
	 * Updated parts get an Updated badge; New wins when both apply; old parts get none.
	 */
	public function test_activity_badge_distinguishes_new_from_updated(): void {
		// Arrange
		$recent = gmdate( 'Y-m-d H:i:s', time() - 5 * DAY_IN_SECONDS );
		$old    = gmdate( 'Y-m-d H:i:s', time() - 90 * DAY_IN_SECONDS );

		// Act & Assert
		$this->assertSame( 'new', CSF_Parts_Part_Card::activity_badge( $this->part( array( 'created_at' => $recent, 'updated_at' => $recent ) ), 30 ) );
		$this->assertSame( 'updated', CSF_Parts_Part_Card::activity_badge( $this->part( array( 'created_at' => $old, 'updated_at' => $recent ) ), 30 ) );
		$this->assertSame( '', CSF_Parts_Part_Card::activity_badge( $this->part( array( 'created_at' => $old, 'updated_at' => $old ) ), 30 ) );
		$this->assertSame( '', CSF_Parts_Part_Card::activity_badge( $this->part( array( 'created_at' => $recent, 'updated_at' => $recent ) ), 0 ) );

		$html = CSF_Parts_Part_Card::render( $this->part( array( 'created_at' => $old, 'updated_at' => $recent ) ), '/p' );
		$this->assertStringContainsString( 'csf-part-card__new--updated', $html );
		$this->assertStringContainsString( '>Updated<', $html );
	}

	/**
	 * Render options control the badge and summary lines.
	 */
	public function test_render_honours_options(): void {
		// Arrange
		$part = $this->part( array(
			'created_at'    => gmdate( 'Y-m-d H:i:s' ),
			'compatibility' => json_encode( array( array( 'year' => 2020, 'make' => 'Honda', 'model' => 'Civic' ) ) ),
		) );

		// Act
		$default = CSF_Parts_Part_Card::render( $part, '/p' );
		$quiet   = CSF_Parts_Part_Card::render( $part, '/p', array( 'new_badge_days' => 0, 'show_fitment_line' => false ) );

		// Assert
		$this->assertStringContainsString( 'csf-part-card__new', $default );
		$this->assertStringContainsString( '2020 Honda Civic', $default );
		$this->assertStringNotContainsString( 'csf-part-card__new', $quiet );
		$this->assertStringNotContainsString( 'csf-part-card__fitment', $quiet );
	}

	/**
	 * Long fitment lists are capped and end with "and others"; makes/models get human casing.
	 */
	public function test_fitment_summary_caps_vehicles_and_cases_names(): void {
		// Arrange
		$rows = json_encode( array(
			array( 'year' => 2006, 'make' => 'Audi', 'model' => 'A3 Quattro' ),
			array( 'year' => 2018, 'make' => 'Audi', 'model' => 'Tt Quattro' ),
			array( 'year' => 2010, 'make' => 'Volkswagen', 'model' => 'Passat' ),
			array( 'year' => 2010, 'make' => 'Volkswagen', 'model' => 'Cc' ),
			array( 'year' => 2010, 'make' => 'Volkswagen', 'model' => 'Golf' ),
		) );

		// Act
		$summary = CSF_Parts_Part_Card::fitment_summary( $rows );

		// Assert
		// Equal model-years, so makes then models are alphabetical.
		$this->assertSame( '2006 to 2018 Audi A3 Quattro, TT Quattro, Volkswagen CC and others', $summary );
	}

	/**
	 * The vehicle with the most model-years leads, even when stored later.
	 */
	public function test_fitment_summary_leads_with_most_model_years(): void {
		// Arrange
		$rows = json_encode( array(
			array( 'year' => 2019, 'make' => 'Acura', 'model' => 'ILX' ),
			array( 'year' => 2018, 'make' => 'Honda', 'model' => 'Accord' ),
			array( 'year' => 2016, 'make' => 'Honda', 'model' => 'Civic' ),
			array( 'year' => 2017, 'make' => 'Honda', 'model' => 'Civic' ),
			array( 'year' => 2020, 'make' => 'Honda', 'model' => 'Civic' ),
		) );

		// Act
		$summary = CSF_Parts_Part_Card::fitment_summary( $rows );

		// Assert
		$this->assertSame( '2016 to 2020 Honda Civic, Accord, Acura ILX', $summary );
	}

	/**
	 * With a context, matching vehicles lead and set the year range; the rest become "and others".
	 */
	public function test_fitment_summary_with_context_leads_with_matching_vehicles(): void {
		// Arrange: CSF 2276, light-duty vans stored first.
		$rows = array();
		foreach ( array( 'E-150 Econoline', 'E-150 Econoline Club Wagon', 'E-250 Econoline', 'E-350 Econoline' ) as $model ) {
			foreach ( range( 1992, 1996 ) as $year ) {
				$rows[] = array( 'year' => $year, 'make' => 'Ford', 'model' => $model, 'engine' => '5.8L V8' );
			}
		}
		$rows[]  = array( 'year' => 1996, 'make' => 'Ford', 'model' => 'Econoline Super Duty', 'engine' => '5.8L V8' );
		$json    = json_encode( $rows );
		$context = array( 'makes' => array( 'Ford' ), 'models' => array( 'E-350 Econoline', 'Econoline Super Duty', 'F-350' ) );

		// Act
		$scoped   = CSF_Parts_Part_Card::fitment_summary( $json, $context );
		$unscoped = CSF_Parts_Part_Card::fitment_summary( $json );

		// Assert
		$this->assertSame( '1992 to 1996 Ford E-350 Econoline, Econoline Super Duty and others, 5.8 L', $scoped );
		$this->assertSame( '1992 to 1996 Ford E-150 Econoline, E-150 Econoline Club Wagon, E-250 Econoline and others, 5.8 L', $unscoped );
	}

	/**
	 * A year in the context picks the vehicles that fit it, and the range spans all their years.
	 */
	public function test_fitment_summary_context_year_selects_vehicles_but_keeps_their_range(): void {
		// Arrange: CSF 4013 fits three Transits 2015-2019 and the HD only from 2020.
		$rows = array();
		foreach ( array( 'Transit-150', 'Transit-250', 'Transit-350' ) as $model ) {
			foreach ( range( 2015, 2019 ) as $year ) {
				$rows[] = array( 'year' => $year, 'make' => 'Ford', 'model' => $model, 'engine' => '3.5L V6 3496cc' );
			}
		}
		$rows[] = array( 'year' => 2020, 'make' => 'Ford', 'model' => 'Transit-350 Hd', 'engine' => '3.5L V6 3496cc' );
		$json   = json_encode( $rows );

		// Act
		$summary  = CSF_Parts_Part_Card::fitment_summary( $json, array( 'makes' => array( 'ford' ), 'years' => array( '2015' ) ) );
		$one_van  = CSF_Parts_Part_Card::fitment_summary( $json, array( 'makes' => array( 'Ford' ), 'models' => array( 'Transit-250' ), 'years' => array( 2015 ) ) );

		// Assert
		$this->assertSame( '2015 to 2019 Ford Transit-150, Transit-250, Transit-350 and others, 3.5 L', $summary );
		$this->assertSame( '2015 to 2019 Ford Transit-250 and others, 3.5 L', $one_van );
	}

	/**
	 * A part fitting many makes is described by breadth unless a context narrows it.
	 */
	public function test_fitment_summary_uses_breadth_for_many_makes(): void {
		// Arrange: a universal cap; Ford has the most model-years.
		$rows = array(
			array( 'year' => 1988, 'make' => 'Acura', 'model' => 'Cl' ),
			array( 'year' => 2014, 'make' => 'Acura', 'model' => 'Tl' ),
			array( 'year' => 1990, 'make' => 'Chevrolet', 'model' => 'W4500 Tiltmaster' ),
			array( 'year' => 1991, 'make' => 'Chevrolet', 'model' => 'W4500 Tiltmaster' ),
			array( 'year' => 1992, 'make' => 'Chevrolet', 'model' => 'W5500 Tiltmaster' ),
			array( 'year' => 1970, 'make' => 'Ford', 'model' => 'F-250' ),
			array( 'year' => 1971, 'make' => 'Ford', 'model' => 'F-250' ),
			array( 'year' => 1972, 'make' => 'Ford', 'model' => 'F-250' ),
			array( 'year' => 2001, 'make' => 'Ford', 'model' => 'E-350 Super Duty' ),
			array( 'year' => 2001, 'make' => 'Gmc', 'model' => 'W4500' ),
			array( 'year' => 2001, 'make' => 'Toyota', 'model' => 'Tacoma' ),
		);
		$json = json_encode( $rows );

		// Act
		$breadth = CSF_Parts_Part_Card::fitment_summary( $json );
		$ford    = CSF_Parts_Part_Card::fitment_summary( $json, array( 'makes' => array( 'Ford' ) ) );
		$no_hit  = CSF_Parts_Part_Card::fitment_summary( $json, array( 'makes' => array( 'Honda' ) ) );

		// Assert
		$this->assertSame( 'Fits 5 makes including Ford, Chevrolet and Acura, 1970 to 2014', $breadth );
		$this->assertSame( '1970 to 2001 Ford F-250, E-350 Super Duty and others', $ford );
		$this->assertSame( $breadth, $no_hit ); // a context that matches nothing falls back
		$this->assertSame( 'Fits 5 makes including Chevrolet, Acura and GMC, 1988 to 2014', CSF_Parts_Part_Card::fitment_summary( $json, array( 'makes' => array( 'Chevrolet', 'Acura', 'Gmc', 'Toyota' ) ) ) ); // a context this wide is breadth too
	}

	/**
	 * The card takes the context as a render option, and it is derived from query filters.
	 */
	public function test_render_uses_fitment_context_option(): void {
		// Arrange
		$part = $this->part( array(
			'compatibility' => json_encode( array(
				array( 'year' => 2004, 'make' => 'Chevrolet', 'model' => 'Colorado' ),
				array( 'year' => 2006, 'make' => 'Gmc', 'model' => 'Canyon' ),
			) ),
		) );
		$context = CSF_Parts_Part_Card::context_from_filters( array( 'makes' => array( 'Gmc' ), 'years' => array( 2006, '', 2006 ), 'orderby' => 'sku' ) );

		// Act
		$html = CSF_Parts_Part_Card::render( $part, '/p', array( 'fitment_context' => $context ) );

		// Assert
		$this->assertSame( array( 'makes' => array( 'Gmc' ), 'models' => array(), 'years' => array( '2006' ) ), $context );
		$this->assertStringContainsString( '2006 GMC Canyon and others', $html );
	}
}
