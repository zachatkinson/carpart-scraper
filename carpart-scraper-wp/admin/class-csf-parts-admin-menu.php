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
		// Main settings page (submenu under Parts).
		add_submenu_page(
			'edit.php?post_type=' . CSF_Parts_Constants::POST_TYPE . '',
			__( 'Settings', CSF_Parts_Constants::TEXT_DOMAIN ),
			__( 'Settings', CSF_Parts_Constants::TEXT_DOMAIN ),
			'manage_options',
			'csf-parts-settings',
			array( $this, 'render_settings_page' )
		);

		// Import page.
		add_submenu_page(
			'edit.php?post_type=' . CSF_Parts_Constants::POST_TYPE . '',
			__( 'Import Parts', CSF_Parts_Constants::TEXT_DOMAIN ),
			__( 'Import', CSF_Parts_Constants::TEXT_DOMAIN ),
			'manage_options',
			'csf-parts-import',
			array( $this, 'render_import_page' )
		);

		// Import log page (hidden from menu).
		add_submenu_page(
			'',
			__( 'Import Log', CSF_Parts_Constants::TEXT_DOMAIN ),
			__( 'Import Log', CSF_Parts_Constants::TEXT_DOMAIN ),
			'manage_options',
			'csf-parts-import-log',
			array( $this, 'render_import_log_page' )
		);
	}

	/**
	 * Render settings page.
	 *
	 * @since 1.0.0
	 */
	public function render_settings_page(): void {
		if ( ! current_user_can( 'manage_options' ) ) {
			wp_die( esc_html__( 'You do not have permission to access this page.', CSF_Parts_Constants::TEXT_DOMAIN ) );
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
			wp_die( esc_html__( 'You do not have permission to access this page.', CSF_Parts_Constants::TEXT_DOMAIN ) );
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
			wp_die( esc_html__( 'You do not have permission to access this page.', CSF_Parts_Constants::TEXT_DOMAIN ) );
		}

		require_once CSF_PARTS_PLUGIN_DIR . 'admin/views/import-log-page.php';
	}
}
