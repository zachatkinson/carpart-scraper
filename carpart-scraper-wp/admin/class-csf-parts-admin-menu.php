<?php
/**
 * Admin Menu Registration.
 *
 * Registers admin menu pages for CSF Parts plugin.
 *
 * @package CSF_Parts_Catalog
 * @since   1.0.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

/**
 * Class CSF_Parts_Admin_Menu
 */
class CSF_Parts_Admin_Menu {

	/**
	 * Constructor.
	 */
	public function __construct() {
		add_action( 'admin_menu', array( $this, 'register_menu_pages' ) );
	}

	/**
	 * Register admin menu pages.
	 *
	 * @since 1.0.0
	 */
	public function register_menu_pages(): void {
		// Top-level menu page.
		add_menu_page(
			'CSF Parts',
			'CSF Parts',
			'manage_options',
			'csf-parts',
			array( $this, 'render_parts_list_page' ),
			'dashicons-cart',
			30
		);

		// All Parts submenu (default).
		add_submenu_page(
			'csf-parts',
			'All Parts',
			'All Parts',
			'manage_options',
			'csf-parts',
			array( $this, 'render_parts_list_page' )
		);

		// Import page.
		add_submenu_page(
			'csf-parts',
			'Import Parts',
			'Import',
			'manage_options',
			'csf-parts-import',
			array( $this, 'render_import_page' )
		);

		// Settings page.
		add_submenu_page(
			'csf-parts',
			'Settings',
			'Settings',
			'manage_options',
			'csf-parts-settings',
			array( $this, 'render_settings_page' )
		);

		// Import log page (hidden from menu).
		add_submenu_page(
			'',
			'Import Log',
			'Import Log',
			'manage_options',
			'csf-parts-import-log',
			array( $this, 'render_import_log_page' )
		);
	}

	/**
	 * Render parts list page.
	 *
	 * @since 1.0.0
	 */
	public function render_parts_list_page(): void {
		if ( ! current_user_can( 'manage_options' ) ) {
			wp_die( esc_html( 'You do not have permission to access this page.' ) );
		}

		require_once CSF_PARTS_PLUGIN_DIR . 'admin/views/parts-list-page.php';
	}

	/**
	 * Render settings page.
	 *
	 * @since 1.0.0
	 */
	public function render_settings_page(): void {
		if ( ! current_user_can( 'manage_options' ) ) {
			wp_die( esc_html( 'You do not have permission to access this page.' ) );
		}

		require_once CSF_PARTS_PLUGIN_DIR . 'admin/views/settings-page.php';
	}

	/**
	 * Render import page.
	 *
	 * @since 1.0.0
	 */
	public function render_import_page(): void {
		if ( ! current_user_can( 'manage_options' ) ) {
			wp_die( esc_html( 'You do not have permission to access this page.' ) );
		}

		require_once CSF_PARTS_PLUGIN_DIR . 'admin/views/import-page.php';
	}

	/**
	 * Render import log page.
	 *
	 * @since 1.0.0
	 */
	public function render_import_log_page(): void {
		if ( ! current_user_can( 'manage_options' ) ) {
			wp_die( esc_html( 'You do not have permission to access this page.' ) );
		}

		require_once CSF_PARTS_PLUGIN_DIR . 'admin/views/import-log-page.php';
	}
}
