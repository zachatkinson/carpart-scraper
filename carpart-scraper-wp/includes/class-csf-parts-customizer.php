<?php
/**
 * Theme Customizer Integration for CSF Parts.
 *
 * Handles theme customizer settings and color overrides.
 * Separated from main plugin class to follow Single Responsibility Principle.
 *
 * @package CSF_Parts_Catalog
 * @since   2.0.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

/**
 * Class CSF_Parts_Customizer
 *
 * Responsible for managing theme customizer integration and color customization.
 */
class CSF_Parts_Customizer {

	/**
	 * Initialize hooks.
	 *
	 * @since 2.0.0
	 */
	public function init(): void {
		add_action( 'customize_register', array( $this, 'register_customizer_settings' ) );
	}

	/**
	 * Register theme customizer settings for color customization.
	 *
	 * @since 2.0.0
	 * @param WP_Customize_Manager $wp_customize Theme customizer object.
	 */
	public function register_customizer_settings( WP_Customize_Manager $wp_customize ): void {
		// Add CSF Parts section.
		$wp_customize->add_section(
			'csf_parts_colors',
			array(
				'title'    => 'CSF Parts Colors',
				'priority' => 30,
			)
		);

		// Primary Color Setting.
		$wp_customize->add_setting(
			'csf_primary_color',
			array(
				'default'           => '',
				'sanitize_callback' => 'sanitize_hex_color',
				'transport'         => 'refresh',
			)
		);

		$wp_customize->add_control(
			new WP_Customize_Color_Control(
				$wp_customize,
				'csf_primary_color',
				array(
					'label'       => 'Primary Color',
					'description' => 'Override the default primary color for CSF Parts elements (links, buttons, highlights). Leave empty to use theme default.',
					'section'     => 'csf_parts_colors',
					'settings'    => 'csf_primary_color',
				)
			)
		);

		// Secondary Color Setting.
		$wp_customize->add_setting(
			'csf_secondary_color',
			array(
				'default'           => '',
				'sanitize_callback' => 'sanitize_hex_color',
				'transport'         => 'refresh',
			)
		);

		$wp_customize->add_control(
			new WP_Customize_Color_Control(
				$wp_customize,
				'csf_secondary_color',
				array(
					'label'       => 'Secondary Color',
					'description' => 'Override the default secondary color for accents, badges, and secondary actions. Leave empty to use theme default.',
					'section'     => 'csf_parts_colors',
					'settings'    => 'csf_secondary_color',
				)
			)
		);
	}

	/**
	 * Add custom color overrides from theme customizer.
	 *
	 * Called during asset enqueuing to inject custom CSS variables.
	 *
	 * @since 2.0.0
	 */
	public function add_custom_color_overrides(): void {
		// Get custom colors from customizer.
		$primary_color   = get_theme_mod( 'csf_primary_color', '' );
		$secondary_color = get_theme_mod( 'csf_secondary_color', '' );

		// Only add overrides if colors are set.
		if ( empty( $primary_color ) && empty( $secondary_color ) ) {
			return;
		}

		$custom_css = ':root {';

		if ( ! empty( $primary_color ) ) {
			// Convert hex to RGB for rgba() usage.
			$rgb = csf_hex_to_rgb( $primary_color );
			$custom_css .= sprintf(
				'--csf-primary: %s; --csf-primary-rgb: %s;',
				esc_attr( $primary_color ),
				esc_attr( $rgb )
			);
		}

		if ( ! empty( $secondary_color ) ) {
			// Convert hex to RGB for rgba() usage.
			$rgb = csf_hex_to_rgb( $secondary_color );
			$custom_css .= sprintf(
				'--csf-secondary: %s; --csf-secondary-rgb: %s;',
				esc_attr( $secondary_color ),
				esc_attr( $rgb )
			);
		}

		$custom_css .= '}';

		wp_add_inline_style( 'csf-parts-colors', $custom_css );
	}
}
