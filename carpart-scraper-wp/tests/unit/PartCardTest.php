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
		$this->assertSame( '2006 to 2018 Audi A3 Quattro, TT Quattro, Volkswagen Passat and others', $summary );
	}
}
