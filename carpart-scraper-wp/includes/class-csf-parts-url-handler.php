<?php
/**
 * Virtual URL Handler for Dynamic Part Pages.
 *
 * Creates SEO-friendly virtual URLs that generate pages dynamically from database.
 * Handles both canonical pages (SKU-only) and vehicle-specific variations.
 *
 * @package CSF_Parts_Catalog
 * @since   2.0.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

/**
 * Class CSF_Parts_URL_Handler
 */
class CSF_Parts_URL_Handler {

	/**
	 * Database instance.
	 *
	 * @var CSF_Parts_Database
	 */
	private $database;

	/**
	 * Constructor.
	 */
	public function __construct() {
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-database.php';
		$this->database = new CSF_Parts_Database();

		// Register rewrite rules.
		add_action( 'init', array( $this, 'register_rewrite_rules' ) );

		// Add query vars.
		add_filter( 'query_vars', array( $this, 'add_query_vars' ) );

		// Handle template loading.
		add_action( 'template_redirect', array( $this, 'handle_virtual_page' ) );
	}

	/**
	 * Register rewrite rules for virtual part URLs.
	 *
	 * URL Patterns:
	 * - Canonical: /parts/{category}-{sku}  (e.g., /parts/radiator-csf-3411)
	 * - Vehicle:   /parts/{year}-{make}-{model}-{category}-{sku}
	 *
	 * @since 2.0.0
	 */
	public function register_rewrite_rules(): void {
		// Vehicle-specific part URL (most specific, match first).
		// Example: /parts/2006-honda-civic-radiator-csf-3411.
		add_rewrite_rule(
			'^parts/([0-9]{4})-([^/-]+)-([^/-]+)-([^/-]+)-(.+)/?$',
			'index.php?csf_part=1&csf_year=$matches[1]&csf_make=$matches[2]&csf_model=$matches[3]&csf_category=$matches[4]&csf_sku=$matches[5]',
			'top'
		);

		// Canonical part URL (SKU-based).
		// Example: /parts/radiator-csf-3411.
		add_rewrite_rule(
			'^parts/([^-]+)-(.+)/?$',
			'index.php?csf_part=1&csf_category=$matches[1]&csf_sku=$matches[2]',
			'top'
		);

		// Parts archive/category pages.
		add_rewrite_rule(
			'^parts/category/([^/]+)/?$',
			'index.php?csf_category_archive=$matches[1]',
			'top'
		);

		// Parts search.
		add_rewrite_rule(
			'^parts/search/([^/]+)/?$',
			'index.php?csf_search=$matches[1]',
			'top'
		);
	}

	/**
	 * Add custom query variables.
	 *
	 * @since 2.0.0
	 * @param array $vars Existing query vars.
	 * @return array Modified query vars.
	 */
	public function add_query_vars( $vars ): array {
		$vars[] = 'csf_part';
		$vars[] = 'csf_sku';
		$vars[] = 'csf_category';
		$vars[] = 'csf_year';
		$vars[] = 'csf_make';
		$vars[] = 'csf_model';
		$vars[] = 'csf_category_archive';
		$vars[] = 'csf_search';

		return $vars;
	}

	/**
	 * Handle virtual page display.
	 *
	 * Checks if request is for a virtual part page and renders it.
	 *
	 * @since 2.0.0
	 */
	public function handle_virtual_page(): void {
		// Check if this is a CSF part request.
		if ( ! get_query_var( 'csf_part' ) ) {
			return;
		}

		$sku = get_query_var( 'csf_sku' );
		if ( empty( $sku ) ) {
			$this->render_404();
			return;
		}

		// Load part from database.
		$part = $this->database->get_part_by_sku( $sku );
		if ( ! $part ) {
			$this->render_404();
			return;
		}

		// Mark as successful page load (not 404).
		global $wp_query;
		$wp_query->is_404 = false;
		status_header( 200 );

		// Get vehicle context (if specified).
		$year  = get_query_var( 'csf_year' );
		$make  = get_query_var( 'csf_make' );
		$model = get_query_var( 'csf_model' );

		// Render part page.
		$this->render_part_page( $part, $year, $make, $model );
		exit;
	}

