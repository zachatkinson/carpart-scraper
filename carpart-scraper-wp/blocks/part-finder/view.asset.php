<?php
/**
 * Asset metadata for the block's view script.
 *
 * WordPress reads this next to view.js so the script URL carries the plugin
 * version instead of the WordPress version, which busts browser caches on
 * every release.
 *
 * @package CSF_Parts_Catalog
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

return array(
	'dependencies' => array(),
	'version'      => defined( 'CSF_PARTS_VERSION' ) ? CSF_PARTS_VERSION : '1.0.0',
);
