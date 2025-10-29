<?php
/**
 * Plugin Name:       CSF Parts Catalog
 * Plugin URI:        https://github.com/zachatkinson/carpart-scraper
 * Description:       Complete automotive parts catalog system with Gutenberg blocks, async search, and JSON import management for CSF MyCarParts data.
 * Version:           1.0.0
 * Requires at least: 6.0
 * Requires PHP:      8.4
 * Author:            Development Team
 * Author URI:        https://github.com/zachatkinson
 * License:           MIT
 * License URI:       https://opensource.org/licenses/MIT
 * Text Domain:       csf-parts
 * Domain Path:       /languages
 *
 * @package CSF_Parts_Catalog
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

/**
 * Plugin version.
 */
define( 'CSF_PARTS_VERSION', '1.0.0' );

/**
 * Plugin root directory.
 */
define( 'CSF_PARTS_PLUGIN_DIR', plugin_dir_path( __FILE__ ) );

/**
 * Plugin root URL.
 */
define( 'CSF_PARTS_PLUGIN_URL', plugin_dir_url( __FILE__ ) );

/**
 * Plugin basename.
 */
define( 'CSF_PARTS_BASENAME', plugin_basename( __FILE__ ) );

/**
 * Autoloader for plugin classes.
 *
 * @param string $class_name The class name to load.
 */
function csf_parts_autoloader( $class_name ) {
	// Check if the class uses our namespace prefix.
	if ( empty( $class_name ) || 0 !== strpos( $class_name, 'CSF_Parts_' ) ) {
		return;
	}

	// Convert class name to file path.
	$class_file = 'class-' . strtolower( str_replace( '_', '-', $class_name ) ) . '.php';
	$file_path  = CSF_PARTS_PLUGIN_DIR . 'includes/' . $class_file;

	// Load the class file if it exists.
	if ( file_exists( $file_path ) ) {
		require_once $file_path;
	}
}
spl_autoload_register( 'csf_parts_autoloader' );

/**
 * Load required core files.
 */
require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-plugin.php';

/**
 * Begins execution of the plugin.
 *
 * @since 1.0.0
 */
function run_csf_parts_catalog() {
	$plugin = CSF_Parts_Plugin::get_instance();
	$plugin->run();
}

// Initialize plugin.
run_csf_parts_catalog();

/**
 * Activation hook.
 *
 * @since 1.0.0
 */
function csf_parts_activate() {
	// Create custom database tables for normalized data storage (V2 architecture).
	require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-database.php';
	$database = new CSF_Parts_Database();
	$database->create_tables();

	// Flush rewrite rules for virtual URLs.
	flush_rewrite_rules();

	// Set default options.
	add_option( 'csf_parts_version', CSF_PARTS_VERSION );
	add_option( 'csf_parts_activation_date', current_time( 'mysql' ) );
}
register_activation_hook( __FILE__, 'csf_parts_activate' );

/**
 * Deactivation hook.
 *
 * @since 1.0.0
 */
function csf_parts_deactivate() {
	// Flush rewrite rules on deactivation.
	flush_rewrite_rules();
}
register_deactivation_hook( __FILE__, 'csf_parts_deactivate' );
