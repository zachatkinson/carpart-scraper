<?php
/**
 * Modern Single Part Template - Shopify-inspired design.
 *
 * SEO-optimized reference catalog page with:
 * - Schema.org structured data
 * - Breadcrumb navigation
 * - Image gallery
 * - Tabbed content
 * - Mobile-responsive design
 *
 * @package CSF_Parts_Catalog
 * @since   2.0.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

// Image helpers kept for theme overrides that still call them.
$get_image_url = function( $image ) {
	$raw_url = '';
	if ( is_array( $image ) && isset( $image['url'] ) ) {
		$raw_url = $image['url'];
	} elseif ( is_string( $image ) ) {
		$raw_url = $image;
	}
	return ! empty( $raw_url ) ? csf_resolve_image_url( $raw_url ) : '';
};

$get_image_alt = function( $image, $fallback ) {
	if ( is_array( $image ) && isset( $image['alt_text'] ) ) {
		return $image['alt_text'];
	}
	return $fallback;
};

// Get first image for meta tags
$first_image_url = ! empty( $images ) ? $get_image_url( $images[0] ) : '';

// Capture searched vehicle from URL parameters for highlighting
// Check both GET params (from catalog filters) AND rewrite vars (from vehicle-specific URLs)
$searched_year  = isset( $_GET['csf_year'] ) ? sanitize_text_field( wp_unslash( $_GET['csf_year'] ) ) : $year;
$searched_make  = isset( $_GET['csf_make'] ) ? sanitize_text_field( wp_unslash( $_GET['csf_make'] ) ) : $make;
$searched_model = isset( $_GET['csf_model'] ) ? sanitize_text_field( wp_unslash( $_GET['csf_model'] ) ) : $model;

// Add Schema.org Structured Data for SEO
add_action( 'wp_footer', function() use ( $title, $part, $first_image_url ) {
	?>
	<!-- Schema.org Structured Data -->
	<script type="application/ld+json">
	{
		"@context": "https://schema.org/",
		"@type": "Product",
		"name": "<?php echo esc_js( $title ); ?>",
		"sku": "<?php echo esc_js( $part->sku ); ?>",
		"description": "<?php echo esc_js( wp_strip_all_tags( $part->description ?? '' ) ); ?>",
		"category": "<?php echo esc_js( $part->category ); ?>",
		<?php if ( ! empty( $first_image_url ) ) : ?>
		"image": "<?php echo esc_js( $first_image_url ); ?>",
		<?php endif; ?>
		<?php if ( $part->manufacturer ) : ?>
		"brand": {
			"@type": "Brand",
			"name": "<?php echo esc_js( $part->manufacturer ); ?>"
		},
		<?php endif; ?>
		"offers": {
			"@type": "Offer",
			"availability": "https://schema.org/InStock",
			"priceCurrency": "USD"
		}
	}
	</script>
	<?php
} );

// Use WordPress's theme system - handles both traditional and block themes
get_header();
?>

<div class="csf-part-modern">
	<?php echo CSF_Parts_Part_Layout::render( $view ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Block output, escaped per block. ?>
</div>

<?php
// Use WordPress's theme system - handles both traditional and block themes
get_footer();
