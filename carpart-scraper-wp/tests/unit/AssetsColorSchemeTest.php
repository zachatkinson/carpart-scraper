<?php
/**
 * Unit tests for the color-scheme behaviour of CSF_Parts_Assets.
 *
 * The "Color scheme" setting decides whether the dark palette stylesheet is
 * loaded, and with which <link media> attribute. These tests pin that contract.
 *
 * @package CSF_Parts_Catalog
 */

use PHPUnit\Framework\TestCase;

require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-customizer.php';
require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-assets.php';

/**
 * Test color scheme resolution.
 */
final class AssetsColorSchemeTest extends TestCase {

	/**
	 * Automatic scheme follows the visitor's OS preference via a media query.
	 */
	public function test_auto_scheme_loads_dark_stylesheet_for_dark_preference_only(): void {
		// Arrange
		$scheme = CSF_Parts_Constants::COLOR_SCHEME_AUTO;

		// Act
		$media = CSF_Parts_Assets::get_dark_stylesheet_media( $scheme );

		// Assert
		$this->assertSame( '(prefers-color-scheme: dark)', $media );
	}

	/**
	 * Light-only scheme never loads the dark stylesheet.
	 */
	public function test_light_scheme_skips_dark_stylesheet(): void {
		// Arrange
		$scheme = CSF_Parts_Constants::COLOR_SCHEME_LIGHT;

		// Act
		$media = CSF_Parts_Assets::get_dark_stylesheet_media( $scheme );

		// Assert
		$this->assertNull( $media );
	}

	/**
	 * Dark-only scheme loads the dark stylesheet unconditionally.
	 */
	public function test_dark_scheme_loads_dark_stylesheet_for_all_media(): void {
		// Arrange
		$scheme = CSF_Parts_Constants::COLOR_SCHEME_DARK;

		// Act
		$media = CSF_Parts_Assets::get_dark_stylesheet_media( $scheme );

		// Assert
		$this->assertSame( 'all', $media );
	}

	/**
	 * Unknown values fall back to the default (automatic) scheme.
	 */
	public function test_sanitize_color_scheme_rejects_unknown_values(): void {
		// Arrange
		$unknown = 'blue';

		// Act
		$result = CSF_Parts_Assets::sanitize_color_scheme( $unknown );

		// Assert
		$this->assertSame( CSF_Parts_Constants::COLOR_SCHEME_DEFAULT, $result );
	}

	/**
	 * Every declared scheme survives sanitization unchanged.
	 */
	public function test_sanitize_color_scheme_preserves_valid_values(): void {
		foreach ( CSF_Parts_Constants::COLOR_SCHEMES as $scheme ) {
			// Act
			$result = CSF_Parts_Assets::sanitize_color_scheme( $scheme );

			// Assert
			$this->assertSame( $scheme, $result );
		}
	}

	/**
	 * The dark stylesheet exists and carries no media query of its own,
	 * since the <link media> attribute is what gates it.
	 */
	public function test_dark_stylesheet_has_no_embedded_color_scheme_media_query(): void {
		// Arrange
		$path = CSF_PARTS_PLUGIN_DIR . 'public/css/csf-color-system-dark.css';

		// Act
		$css = file_get_contents( $path );
		// Strip comments so documentation mentions of the query don't count.
		$rules = preg_replace( '#/\*.*?\*/#s', '', $css );

		// Assert
		$this->assertFileExists( $path );
		$this->assertStringNotContainsString( 'prefers-color-scheme', $rules );
		$this->assertStringContainsString( '--csf-bg: #1d2327', $rules );
	}

	/**
	 * The base color system no longer switches on its own.
	 */
	public function test_base_stylesheet_has_no_color_scheme_media_query(): void {
		// Arrange
		$path = CSF_PARTS_PLUGIN_DIR . 'public/css/csf-color-system.css';

		// Act
		$rules = preg_replace( '#/\*.*?\*/#s', '', file_get_contents( $path ) );

		// Assert
		$this->assertStringNotContainsString( 'prefers-color-scheme', $rules );
	}
}
