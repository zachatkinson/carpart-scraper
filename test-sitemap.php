<?php
/**
 * Test script to debug sitemap provider.
 * Run via: ddev wp eval-file test-sitemap.php
 */

// Load classes
require_once __DIR__ . '/includes/class-csf-parts-database.php';
require_once __DIR__ . '/includes/class-csf-parts-url-handler.php';
require_once __DIR__ . '/includes/class-csf-parts-sitemap-provider.php';

echo "=== Testing Sitemap Provider ===\n\n";

// Create provider instance
$provider = new CSF_Parts_Sitemap_Provider();

echo "1. Testing get_max_num_pages():\n";
$max_pages = $provider->get_max_num_pages();
echo "   Max pages: " . $max_pages . "\n\n";

echo "2. Testing get_url_list(1):\n";
$urls = $provider->get_url_list( 1 );
echo "   URL count: " . count( $urls ) . "\n";

if ( ! empty( $urls ) ) {
	echo "   First 3 URLs:\n";
	foreach ( array_slice( $urls, 0, 3 ) as $url_data ) {
		echo "   - " . $url_data['loc'] . "\n";
	}
} else {
	echo "   ERROR: No URLs returned!\n";
}

echo "\n3. Testing URL handler directly:\n";
$url_handler = new CSF_Parts_URL_Handler();
$all_urls    = $url_handler->get_all_virtual_urls();
echo "   Total virtual URLs: " . count( $all_urls ) . "\n";

if ( ! empty( $all_urls ) ) {
	echo "   First 3 URLs:\n";
	foreach ( array_slice( $all_urls, 0, 3 ) as $url ) {
		echo "   - " . $url . "\n";
	}
}

echo "\n✅ Test completed!\n";
