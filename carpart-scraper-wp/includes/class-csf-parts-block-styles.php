<?php
/**
 * Block-level style resolution for the Product Catalog block.
 *
 * Turns block attributes into (a) CSS custom properties on the block wrapper
 * so the stylesheet stays the single implementation of card styling, and
 * (b) the small per-instance CSS that genuinely varies per block (grid
 * columns and gaps per breakpoint, image aspect ratio).
 *
 * Wrapper padding/margin/colour/typography come from WordPress core block
 * supports; the legacy blockPadding/blockMargin attributes are honoured only
 * when the core spacing style is absent, so old content keeps rendering.
 *
 * All methods are static and pure so they can be unit tested without WordPress.
 *
 * @package CSF_Parts_Catalog
 * @since   1.10.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

/**
 * Class CSF_Parts_Block_Styles
 */
final class CSF_Parts_Block_Styles {

	/** Shadow attribute value => token. */
	private const SHADOWS = array(
		'none' => 'none',
		'sm'   => 'var(--csf-shadow-sm)',
		'md'   => 'var(--csf-shadow-md)',
		'lg'   => 'var(--csf-shadow-lg)',
		'xl'   => 'var(--csf-shadow-xl)',
	);

	private const CARD_SCHEMES  = array( 'light', 'dark', 'brand' );
	private const HOVER_EFFECTS = array( 'none', 'lift', 'zoom', 'shadow' );
	private const ANIMATIONS    = array( 'fade', 'slideUp', 'slideLeft' );

	/**
	 * CSS custom properties for card styling, for the wrapper style attribute.
	 *
	 * Only attributes the author actually set are emitted; anything unset
	 * falls through to the --csf-* design tokens in the stylesheet.
	 *
	 * @param array<string, mixed> $attributes Block attributes.
	 * @return string e.g. "--csf-card-radius:8px;--csf-card-shadow:var(--csf-shadow-md);"
	 */
	public static function card_style_vars( array $attributes ): string {
		$vars = '';

		if ( isset( $attributes['borderRadius'] ) && is_numeric( $attributes['borderRadius'] ) ) {
			$vars .= sprintf( '--csf-card-radius:%dpx;', max( 0, (int) $attributes['borderRadius'] ) );
		}

		if ( isset( $attributes['borderWidth'] ) && is_numeric( $attributes['borderWidth'] ) ) {
			$vars .= sprintf( '--csf-card-border-width:%dpx;', max( 0, (int) $attributes['borderWidth'] ) );
		}

		$color = isset( $attributes['borderColor'] ) ? (string) $attributes['borderColor'] : '';
		if ( preg_match( '/^#([0-9a-f]{3}|[0-9a-f]{6})$/i', $color ) ) {
			$vars .= sprintf( '--csf-card-border-color:%s;', $color );
		}

		$shadow = isset( $attributes['cardShadow'] ) ? (string) $attributes['cardShadow'] : '';
		if ( isset( self::SHADOWS[ $shadow ] ) ) {
			$vars .= sprintf( '--csf-card-shadow:%s;', self::SHADOWS[ $shadow ] );
		}

		return $vars;
	}

	/**
	 * Padding/margin from the legacy blockPadding/blockMargin attributes.
	 *
	 * Emitted only when non-zero and only when core spacing (style.spacing)
	 * is not set, so blocks re-saved with the core controls never get both.
	 *
	 * @param array<string, mixed> $attributes Block attributes.
	 * @return string e.g. "padding:0px 24px 0px 24px;"
	 */
	public static function legacy_spacing_style( array $attributes ): string {
		if ( ! empty( $attributes['style']['spacing'] ) ) {
			return '';
		}

		$css = '';
		foreach ( array( 'blockPadding' => 'padding', 'blockMargin' => 'margin' ) as $attr => $property ) {
			$box = isset( $attributes[ $attr ] ) && is_array( $attributes[ $attr ] ) ? $attributes[ $attr ] : array();
			$sides = array();
			foreach ( array( 'top', 'right', 'bottom', 'left' ) as $side ) {
				$sides[] = max( 0, (int) ( $box[ $side ] ?? 0 ) );
			}
			if ( array_sum( $sides ) > 0 ) {
				$css .= sprintf( '%s:%dpx %dpx %dpx %dpx;', $property, ...$sides );
			}
		}

		return $css;
	}

