<?php
/**
 * Unit tests for CSF_Parts_Part_Card.
 *
 * @package CSF_Parts_Catalog
 */

use PHPUnit\Framework\TestCase;
use Brain\Monkey;
use Brain\Monkey\Functions;

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
		$this->assertStringContainsString( '<span class="csf-part-card__badge">Radiator</span>', $html );
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
		$this->assertSame( '28 ½" × 20" × 2 ¼"', $dims );
		$this->assertNull( CSF_Parts_Part_Card::dimensions( $partial ) );
	}

	/**
	 * Makes are distinct and capped at four badges with a "+N" overflow badge.
	 */
	public function test_render_caps_make_badges_with_overflow(): void {
		// Arrange
		$rows = array();
		foreach ( array( 'Honda', 'Honda', 'Acura', 'Toyota', 'Ford', 'Mazda', 'Kia' ) as $make ) {
			$rows[] = array( 'make' => $make, 'model' => 'X' );
		}
		$part = $this->part( array( 'compatibility' => json_encode( $rows ) ) );

		// Act
		$html = CSF_Parts_Part_Card::render( $part, '/p' );

		// Assert
		$this->assertSame( 4, substr_count( $html, '<span class="csf-part-card__make-badge">' ) );
		$this->assertStringContainsString( 'csf-part-card__make-badge--more">+2<', $html );
	}
}
