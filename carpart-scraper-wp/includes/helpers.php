<?php
/**
 * Helper functions for CSF Parts Catalog.
 *
 * Global utility functions that can be used throughout the plugin.
 *
 * @package CSF_Parts_Catalog
 * @since   2.0.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

/**
 * Format dimension value with HTML fraction entities.
 *
 * Converts plain text fractions (1/2, 9/16, etc.) to nicely formatted
 * HTML using Unicode fraction characters for common fractions and
 * superscript/subscript for uncommon ones.
 *
 * @since 2.0.0
 * @param string $dimension Dimension value (e.g., "28 1/2", "21 9/16").
 * @return string Formatted dimension with HTML fractions.
 *
 * @example
 *     csf_format_dimension_fractions( '28 1/2' )  // Returns: 28 ½
 *     csf_format_dimension_fractions( '21 9/16' ) // Returns: 21 <sup>9</sup>⁄<sub>16</sub>
 */
function csf_format_dimension_fractions( string $dimension ): string {
	// Map common fractions to Unicode characters.
	$fraction_map = array(
		' 1/2'  => ' ½',
		' 1/3'  => ' ⅓',
		' 2/3'  => ' ⅔',
		' 1/4'  => ' ¼',
		' 3/4'  => ' ¾',
		' 1/5'  => ' ⅕',
		' 2/5'  => ' ⅖',
		' 3/5'  => ' ⅗',
		' 4/5'  => ' ⅘',
		' 1/6'  => ' ⅙',
		' 5/6'  => ' ⅚',
		' 1/8'  => ' ⅛',
		' 3/8'  => ' ⅜',
		' 5/8'  => ' ⅝',
		' 7/8'  => ' ⅞',
	);

	// Replace common fractions with Unicode characters.
	$formatted = str_replace( array_keys( $fraction_map ), array_values( $fraction_map ), ' ' . $dimension );

	// Handle uncommon fractions (like 9/16, 1/16) with superscript/subscript.
	// Uses fraction slash character (U+2044) for better rendering.
	$formatted = preg_replace_callback(
		'/\s(\d+)\/(\d+)/',
		function( $matches ) {
			return ' <sup>' . $matches[1] . '</sup>⁄<sub>' . $matches[2] . '</sub>';
		},
		$formatted
	);

	return trim( $formatted );
}

/**
 * Convert hex color to RGB string.
 *
 * Converts a hexadecimal color code to comma-separated RGB values
 * suitable for use in rgba() CSS functions.
 *
 * @since 2.0.0
 * @param string $hex Hex color code (with or without # prefix).
 * @return string RGB values separated by commas (e.g., "37, 99, 235").
 *
 * @example
 *     csf_hex_to_rgb( '#2563eb' )  // Returns: "37, 99, 235"
 *     csf_hex_to_rgb( 'fff' )      // Returns: "255, 255, 255"
 */
function csf_hex_to_rgb( string $hex ): string {
	// Remove # if present.
	$hex = ltrim( $hex, '#' );

	// Parse hex values.
	if ( strlen( $hex ) === 3 ) {
		// Short format (e.g., "fff" -> "ffffff").
		$r = hexdec( str_repeat( substr( $hex, 0, 1 ), 2 ) );
		$g = hexdec( str_repeat( substr( $hex, 1, 1 ), 2 ) );
		$b = hexdec( str_repeat( substr( $hex, 2, 1 ), 2 ) );
	} else {
		// Full format (e.g., "2563eb").
		$r = hexdec( substr( $hex, 0, 2 ) );
		$g = hexdec( substr( $hex, 2, 2 ) );
		$b = hexdec( substr( $hex, 4, 2 ) );
	}

	return "$r, $g, $b";
}

/**
 * Format SKU for display.
 *
 * Converts SKU to clean display format: CSF-3680 -> CSF3680
 *
 * @since 2.0.0
 * @param string $sku Part SKU (e.g., "CSF-3680").
 * @return string Clean display SKU (e.g., "CSF3680").
 *
 * @example
 *     csf_format_sku_display( 'CSF-3680' )  // Returns: "CSF3680"
 *     csf_format_sku_display( 'CSF-10881' ) // Returns: "CSF10881"
 */
function csf_format_sku_display( string $sku ): string {
	// Remove hyphens from SKU for clean display (CSF-3680 -> CSF3680).
	return str_replace( '-', '', strtoupper( $sku ) );
}

/**
 * Generate clean part URL from SKU.
 *
 * Converts SKU to clean URL format: CSF-3680 -> /parts/csf3680
 *
 * @since 2.0.0
 * @param string $sku Part SKU (e.g., "CSF-3680").
 * @return string Clean part URL.
 *
 * @example
 *     csf_get_part_url( 'CSF-3680' )  // Returns: "https://example.com/parts/csf3680"
 */
function csf_get_part_url( string $sku ): string {
	// Remove CSF- prefix and hyphens from SKU for clean URL (CSF-3680 -> csf3680).
	$clean_sku = strtolower( str_replace( array( 'CSF-', '-' ), '', $sku ) );
	return home_url( '/parts/csf' . $clean_sku );
}

