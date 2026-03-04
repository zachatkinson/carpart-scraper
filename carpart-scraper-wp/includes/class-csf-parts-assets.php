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
	 * Constructor.
	 *
	 * @param CSF_Parts_Customizer $customizer Customizer instance for color overrides.
	 */
	public function __construct( CSF_Parts_Customizer $customizer ) {
		$this->customizer = $customizer;
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
		// Color System (foundation - must load first).
		wp_enqueue_style(
			'csf-parts-colors',
			CSF_PARTS_PLUGIN_URL . 'public/css/csf-color-system.css',
			array(),
			CSF_PARTS_VERSION,
			'all'
		);

		// Add custom color overrides from customizer.
		$this->customizer->add_custom_color_overrides();

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
		// Enqueue frontend styles in the block editor so blocks render correctly.
		wp_enqueue_style(
			'csf-parts-public',
			CSF_PARTS_PLUGIN_URL . 'public/css/frontend-styles.css',
			array(),
			CSF_PARTS_VERSION,
			'all'
		);
	}
}
