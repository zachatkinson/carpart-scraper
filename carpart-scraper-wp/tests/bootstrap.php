<?php
/**
 * PHPUnit bootstrap file.
 *
 * @package CSF_Parts_Catalog
 */

// Define test environment constants.
define( 'CSF_PARTS_TESTS', true );

// Resolve plugin directory - handles both local and ddev environments
$plugin_dir = dirname( __DIR__ ) . '/';

// Check if we're in the plugin directory itself
if ( file_exists( $plugin_dir . 'csf-parts-catalog.php' ) ) {
	// Running from plugin directory - path is correct
	define( 'CSF_PARTS_PLUGIN_DIR', $plugin_dir );
} elseif ( file_exists( $plugin_dir . '../csf-parts-catalog.php' ) ) {
	// Running from WordPress root (e.g., carpart-scraper-wp/tests)
	// Plugin is one level up from tests parent
	define( 'CSF_PARTS_PLUGIN_DIR', realpath( $plugin_dir . '../' ) . '/' );
} else {
	// Running from ddev WordPress installation
	define( 'CSF_PARTS_PLUGIN_DIR', __DIR__ . '/../../../../' );
}

// Define WordPress constants needed by plugin
if ( ! defined( 'ABSPATH' ) ) {
	define( 'ABSPATH', '/var/www/html/' );
}

// Load Composer autoloader
if ( file_exists( CSF_PARTS_PLUGIN_DIR . 'vendor/autoload.php' ) ) {
	require_once CSF_PARTS_PLUGIN_DIR . 'vendor/autoload.php';
}

// Load plugin files.
require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-constants.php';
require_once CSF_PARTS_PLUGIN_DIR . 'includes/import-sources/interface-import-source-strategy.php';
require_once CSF_PARTS_PLUGIN_DIR . 'includes/import-sources/class-url-import-source.php';
require_once CSF_PARTS_PLUGIN_DIR . 'includes/import-sources/class-directory-import-source.php';
require_once CSF_PARTS_PLUGIN_DIR . 'includes/import-sources/class-import-source-factory.php';
require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-taxonomies.php';

// Load V2 architecture classes
require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-database.php';
require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-url-handler.php';
require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-rest-api.php';
require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-json-importer.php';
require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-ajax-handler.php';
require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-shortcodes.php';

// Mock WordPress functions for testing.
// Note: Common functions like get_option(), __(), _x() are NOT defined here
// because Brain/Monkey needs to mock them in individual tests.
// Only define functions that Brain/Monkey doesn't typically mock.

if ( ! function_exists( 'wp_upload_dir' ) ) {
	function wp_upload_dir(): array {
		return array(
			'path'    => '/tmp/wp-uploads',
			'url'     => 'http://example.com/wp-content/uploads',
			'basedir' => '/tmp/wp-uploads',
			'baseurl' => 'http://example.com/wp-content/uploads',
		);
	}
}

if ( ! function_exists( 'wp_remote_get' ) ) {
	function wp_remote_get( string $url, array $args = array() ) {
		return array(
			'response' => array( 'code' => 200 ),
			'body'     => '{"test": "data"}',
		);
	}
}

if ( ! function_exists( 'wp_remote_retrieve_response_code' ) ) {
	function wp_remote_retrieve_response_code( $response ): int {
		return $response['response']['code'] ?? 200;
	}
}

if ( ! function_exists( 'wp_remote_retrieve_body' ) ) {
	function wp_remote_retrieve_body( $response ): string {
		return $response['body'] ?? '';
	}
}

if ( ! function_exists( 'is_wp_error' ) ) {
	function is_wp_error( $thing ): bool {
		return $thing instanceof WP_Error;
	}
}

// Mock WP_Error class for testing.
if ( ! class_exists( 'WP_Error' ) ) {
	class WP_Error {
		private string $code;
		private string $message;
		private $data;

		public function __construct( string $code = '', string $message = '', $data = '' ) {
			$this->code    = $code;
			$this->message = $message;
			$this->data    = $data;
		}

		public function get_error_code(): string {
			return $this->code;
		}

		public function get_error_message( string $code = '' ): string {
			return $this->message;
		}

		public function get_error_data( string $code = '' ) {
			return $this->data;
		}
	}
}

echo "PHPUnit bootstrap loaded successfully\n";
