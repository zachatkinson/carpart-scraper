<?php
/**
 * Unit tests for CSF_Parts_Block_Styles.
 *
 * @package CSF_Parts_Catalog
 */

use PHPUnit\Framework\TestCase;

require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-block-styles.php';

/**
 * Test block-level style resolution.
 */
final class BlockStylesTest extends TestCase {

	/**
	 * Unset card attributes emit nothing so tokens apply.
	 */
	public function test_card_style_vars_is_empty_when_nothing_set(): void {
		// Arrange
		$attributes = array( 'borderColor' => '', 'cardShadow' => 'bogus' );

		// Act
		$vars = CSF_Parts_Block_Styles::card_style_vars( $attributes );

		// Assert
		$this->assertSame( '', $vars );
	}

	/**
	 * Set card attributes become custom properties on the wrapper.
	 */
	public function test_card_style_vars_emits_only_set_values(): void {
		// Arrange
		$attributes = array( 'borderRadius' => 12, 'borderColor' => '#abcdef', 'cardShadow' => 'md' );

		// Act
		$vars = CSF_Parts_Block_Styles::card_style_vars( $attributes );

		// Assert
		$this->assertSame( '--csf-card-radius:12px;--csf-card-border-color:#abcdef;--csf-card-shadow:var(--csf-shadow-md);', $vars );
	}

	/**
	 * Legacy padding/margin apply only without core spacing and only when non-zero.
	 */
	public function test_legacy_spacing_yields_to_core_spacing(): void {
		// Arrange
		$legacy = array( 'blockPadding' => array( 'top' => 0, 'right' => 24, 'bottom' => 0, 'left' => 24 ) );
		$core   = $legacy + array( 'style' => array( 'spacing' => array( 'padding' => array( 'top' => '1rem' ) ) ) );
		$zero   = array( 'blockMargin' => array( 'top' => 0, 'right' => 0, 'bottom' => 0, 'left' => 0 ) );

		// Act & Assert
		$this->assertSame( 'padding:0px 24px 0px 24px;', CSF_Parts_Block_Styles::legacy_spacing_style( $legacy ) );
		$this->assertSame( '', CSF_Parts_Block_Styles::legacy_spacing_style( $core ) );
		$this->assertSame( '', CSF_Parts_Block_Styles::legacy_spacing_style( $zero ) );
	}

	/**
	 * Wrapper classes reflect scheme, hover, animation and visibility.
	 */
	public function test_wrapper_classes_cover_scheme_hover_animation_visibility(): void {
		// Arrange
		$attributes = array( 'colorScheme' => 'dark', 'hoverEffect' => 'zoom', 'scrollAnimation' => 'slideUp', 'hideOnMobile' => true, 'hideOnDesktop' => false );

		// Act
		$classes = CSF_Parts_Block_Styles::wrapper_classes( $attributes );

		// Assert
		$this->assertSame( 'csf-card-scheme-dark csf-hover-zoom csf-anim-slide-up csf-hide-mobile', $classes );
	}

	/**
	 * Default scheme adds no scheme class; unknown values are ignored.
	 */
	public function test_wrapper_classes_ignore_default_and_unknown_values(): void {
		// Arrange
		$attributes = array( 'colorScheme' => 'default', 'hoverEffect' => 'wobble', 'scrollAnimation' => 'none' );

		// Act
		$classes = CSF_Parts_Block_Styles::wrapper_classes( $attributes );

		// Assert
		$this->assertSame( '', $classes );
	}

	/**
	 * Per-instance CSS carries the responsive grid and aspect ratio, scoped by id.
	 */
	public function test_instance_css_scopes_grid_and_aspect_ratio(): void {
		// Arrange
		$attributes = array( 'columns' => array( 'desktop' => 4 ), 'gap' => array( 'mobile' => 8 ), 'imageAspectRatio' => '4/3' );

		// Act
		$css = CSF_Parts_Block_Styles::instance_css( 'csf-abc', $attributes );

		// Assert
		$this->assertStringContainsString( '#csf-abc .csf-grid-items{display:grid;gap:8px;grid-template-columns:repeat(2,1fr);}', $css );
		$this->assertStringContainsString( '@media (min-width:1024px){#csf-abc .csf-grid-items{gap:24px;grid-template-columns:repeat(4,1fr);}}', $css );
		$this->assertStringContainsString( '#csf-abc .csf-part-card__image{aspect-ratio:4/3;}', $css );
		$this->assertStringNotContainsString( 'auto', $css );
	}
}
