<?php
/**
 * Asset Management for CSF Parts.
 *
 * Handles enqueuing of CSS and JavaScript files for public, admin, and block editor.
 * Separated from main plugin class to follow Single Responsibility Principle.
 *
 * @package CSF_Parts_Catalog
 * @since   2.0.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

/**
 * Class CSF_Parts_Assets
 *
 * Responsible for managing all plugin assets (CSS and JavaScript).
 */
class CSF_Parts_Assets {

	/**
	 * Customizer instance.
	 *
	 * @var CSF_Parts_Customizer
	 */
	private CSF_Parts_Customizer $customizer;

	/**
	 * Design tokens instance.
	 *
	 * @var CSF_Parts_Design
	 */
	private CSF_Parts_Design $design;

	/**
	 * Constructor.
	 *
	 * @param CSF_Parts_Customizer $customizer Customizer instance for legacy color overrides.
	 * @param CSF_Parts_Design     $design     Design tokens (presets + overrides).
	 */
	public function __construct( CSF_Parts_Customizer $customizer, CSF_Parts_Design $design ) {
		$this->customizer = $customizer;
		$this->design     = $design;
	}

	/**
	 * Initialize hooks.
	 *
	 * @since 2.0.0
	 */
	public function init(): void {
		add_action( 'wp_enqueue_scripts', array( $this, 'enqueue_public_assets' ) );
		add_action( 'admin_enqueue_scripts', array( $this, 'enqueue_admin_assets' ) );
		add_action( 'enqueue_block_editor_assets', array( $this, 'enqueue_block_editor_assets' ) );
	}

	/**
	 * Enqueue public-facing assets.
	 *
	 * @since 2.0.0
	 */
	public function enqueue_public_assets(): void {
		$this->enqueue_color_system();

		// Product Catalog Block CSS.
		wp_enqueue_style(
			'csf-parts-catalog-block',
			CSF_PARTS_PLUGIN_URL . 'public/css/product-catalog-block.css',
			array( 'csf-parts-colors' ),
			CSF_PARTS_VERSION,
			'all'
		);

		// Public CSS.
		wp_enqueue_style(
			'csf-parts-public',
			CSF_PARTS_PLUGIN_URL . 'public/css/frontend-styles.css',
			array( 'csf-parts-colors', 'csf-parts-catalog-block' ),
			CSF_PARTS_VERSION,
			'all'
		);

		// Part page stylesheet, registered so part blocks (block.json "style") can enqueue it anywhere.
		wp_register_style(
			'csf-part-modern',
			CSF_PARTS_PLUGIN_URL . 'public/css/part-single-modern.css',
			array( 'csf-parts-colors', 'csf-parts-catalog-block' ),
			CSF_PARTS_VERSION,
			'all'
		);

		// Part Finder block CSS (block.json "style" handle).
		wp_enqueue_style(
			'csf-parts-part-finder',
			CSF_PARTS_PLUGIN_URL . 'public/css/part-finder-block.css',
			array( 'csf-parts-colors', 'csf-parts-catalog-block' ),
			CSF_PARTS_VERSION,
			'all'
		);

		// Async search JS.
		wp_enqueue_script(
			'csf-parts-search',
			CSF_PARTS_PLUGIN_URL . 'public/js/search-async.js',
			array(),
			CSF_PARTS_VERSION,
			true
		);

		// Engine selector JS - dynamic fitment confirmation.
		wp_enqueue_script(
			'csf-parts-engine-selector',
			CSF_PARTS_PLUGIN_URL . 'public/js/engine-selector.js',
			array(),
			CSF_PARTS_VERSION,
			true
		);

		// Localize script with REST API data.
		wp_localize_script(
			'csf-parts-search',
			'csfPartsData',
			array(
				'restUrl' => rest_url( 'csf/v1/' ),
				'nonce'   => wp_create_nonce( 'wp_rest' ),
				'ajaxUrl' => admin_url( 'admin-ajax.php' ),
			)
		);
	}

	/**
	 * Enqueue the token stylesheets in precedence order.
	 *
	 * base tokens → dark tokens (per Color Scheme) → Design settings inline CSS
	 * → legacy Customizer colours. Shared by the front end and the block editor
	 * so previews match.
	 *
	 * @since 1.9.0
	 */
	private function enqueue_color_system(): void {
		// Color System (foundation - must load first).
		wp_enqueue_style(
			'csf-parts-colors',
			CSF_PARTS_PLUGIN_URL . 'public/css/csf-color-system.css',
			array(),
			CSF_PARTS_VERSION,
			'all'
		);

		// Dark palette: enqueued (or not) according to the Color scheme setting.
		$scheme       = $this->get_color_scheme();
		$color_handle = $this->enqueue_dark_color_scheme( $scheme );

		// Design presets + overrides, after the dark sheet so they win.
		$design_css = $this->design->inline_css( $scheme );
		if ( '' !== $design_css ) {
			wp_add_inline_style( $color_handle, $design_css );
		}

		// Legacy customizer colours (kept for sites that set them before 1.9.0).
		$this->customizer->add_custom_color_overrides( $color_handle );
	}

