<?php
/**
 * Unit tests for CSF_Parts_Design.
 *
 * Covers preset resolution, override precedence, sanitisation, and the
 * inline CSS contract that the asset loader relies on.
 *
 * @package CSF_Parts_Catalog
 */

use PHPUnit\Framework\TestCase;

require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-design.php';

/**
 * Test design tokens and presets.
 */
final class DesignTest extends TestCase {

	/**
	 * Every preset only sets tokens that exist in the catalogue.
	 */
	public function test_presets_only_reference_known_tokens(): void {
		// Arrange
		$known = array_keys( CSF_Parts_Design::tokens() );

		foreach ( CSF_Parts_Design::presets() as $id => $preset ) {
			foreach ( array( 'light', 'dark' ) as $scheme ) {
				// Act
				$unknown = array_diff( array_keys( $preset[ $scheme ] ), $known );

				// Assert
				$this->assertSame( array(), array_values( $unknown ), "Preset {$id} ({$scheme}) sets unknown tokens" );
			}
		}
	}

	/**
	 * The default preset applies nothing, so existing sites are unchanged.
	 */
	public function test_default_settings_produce_no_css(): void {
		// Arrange
		$settings = CSF_Parts_Design::default_settings();

		// Act
		$css = CSF_Parts_Design::build_css( $settings, CSF_Parts_Constants::COLOR_SCHEME_AUTO );

		// Assert
		$this->assertSame( '', $css );
	}

	/**
	 * An override beats the preset value for the same token.
	 */
	public function test_override_beats_preset(): void {
		// Arrange
		$settings = array(
			'preset'    => 'csf-red',
			'overrides' => array( 'primary' => '#123456' ),
		);

		// Act
		$resolved = CSF_Parts_Design::resolve( $settings );

		// Assert
		$this->assertSame( '#123456', $resolved['light']['primary'] );
		$this->assertSame( '#2D3748', $resolved['light']['secondary'] );
	}

	/**
	 * Brand overrides carry into dark mode; surface overrides do not.
	 */
	public function test_brand_overrides_apply_to_dark_but_surfaces_do_not(): void {
		// Arrange
		$settings = array(
			'preset'    => 'csf-red',
			'overrides' => array(
				'primary' => '#ABCDEF',
				'surface' => '#111111',
			),
		);

		// Act
		$resolved = CSF_Parts_Design::resolve( $settings );

		// Assert
		$this->assertSame( '#ABCDEF', $resolved['dark']['primary'] );
		$this->assertArrayNotHasKey( 'surface', $resolved['dark'] );
	}

	/**
	 * Dark declarations are media-gated for the automatic scheme, bare for
	 * dark-only, and omitted for light-only.
	 */
	public function test_build_css_gates_dark_block_by_scheme(): void {
		// Arrange
		$settings = array( 'preset' => 'csf-red', 'overrides' => array() );

		// Act
		$auto  = CSF_Parts_Design::build_css( $settings, CSF_Parts_Constants::COLOR_SCHEME_AUTO );
		$dark  = CSF_Parts_Design::build_css( $settings, CSF_Parts_Constants::COLOR_SCHEME_DARK );
		$light = CSF_Parts_Design::build_css( $settings, CSF_Parts_Constants::COLOR_SCHEME_LIGHT );

		// Assert
		$this->assertStringContainsString( '@media (prefers-color-scheme: dark){:root{--csf-primary:#F05252;', $auto );
		$this->assertStringNotContainsString( '@media', $dark );
		$this->assertStringContainsString( '--csf-primary:#F05252;', $dark );
		$this->assertStringNotContainsString( '#F05252', $light );
		$this->assertStringStartsWith( ':root{--csf-primary:#CF2E2E;', $light );
	}

	/**
	 * Invalid colours, oversized lengths, unknown tokens and presets are rejected.
	 */
	public function test_sanitize_settings_drops_invalid_input(): void {
		// Arrange
		$raw = array(
			'preset'    => 'not-a-preset',
			'overrides' => array(
				'primary'   => 'red',
				'secondary' => '#abc',
				'radius-lg' => '999px',
				'radius-sm' => '6',
				'bogus'     => '#000000',
			),
		);

		// Act
		$clean = CSF_Parts_Design::sanitize_settings( $raw );

		// Assert
		$this->assertSame( CSF_Parts_Constants::DESIGN_PRESET_DEFAULT, $clean['preset'] );
		$this->assertEqualsCanonicalizing(
			array(
				'secondary' => '#ABC',
				'radius-lg' => '64px',
				'radius-sm' => '6px',
			),
			$clean['overrides']
		);
	}
}