	/**
	 * Wrapper classes that switch stylesheet-driven behaviour.
	 *
	 * @param array<string, mixed> $attributes Block attributes.
	 * @return string Space-separated class names (may be empty).
	 */
	public static function wrapper_classes( array $attributes ): string {
		$classes = array();

		$scheme = isset( $attributes['colorScheme'] ) ? (string) $attributes['colorScheme'] : '';
		if ( in_array( $scheme, self::CARD_SCHEMES, true ) ) {
			$classes[] = 'csf-card-scheme-' . $scheme;
		}

		$hover = isset( $attributes['hoverEffect'] ) ? (string) $attributes['hoverEffect'] : 'lift';
		if ( in_array( $hover, self::HOVER_EFFECTS, true ) ) {
			$classes[] = 'csf-hover-' . $hover;
		}

		$animation = isset( $attributes['scrollAnimation'] ) ? (string) $attributes['scrollAnimation'] : 'none';
		if ( in_array( $animation, self::ANIMATIONS, true ) ) {
			$classes[] = 'csf-anim-' . strtolower( preg_replace( '/([A-Z])/', '-$1', $animation ) );
		}

		foreach ( array( 'hideOnMobile' => 'mobile', 'hideOnTablet' => 'tablet', 'hideOnDesktop' => 'desktop' ) as $attr => $device ) {
			if ( ! empty( $attributes[ $attr ] ) ) {
				$classes[] = 'csf-hide-' . $device;
			}
		}

		return implode( ' ', $classes );
	}

	/**
	 * Per-instance CSS: responsive grid columns/gap and image aspect ratio.
	 *
	 * @param string               $block_id   Wrapper element id.
	 * @param array<string, mixed> $attributes Block attributes.
	 * @return string CSS (no <style> tag).
	 */
	public static function instance_css( string $block_id, array $attributes ): string {
		$columns = array_merge( array( 'mobile' => 2, 'tablet' => 3, 'desktop' => 4 ), (array) ( $attributes['columns'] ?? array() ) );
		$gap     = array_merge( array( 'mobile' => 16, 'tablet' => 20, 'desktop' => 24 ), (array) ( $attributes['gap'] ?? array() ) );
		$id      = '#' . $block_id;

		$css = sprintf(
			'%1$s .csf-grid-items{display:grid;gap:%2$dpx;grid-template-columns:repeat(%3$d,1fr);}',
			$id,
			max( 0, (int) $gap['mobile'] ),
			max( 1, (int) $columns['mobile'] )
		);
		$css .= sprintf(
			'@media (min-width:768px){%1$s .csf-grid-items{gap:%2$dpx;grid-template-columns:repeat(%3$d,1fr);}}',
			$id,
			max( 0, (int) $gap['tablet'] ),
			max( 1, (int) $columns['tablet'] )
		);
		$css .= sprintf(
			'@media (min-width:1024px){%1$s .csf-grid-items{gap:%2$dpx;grid-template-columns:repeat(%3$d,1fr);}}',
			$id,
			max( 0, (int) $gap['desktop'] ),
			max( 1, (int) $columns['desktop'] )
		);

		$ratio = isset( $attributes['imageAspectRatio'] ) ? (string) $attributes['imageAspectRatio'] : 'auto';
		if ( preg_match( '#^\d+/\d+$#', $ratio ) ) {
			$css .= sprintf( '%1$s .csf-part-card__image{aspect-ratio:%2$s;}', $id, $ratio );
		}

		return $css;
	}
}