	/**
	 * Current Color Scheme setting, sanitized.
	 *
	 * @since 1.9.0
	 * @return string
	 */
	private function get_color_scheme(): string {
		return self::sanitize_color_scheme(
			(string) get_option( CSF_Parts_Constants::OPTION_COLOR_SCHEME, CSF_Parts_Constants::COLOR_SCHEME_DEFAULT )
		);
	}

	/**
	 * Enqueue the dark color-scheme stylesheet according to the plugin setting.
	 *
	 * @since 1.8.11
	 * @param string $scheme One of CSF_Parts_Constants::COLOR_SCHEMES.
	 * @return string Handle of the last enqueued color stylesheet.
	 */
	private function enqueue_dark_color_scheme( string $scheme ): string {
		$media = self::get_dark_stylesheet_media( $scheme );

		if ( null === $media ) {
			return 'csf-parts-colors';
		}

		wp_enqueue_style(
			'csf-parts-colors-dark',
			CSF_PARTS_PLUGIN_URL . 'public/css/csf-color-system-dark.css',
			array( 'csf-parts-colors' ),
			CSF_PARTS_VERSION,
			$media
		);

		return 'csf-parts-colors-dark';
	}

	/**
	 * Resolve the <link media> attribute for the dark stylesheet.
	 *
	 * @since 1.8.11
	 * @param string $scheme One of CSF_Parts_Constants::COLOR_SCHEMES.
	 * @return string|null Media query string, or null when the dark stylesheet
	 *                     must not be loaded at all.
	 */
	public static function get_dark_stylesheet_media( string $scheme ): ?string {
		switch ( $scheme ) {
			case CSF_Parts_Constants::COLOR_SCHEME_DARK:
				return 'all';
			case CSF_Parts_Constants::COLOR_SCHEME_LIGHT:
				return null;
			case CSF_Parts_Constants::COLOR_SCHEME_AUTO:
			default:
				return '(prefers-color-scheme: dark)';
		}
	}

	/**
	 * Coerce an arbitrary value to a valid color scheme.
	 *
	 * @since 1.8.11
	 * @param string $scheme Raw value (e.g. from a form or option).
	 * @return string A member of CSF_Parts_Constants::COLOR_SCHEMES.
	 */
	public static function sanitize_color_scheme( string $scheme ): string {
		return in_array( $scheme, CSF_Parts_Constants::COLOR_SCHEMES, true )
			? $scheme
			: CSF_Parts_Constants::COLOR_SCHEME_DEFAULT;
	}

	/**
	 * Enqueue admin assets.
	 *
	 * @since 2.0.0
	 * @param string $hook Current admin page hook.
	 */
	public function enqueue_admin_assets( string $hook ): void {
		// Only load on CSF Parts admin pages.
		if ( empty( $hook ) || false === strpos( $hook, 'csf-parts' ) ) {
			return;
		}

		// Admin CSS.
		wp_enqueue_style(
			'csf-parts-admin',
			CSF_PARTS_PLUGIN_URL . 'admin/css/admin-styles.css',
			array(),
			CSF_PARTS_VERSION,
			'all'
		);

		// Admin JS.
		wp_enqueue_script(
			'csf-parts-admin',
			CSF_PARTS_PLUGIN_URL . 'admin/js/admin-scripts.js',
			array( 'jquery' ),
			CSF_PARTS_VERSION,
			true
		);

		// Design page uses the core colour picker.
		if ( false !== strpos( $hook, 'csf-parts-design' ) ) {
			wp_enqueue_style( 'wp-color-picker' );
			wp_enqueue_script( 'wp-color-picker' );
		}

		// Localize admin script.
		wp_localize_script(
			'csf-parts-admin',
			'csfPartsAdmin',
			array(
				'ajaxUrl' => admin_url( 'admin-ajax.php' ),
				'nonce'   => wp_create_nonce( 'csf_parts_admin' ),
			)
		);
	}

	/**
	 * Enqueue block editor assets.
	 *
	 * @since 2.0.0
	 */
	public function enqueue_block_editor_assets(): void {
		// Same token stack as the front end so editor previews match.
		$this->enqueue_color_system();

		wp_enqueue_style(
			'csf-parts-catalog-block',
			CSF_PARTS_PLUGIN_URL . 'public/css/product-catalog-block.css',
			array( 'csf-parts-colors' ),
			CSF_PARTS_VERSION,
			'all'
		);

		// Enqueue frontend styles in the block editor so blocks render correctly.
		wp_enqueue_style(
			'csf-parts-public',
			CSF_PARTS_PLUGIN_URL . 'public/css/frontend-styles.css',
			array( 'csf-parts-colors', 'csf-parts-catalog-block' ),
			CSF_PARTS_VERSION,
			'all'
		);

		wp_enqueue_style(
			'csf-parts-part-finder',
			CSF_PARTS_PLUGIN_URL . 'public/css/part-finder-block.css',
			array( 'csf-parts-colors', 'csf-parts-catalog-block' ),
			CSF_PARTS_VERSION,
			'all'
		);

		wp_enqueue_style(
			'csf-part-modern',
			CSF_PARTS_PLUGIN_URL . 'public/css/part-single-modern.css',
			array( 'csf-parts-colors', 'csf-parts-catalog-block' ),
			CSF_PARTS_VERSION,
			'all'
		);
	}
}
