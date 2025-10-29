<?php
/**
 * Gutenberg Blocks Registration.
 *
 * Registers all custom Gutenberg blocks for the CSF Parts Catalog plugin.
 *
 * @package    CSF_Parts_Catalog
 * @subpackage CSF_Parts_Catalog/includes
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * CSF Parts Blocks class.
 *
 * Handles registration and asset enqueuing for all Gutenberg blocks.
 */
class CSF_Parts_Blocks {

	/**
	 * Plugin directory path.
	 *
	 * @var string
	 */
	private $plugin_dir;

	/**
	 * Plugin directory URL.
	 *
	 * @var string
	 */
	private $plugin_url;

	/**
	 * Initialize the class.
	 *
	 * @param string $plugin_dir Plugin directory path.
	 * @param string $plugin_url Plugin directory URL.
	 */
	public function __construct( $plugin_dir, $plugin_url ) {
		$this->plugin_dir = $plugin_dir;
		$this->plugin_url = $plugin_url;
	}

	/**
	 * Register hooks.
	 */
	public function init() {
		add_action( 'init', array( $this, 'register_blocks' ) );
		add_action( 'enqueue_block_editor_assets', array( $this, 'enqueue_editor_assets' ) );
		add_action( 'wp_enqueue_scripts', array( $this, 'enqueue_frontend_assets' ) );
	}

	/**
	 * Register all blocks.
	 */
	public function register_blocks() {
		// Register Single Product block.
		register_block_type( $this->plugin_dir . 'blocks/single-product' );

		// Register Product Grid block.
		register_block_type( $this->plugin_dir . 'blocks/product-grid' );

		// Register Vehicle Selector block.
		register_block_type( $this->plugin_dir . 'blocks/vehicle-selector' );
	}

	/**
	 * Enqueue editor assets.
	 *
	 * Loads compiled JavaScript for the block editor.
	 */
	public function enqueue_editor_assets() {
		// Editor styles for all blocks.
		wp_enqueue_style(
			'csf-blocks-editor',
			$this->plugin_url . 'blocks/build/editor.css',
			array( 'wp-edit-blocks' ),
			CSF_PARTS_VERSION
		);
	}

	/**
	 * Enqueue frontend assets.
	 *
	 * Loads styles and scripts needed for blocks on the frontend.
	 */
	public function enqueue_frontend_assets() {
		// Frontend styles for all blocks.
		wp_enqueue_style(
			'csf-blocks-frontend',
			$this->plugin_url . 'blocks/build/style.css',
			array(),
			CSF_PARTS_VERSION
		);

		// AJAX script for Vehicle Selector.
		if ( has_block( 'csf-parts/vehicle-selector' ) ) {
			wp_enqueue_script(
				'csf-vehicle-selector',
				$this->plugin_url . 'blocks/build/vehicle-selector.js',
				array( 'jquery' ),
				CSF_PARTS_VERSION,
				true
			);

			// Localize script for AJAX.
			wp_localize_script(
				'csf-vehicle-selector',
				'csfVehicleSelector',
				array(
					'ajaxUrl' => admin_url( 'admin-ajax.php' ),
					'nonce'   => wp_create_nonce( 'csf_vehicle_search' ),
				)
			);
		}
	}
}
