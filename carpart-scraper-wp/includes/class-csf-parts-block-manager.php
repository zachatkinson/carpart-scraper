<?php
/**
 * Block Management for CSF Parts.
 *
 * Handles registration of Gutenberg blocks and block categories.
 * Separated from main plugin class to follow Single Responsibility Principle.
 *
 * @package CSF_Parts_Catalog
 * @since   2.0.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

/**
 * Class CSF_Parts_Block_Manager
 *
 * Responsible for managing all Gutenberg block registrations.
 */
class CSF_Parts_Block_Manager {

	/**
	 * Initialize hooks.
	 *
	 * @since 2.0.0
	 */
	public function init(): void {
		add_action( 'init', array( $this, 'register_blocks' ) );
	}

	/**
	 * Register Gutenberg blocks.
	 *
	 * @since 2.0.0
	 */
	public function register_blocks(): void {
		// Check if Block Editor is available.
		if ( ! function_exists( 'register_block_type' ) ) {
			return;
		}

		// Register block category.
		add_filter( 'block_categories_all', array( $this, 'register_block_category' ), 10, 2 );

		// Register blocks (will be built with @wordpress/scripts).
		$blocks = array( 'single-product', 'product-catalog' );

		foreach ( $blocks as $block ) {
			$block_path = CSF_PARTS_PLUGIN_DIR . 'blocks/' . $block;

			if ( file_exists( $block_path . '/block.json' ) ) {
				register_block_type( $block_path );
			}
		}
	}

	/**
	 * Register custom block category.
	 *
	 * @since 2.0.0
	 * @param array                   $categories Existing block categories.
	 * @param WP_Block_Editor_Context $context    Block editor context.
	 * @return array Modified block categories.
	 */
	public function register_block_category( array $categories, $context ): array {
		return array_merge(
			$categories,
			array(
				array(
					'slug'  => 'csf-parts',
					'title' => 'CSF Parts',
					'icon'  => 'car',
				),
			)
		);
	}
}