	/**
	 * Render part page dynamically.
	 *
	 * @since 2.0.0
	 * @param object $part  Part data from database.
	 * @param string $year  Vehicle year (optional).
	 * @param string $make  Vehicle make (optional).
	 * @param string $model Vehicle model (optional).
	 */
	private function render_part_page( object $part, string $year = '', string $make = '', string $model = '' ): void {
		// Decode JSON fields.
		$compatibility  = ! empty( $part->compatibility ) ? json_decode( $part->compatibility, true ) : array();
		$specifications = ! empty( $part->specifications ) ? json_decode( $part->specifications, true ) : array();
		$features       = ! empty( $part->features ) ? json_decode( $part->features, true ) : array();
		$images         = ! empty( $part->images ) ? json_decode( $part->images, true ) : array();

		// Determine if this is canonical or vehicle-specific page.
		$is_vehicle_specific = ! empty( $year ) && ! empty( $make ) && ! empty( $model );

		// Singularize category for part title (Radiators -> Radiator).
		$category_singular = rtrim( $part->category, 's' );

		// Generate page title.
		if ( $is_vehicle_specific ) {
			$title = sprintf(
				'%s %s %s %s — %s',
				sanitize_text_field( $year ),
				sanitize_text_field( ucwords( str_replace( '-', ' ', $make ) ) ),
				sanitize_text_field( ucwords( str_replace( '-', ' ', $model ) ) ),
				sanitize_text_field( $category_singular ),
				sanitize_text_field( $part->sku )
			);
		} else {
			$title = sprintf(
				'%s — %s',
				sanitize_text_field( $category_singular ),
				sanitize_text_field( $part->sku )
			);
		}

		// Generate canonical URL (always points to generic SKU page with singular category).
		$canonical_url = home_url( sprintf(
			'/parts/%s-%s',
			sanitize_title( $category_singular ),
			sanitize_title( $part->sku )
		) );

		// Generate meta description.
		$meta_description = sprintf(
			'%s for %s. Price: $%s. In stock and ready to ship. %s',
			esc_attr( $part->category ),
			esc_attr( $part->manufacturer ),
			esc_attr( number_format( $part->price, 2 ) ),
			esc_attr( wp_trim_words( $part->description, 20 ) )
		);

		// Set WordPress document title via filter.
		add_filter( 'pre_get_document_title', function() use ( $title ) {
			return $title;
		}, 10 );

		// Add SEO meta tags and Schema.org via wp_head hook.
		add_action( 'wp_head', function() use ( $canonical_url, $meta_description, $title, $part, $images ) {
			echo "\n<!-- CSF Parts SEO Meta Tags -->\n";
			echo '<meta name="description" content="' . esc_attr( $meta_description ) . '">' . "\n";
			echo '<link rel="canonical" href="' . esc_url( $canonical_url ) . '">' . "\n";

			// Schema.org Product markup.
			$schema_product = array(
				'@context'    => 'https://schema.org/',
				'@type'       => 'Product',
				'name'        => $title,
				'sku'         => $part->sku,
				'description' => wp_strip_all_tags( $part->description ),
				'brand'       => array(
					'@type' => 'Brand',
					'name'  => $part->manufacturer,
				),
				'offers'      => array(
					'@type'         => 'Offer',
					'price'         => $part->price,
					'priceCurrency' => 'USD',
					'availability'  => $part->in_stock ? 'https://schema.org/InStock' : 'https://schema.org/OutOfStock',
					'url'           => $canonical_url,
				),
			);

			if ( ! empty( $images ) && isset( $images[0]['url'] ) ) {
				$schema_product['image'] = $images[0]['url'];
			}

			echo '<script type="application/ld+json">' . "\n";
			echo wp_json_encode( $schema_product, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) . "\n";
			echo '</script>' . "\n";

			// Open Graph tags.
			echo '<meta property="og:type" content="product">' . "\n";
			echo '<meta property="og:title" content="' . esc_attr( $title ) . '">' . "\n";
			echo '<meta property="og:description" content="' . esc_attr( $meta_description ) . '">' . "\n";
			echo '<meta property="og:url" content="' . esc_url( get_site_url() . $_SERVER['REQUEST_URI'] ) . '">' . "\n";
			if ( ! empty( $images ) && isset( $images[0]['url'] ) ) {
				echo '<meta property="og:image" content="' . esc_url( $images[0]['url'] ) . '">' . "\n";
			}
		}, 1 );

		// Set template variables for use in template file.
		$template_vars = compact( 'part', 'title', 'canonical_url', 'compatibility', 'specifications', 'features', 'images', 'is_vehicle_specific', 'year', 'make', 'model' );

		// Load template.
		$this->load_template( 'part-single', $template_vars );
	}

	/**
	 * Load template file with variables.
	 *
	 * @since 2.0.0
	 * @param string $template_name Template name (without .php).
	 * @param array  $vars          Variables to extract into template scope.
	 */
	private function load_template( string $template_name, array $vars = array() ): void {
		// Extract variables into local scope.
		extract( $vars ); // phpcs:ignore WordPress.PHP.DontExtract.extract_extract

		// Check theme override first.
		$theme_template = locate_template( array( "csf-parts/{$template_name}.php" ) );

		if ( $theme_template ) {
			include $theme_template;
		} else {
			// Load plugin template.
			$plugin_template = CSF_PARTS_PLUGIN_DIR . "templates/{$template_name}.php";
			if ( file_exists( $plugin_template ) ) {
				include $plugin_template;
			}
		}
	}

	/**
	 * Render 404 page.
	 *
	 * @since 2.0.0
	 */
	private function render_404(): void {
		global $wp_query;
		$wp_query->set_404();
		status_header( 404 );
		get_template_part( 404 );
		exit;
	}

	/**
	 * Get all virtual URLs for sitemap generation.
	 *
	 * @since 2.0.0
	 * @return array Array of URLs.
	 */
	public function get_all_virtual_urls(): array {
		global $wpdb;
		$table = $wpdb->prefix . 'csf_parts';

		$parts = $wpdb->get_results( "SELECT sku, category, compatibility FROM {$table}" );

		$urls = array();

		foreach ( $parts as $part ) {
			$compatibility = ! empty( $part->compatibility ) ? json_decode( $part->compatibility, true ) : array();

			// Singularize category for URLs.
			$category_singular = rtrim( $part->category, 's' );

			// Add canonical URL.
			$urls[] = home_url( sprintf(
				'/parts/%s-%s',
				sanitize_title( $category_singular ),
				sanitize_title( $part->sku )
			) );

			// Add vehicle-specific URLs.
			foreach ( $compatibility as $vehicle ) {
				$year  = $vehicle['year'] ?? '';
				$make  = $vehicle['make'] ?? '';
				$model = $vehicle['model'] ?? '';

				if ( $year && $make && $model ) {
					$urls[] = home_url( sprintf(
						'/parts/%s-%s-%s-%s-%s',
						$year,
						sanitize_title( $make ),
						sanitize_title( $model ),
						sanitize_title( $category_singular ),
						sanitize_title( $part->sku )
					) );
				}
			}
		}

		return $urls;
	}
}
