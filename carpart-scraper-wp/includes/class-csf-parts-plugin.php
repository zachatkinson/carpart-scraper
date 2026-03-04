<?php
/**
 * Main plugin class (refactored for SOLID compliance).
 *
 * Orchestrates plugin initialization and coordinates components.
 * Follows Single Responsibility Principle - only responsible for plugin lifecycle.
 *
 * @package CSF_Parts_Catalog
 * @since   1.0.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

/**
 * Class CSF_Parts_Plugin
 *
 * Core orchestrator - delegates specific responsibilities to focused classes.
 */
class CSF_Parts_Plugin {

	/**
	 * Plugin instance.
	 *
	 * @var CSF_Parts_Plugin
	 */
	private static $instance = null;

	/**
	 * Component instances.
	 *
	 * @var object[]
	 */
	private array $components = array();

	/**
	 * Get plugin instance (Singleton pattern).
	 *
	 * @return CSF_Parts_Plugin
	 */
	public static function get_instance() {
		if ( null === self::$instance ) {
			self::$instance = new self();
		}
		return self::$instance;
	}

	/**
	 * Constructor.
	 */
	private function __construct() {
		$this->load_dependencies();
		$this->initialize_components();
		$this->define_hooks();
	}

	/**
	 * Load required dependencies.
	 *
	 * @since 2.0.0
	 */
	private function load_dependencies(): void {
		// Load helper functions first.
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/helpers.php';

		// Load constants.
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-constants.php';

		// Load import source strategies.
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/import-sources/interface-import-source-strategy.php';
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/import-sources/class-url-import-source.php';
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/import-sources/class-directory-import-source.php';
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/import-sources/class-import-source-factory.php';

		// Load core classes.
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-database.php';
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-url-handler.php';
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-sitemap-provider.php';

		// Load supporting classes.
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-ajax-handler.php';
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-rest-api.php';
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-json-importer.php';
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-auto-import.php';
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-shortcodes.php';

		// Load separated responsibility classes (SOLID refactoring).
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-customizer.php';
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-assets.php';
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-block-manager.php';

		// Load admin classes.
		if ( is_admin() ) {
			require_once CSF_PARTS_PLUGIN_DIR . 'admin/class-csf-parts-admin-menu.php';
			require_once CSF_PARTS_PLUGIN_DIR . 'admin/class-csf-parts-import-manager.php';
		}
	}

	/**
	 * Initialize plugin components.
	 *
	 * Each component handles a single responsibility (SOLID principle).
	 *
	 * @since 2.0.0
	 */
	private function initialize_components(): void {
		// Core database component.
		$this->components['database'] = new CSF_Parts_Database();
		$this->components['database']->maybe_migrate();

		// URL handling (virtual pages).
		$this->components['url_handler'] = new CSF_Parts_URL_Handler();

		// Customizer integration (separated from main class).
		$this->components['customizer'] = new CSF_Parts_Customizer();
		$this->components['customizer']->init();

		// Asset management (separated from main class).
		$this->components['assets'] = new CSF_Parts_Assets( $this->components['customizer'] );
		$this->components['assets']->init();

		// Block management (separated from main class).
		$this->components['block_manager'] = new CSF_Parts_Block_Manager();
		$this->components['block_manager']->init();

		// API handlers.
		$this->components['ajax_handler'] = new CSF_Parts_AJAX_Handler();
		$this->components['rest_api']     = new CSF_Parts_REST_API();

		// Import and automation.
		$this->components['auto_import'] = new CSF_Parts_Auto_Import();
		$this->components['shortcodes']  = new CSF_Parts_Shortcodes();

		// Admin components (only in admin context).
		if ( is_admin() ) {
			$this->components['admin_menu']     = new CSF_Parts_Admin_Menu();
			$this->components['import_manager'] = new CSF_Parts_Import_Manager();
		}
	}

	/**
	 * Define core WordPress hooks.
	 *
	 * Only hooks that directly relate to plugin orchestration remain here.
	 * Component-specific hooks are defined in their respective classes.
	 *
	 * @since 2.0.0
	 */
	private function define_hooks(): void {
		// Register sitemap provider (WordPress 5.5+).
		add_action( 'init', array( $this, 'register_sitemap_provider' ) );

		// Allow JSON uploads for administrators only.
		add_filter( 'upload_mimes', array( $this, 'allow_json_uploads' ) );

		// Add plugin action links.
		add_filter( 'plugin_action_links_' . CSF_PARTS_BASENAME, array( $this, 'add_action_links' ) );
	}

	/**
	 * Run the plugin.
	 *
	 * @since 1.0.0
	 */
	public function run(): void {
		// Plugin is initialized in constructor via hooks.
		do_action( 'csf_parts_loaded' );
	}

	/**
	 * Get component instance.
	 *
	 * Provides access to plugin components for extensibility.
	 *
	 * @since 2.0.0
	 * @param string $component_name Component name.
	 * @return object|null Component instance or null if not found.
	 */
	public function get_component( string $component_name ) {
		return $this->components[ $component_name ] ?? null;
	}

	/**
	 * Register sitemap provider with WordPress core sitemaps.
	 *
	 * @since 2.0.0
	 */
	public function register_sitemap_provider(): void {
		// Check if sitemaps are available (WordPress 5.5+).
		if ( ! function_exists( 'wp_register_sitemap_provider' ) ) {
			return;
		}

		// Register our custom sitemap provider.
		$provider = new CSF_Parts_Sitemap_Provider();
		wp_register_sitemap_provider( 'csfparts', $provider );
	}

	/**
	 * Allow JSON file uploads for administrators only.
	 *
	 * @since 1.0.0
	 * @param array $mimes Existing MIME types.
	 * @return array Modified MIME types.
	 */
	public function allow_json_uploads( array $mimes ): array {
		// Only allow JSON uploads for administrators.
		if ( ! current_user_can( 'manage_options' ) ) {
			return $mimes;
		}

		// Add JSON MIME type.
		$mimes['json'] = 'application/json';

		return $mimes;
	}

	/**
	 * Add action links to plugin page.
	 *
	 * @since 1.0.0
	 * @param array $links Existing plugin action links.
	 * @return array Modified action links.
	 */
	public function add_action_links( array $links ): array {
		$settings_link = sprintf(
			'<a href="%s">%s</a>',
			admin_url( 'admin.php?page=csf-parts-import' ),
			__( 'Import', 'csf-parts' )
		);

		array_unshift( $links, $settings_link );

		return $links;
	}

	/**
	 * Legacy getter for backwards compatibility.
	 *
	 * @deprecated 2.0.0 Use get_component() instead.
	 * @param string $property Property name.
	 * @return mixed Component instance or null.
	 */
	public function __get( string $property ) {
		return $this->get_component( $property );
	}
}