/**
 * Render a consistent select dropdown with standard styling.
 *
 * Generates a select dropdown with consistent .csf-select styling including
 * chevron icon, proper escaping, and optional label.
 *
 * @since 2.0.0
 * @param array $args {
 *     Dropdown configuration options.
 *
 *     @type string       $id             Select element ID (required).
 *     @type string       $name           Select element name (required).
 *     @type array        $options        Array of options. Keys are values, values are labels (required).
 *     @type string       $selected       Currently selected value. Default empty.
 *     @type string       $label          Label text. Default empty (no label).
 *     @type string       $placeholder    Placeholder option text. Default 'Select...'.
 *     @type string       $class          Additional CSS classes. Default empty.
 *     @type string       $wrapper_class  Wrapper div CSS classes. Default 'csf-filter-group'.
 *     @type bool         $show_wrapper   Whether to show wrapper div. Default true.
 *     @type array        $attributes     Additional HTML attributes for select. Default empty.
 * }
 * @return string HTML markup for the dropdown.
 *
 * @example
 *     // Simple dropdown
 *     echo csf_render_select( array(
 *         'id'      => 'my-select',
 *         'name'    => 'my_value',
 *         'options' => array( 'opt1' => 'Option 1', 'opt2' => 'Option 2' ),
 *         'label'   => 'Choose Option',
 *     ) );
 *
 *     // Dropdown without wrapper
 *     echo csf_render_select( array(
 *         'id'           => 'engine-select',
 *         'name'         => 'engine',
 *         'options'      => $engines,
 *         'show_wrapper' => false,
 *         'class'        => 'my-custom-class',
 *     ) );
 */
function csf_render_select( array $args ): string {
	// Default arguments.
	$defaults = array(
		'id'            => '',
		'name'          => '',
		'options'       => array(),
		'selected'      => '',
		'label'         => '',
		'placeholder'   => 'Select...',
		'class'         => '',
		'wrapper_class' => 'csf-filter-group',
		'show_wrapper'  => true,
		'attributes'    => array(),
	);

	$args = wp_parse_args( $args, $defaults );

	// Validate required fields.
	if ( empty( $args['id'] ) || empty( $args['name'] ) || empty( $args['options'] ) ) {
		return '<!-- csf_render_select: Missing required parameters -->';
	}

	// Build additional attributes string.
	$attr_string = '';
	if ( ! empty( $args['attributes'] ) && is_array( $args['attributes'] ) ) {
		foreach ( $args['attributes'] as $attr_key => $attr_value ) {
			$attr_string .= ' ' . esc_attr( $attr_key ) . '="' . esc_attr( $attr_value ) . '"';
		}
	}

	// Build CSS classes (always include .csf-select for consistent styling).
	$select_classes = 'csf-select';
	if ( ! empty( $args['class'] ) ) {
		$select_classes .= ' ' . esc_attr( $args['class'] );
	}

	// Start building HTML.
	$html = '';

	// Wrapper div (optional).
	if ( $args['show_wrapper'] ) {
		$html .= '<div class="' . esc_attr( $args['wrapper_class'] ) . '">';
	}

	// Label (optional).
	if ( ! empty( $args['label'] ) ) {
		$html .= '<label for="' . esc_attr( $args['id'] ) . '" class="csf-filter-group__label">';
		$html .= esc_html( $args['label'] );
		$html .= '</label>';
	}

	// Select element.
	$html .= '<select';
	$html .= ' id="' . esc_attr( $args['id'] ) . '"';
	$html .= ' name="' . esc_attr( $args['name'] ) . '"';
	$html .= ' class="' . esc_attr( $select_classes ) . '"';
	$html .= $attr_string;
	$html .= '>';

	// Placeholder option.
	if ( ! empty( $args['placeholder'] ) ) {
		$html .= '<option value="">';
		$html .= esc_html( $args['placeholder'] );
		$html .= '</option>';
	}

	// Options.
	foreach ( $args['options'] as $value => $label ) {
		$html .= '<option value="' . esc_attr( $value ) . '"';
		if ( (string) $args['selected'] === (string) $value ) {
			$html .= ' selected';
		}
		$html .= '>';
		$html .= esc_html( $label );
		$html .= '</option>';
	}

	$html .= '</select>';

	// Close wrapper div (if opened).
	if ( $args['show_wrapper'] ) {
		$html .= '</div>';
	}

	return $html;
}

/**
 * Get placeholder image URL for parts without images.
 *
 * Returns the URL to a placeholder SVG image used when a part has no product images available.
 *
 * @since 2.0.0
 * @return string URL to placeholder image.
 */
function csf_get_placeholder_image_url(): string {
	return plugins_url( 'public/images/part-placeholder.svg', dirname( __FILE__, 2 ) . '/csf-parts-catalog.php' );
}

/**
 * Resolve an image URL from a relative path or full URL.
 *
 * Handles both full URLs (returned as-is) and relative paths stored in the
 * database (e.g. "images/avif/CSF-3680_0.avif") by prepending the WordPress
 * uploads directory URL. Images are stored in wp-content/uploads/csf-parts/
 * so they persist across plugin updates.
 *
 * @since 1.2.1
 * @param string $url Image URL or relative path.
 * @return string Fully qualified image URL.
 */
function csf_resolve_image_url( string $url ): string {
	if ( empty( $url ) ) {
		return csf_get_placeholder_image_url();
	}

	// Already a full URL — return as-is.
	if ( str_starts_with( $url, 'http://' ) || str_starts_with( $url, 'https://' ) || str_starts_with( $url, '//' ) ) {
		return $url;
	}

	// Relative path — resolve from wp-content/uploads/csf-parts/.
	$upload_dir = wp_upload_dir();
	return $upload_dir['baseurl'] . '/csf-parts/' . ltrim( $url, '/' );
}
