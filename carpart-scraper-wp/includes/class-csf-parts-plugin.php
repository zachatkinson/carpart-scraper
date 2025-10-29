<?php
/**
 * Main plugin class.
 *
 * Coordinates all plugin functionality and initializes components.
 *
 * @package CSF_Parts_Catalog
 * @since   1.0.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

/**
 * Class CSF_Parts_Plugin
 */
class CSF_Parts_Plugin {

	/**
	 * Plugin instance.
	 *
	 * @var CSF_Parts_Plugin
	 */
	private static $instance = null;

	/**
	 * AJAX handler.
	 *
	 * @var CSF_Parts_AJAX_Handler
	 */
	public $ajax_handler;

	/**
	 * REST API handler.
	 *
	 * @var CSF_Parts_REST_API
	 */
	public $rest_api;

	/**
	 * Admin menu handler.
	 *
	 * @var CSF_Parts_Admin_Menu
	 */
	public $admin_menu;

	/**
	 * Auto-import handler.
	 *
	 * @var CSF_Parts_Auto_Import
	 */
	public $auto_import;

	/**
	 * Import manager.
	 *
	 * @var CSF_Parts_Import_Manager
	 */
	public $import_manager;

	/**
	 * URL handler for virtual pages.
	 *
	 * @var CSF_Parts_URL_Handler
	 */
	public $url_handler;

	/**
	 * Database handler.
	 *
	 * @var CSF_Parts_Database
	 */
	public $database;

	/**
	 * Shortcodes handler.
	 *
	 * @var CSF_Parts_Shortcodes
	 */
	public $shortcodes;

	/**
	 * Get plugin instance.
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
		$this->define_hooks();
	}

	/**
	 * Load required dependencies.
	 *
	 * @since 1.0.0
	 */
	private function load_dependencies(): void {
		// Load constants first (required by all other classes).
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-constants.php';

		// Load import source strategies.
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/import-sources/interface-import-source-strategy.php';
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/import-sources/class-url-import-source.php';
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/import-sources/class-directory-import-source.php';
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/import-sources/class-import-source-factory.php';

		// Load core classes (v2 - dynamic architecture).
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-database.php';
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-url-handler.php';
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-sitemap-provider.php';

		// Load supporting classes.
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-ajax-handler.php';
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-rest-api.php';
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-json-importer.php';
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-auto-import.php';
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-shortcodes.php';

		// Load admin classes.
		if ( is_admin() ) {
			require_once CSF_PARTS_PLUGIN_DIR . 'admin/class-csf-parts-admin-menu.php';
			require_once CSF_PARTS_PLUGIN_DIR . 'admin/class-csf-parts-import-manager.php';
		}

		// Initialize components (v2 architecture).
		$this->database     = new CSF_Parts_Database();
		$this->url_handler  = new CSF_Parts_URL_Handler();

		// Initialize supporting components.
		$this->ajax_handler    = new CSF_Parts_AJAX_Handler();
		$this->rest_api        = new CSF_Parts_REST_API();
		$this->auto_import     = new CSF_Parts_Auto_Import();
		$this->shortcodes      = new CSF_Parts_Shortcodes();

		if ( is_admin() ) {
			$this->admin_menu     = new CSF_Parts_Admin_Menu();
			$this->import_manager = new CSF_Parts_Import_Manager();
		}
	}

	/**
	 * Define WordPress hooks.
	 *
	 * @since 1.0.0
	 */
	private function define_hooks() {
		// Localization.
		add_action( 'plugins_loaded', array( $this, 'load_textdomain' ) );

		// Enqueue scripts and styles.
		add_action( 'wp_enqueue_scripts', array( $this, 'enqueue_public_assets' ) );
		add_action( 'admin_enqueue_scripts', array( $this, 'enqueue_admin_assets' ) );

		// Register Gutenberg blocks.
		add_action( 'init', array( $this, 'register_blocks' ) );

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
	public function run() {
		// Plugin is initialized in constructor via hooks.
		do_action( 'csf_parts_loaded' );
	}

	/**
	 * Load plugin textdomain for internationalization.
	 *
	 * @since 1.0.0
	 */
	public function load_textdomain() {
		load_plugin_textdomain(
			'csf-parts',
			false,
			dirname( CSF_PARTS_BASENAME ) . '/languages'
		);
	}

	/**
	 * Enqueue public-facing assets.
	 *
	 * @since 1.0.0
	 */
	public function enqueue_public_assets() {
		// Public CSS.
		wp_enqueue_style(
			'csf-parts-public',
			CSF_PARTS_PLUGIN_URL . 'public/css/frontend-styles.css',
			array(),
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

		// Localize script with REST API data.
		wp_localize_script(
			'csf-parts-search',
			'csfPartsData',
			array(
				'restUrl'   => rest_url( 'csf/v1/' ),
				'nonce'     => wp_create_nonce( 'wp_rest' ),
				'ajaxUrl'   => admin_url( 'admin-ajax.php' ),
			)
		);
	}

	/**
	 * Enqueue admin assets.
	 *
	 * @since 1.0.0
	 * @param string $hook Current admin page hook.
	 */
	public function enqueue_admin_assets( $hook ) {
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
	 * Register Gutenberg blocks.
	 *
	 * @since 1.0.0
	 */
	public function register_blocks() {
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
	 * @since 1.0.0
	 * @param array                   $categories Existing block categories.
	 * @param WP_Block_Editor_Context $context    Block editor context.
	 * @return array Modified block categories.
	 */
	public function register_block_category( $categories, $context ) {
		return array_merge(
			$categories,
			array(
				array(
					'slug'  => 'csf-parts',
					'title' => __( 'CSF Parts', 'csf-parts' ),
					'icon'  => 'car',
				),
			)
		);
	}

	/**
	 * Register sitemap provider with WordPress core sitemaps.
	 *
	 * @since 2.0.0
	 */
	public function register_sitemap_provider() {
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
	public function allow_json_uploads( $mimes ) {
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
	public function add_action_links( $links ) {
		$settings_link = sprintf(
			'<a href="%s">%s</a>',
			admin_url( 'admin.php?page=csf-parts-import' ),
			__( 'Import', 'csf-parts' )
		);

		array_unshift( $links, $settings_link );

		return $links;
	}


}
