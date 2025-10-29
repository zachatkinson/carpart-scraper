<?php
/**
 * Shortcodes for CSF Parts Catalog.
 *
 * Provides shortcodes for displaying parts search, grids, and single products.
 *
 * @package CSF_Parts_Catalog
 * @since   2.0.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

/**
 * Class CSF_Parts_Shortcodes
 *
 * Handles all plugin shortcodes.
 */
class CSF_Parts_Shortcodes {

	/**
	 * Constructor.
	 */
	public function __construct() {
		add_action( 'init', array( $this, 'register_shortcodes' ) );
	}

	/**
	 * Register all shortcodes.
	 *
	 * @since 2.0.0
	 */
	public function register_shortcodes(): void {
		add_shortcode( 'csf_parts_search', array( $this, 'render_search' ) );
		add_shortcode( 'csf_parts_grid', array( $this, 'render_grid' ) );
		add_shortcode( 'csf_single_part', array( $this, 'render_single_part' ) );
		add_shortcode( 'csf_vehicle_selector', array( $this, 'render_vehicle_selector' ) );
	}

	/**
	 * Render async search shortcode.
	 *
	 * Usage: [csf_parts_search filters="true" per_page="20"]
	 *
	 * @since  2.0.0
	 * @param  array $atts Shortcode attributes.
	 * @return string Shortcode output.
	 */
	public function render_search( $atts ): string {
		$atts = shortcode_atts(
			array(
				'filters'     => 'true',
				'per_page'    => '20',
				'min_length'  => '2',
				'debounce'    => '300',
				'placeholder' => 'Search parts by name or SKU...',
			),
			$atts,
			'csf_parts_search'
		);

		// Ensure assets are enqueued.
		$this->enqueue_search_assets();

		// Generate unique ID for this search instance.
		static $instance = 0;
		$instance++;
		$container_id = 'csf-search-' . $instance;

		// Build data attributes for configuration.
		$data_attrs = sprintf(
			'data-csf-search data-show-filters="%s" data-per-page="%s" data-min-search-length="%s" data-debounce-delay="%s"',
			esc_attr( $atts['filters'] ),
			esc_attr( $atts['per_page'] ),
			esc_attr( $atts['min_length'] ),
			esc_attr( $atts['debounce'] )
		);

		// Return search container.
		return sprintf(
			'<div id="%s" class="csf-search-container" %s></div>',
			esc_attr( $container_id ),
			$data_attrs
		);
	}

	/**
	 * Render parts grid shortcode.
	 *
	 * Usage: [csf_parts_grid category="Radiators" limit="12"]
	 *
	 * @since  2.0.0
	 * @param  array $atts Shortcode attributes.
	 * @return string Shortcode output.
	 */
	public function render_grid( $atts ): string {
		$atts = shortcode_atts(
			array(
				'category' => '',
				'make'     => '',
				'model'    => '',
				'year'     => '',
				'limit'    => '12',
				'columns'  => '3',
			),
			$atts,
			'csf_parts_grid'
		);

		// Enqueue styles.
		wp_enqueue_style( 'csf-parts-public' );

		// Build API parameters.
		$params = array(
			'per_page' => intval( $atts['limit'] ),
		);

		if ( ! empty( $atts['category'] ) ) {
			$params['category'] = sanitize_text_field( $atts['category'] );
		}
		if ( ! empty( $atts['make'] ) ) {
			$params['make'] = sanitize_text_field( $atts['make'] );
		}
		if ( ! empty( $atts['model'] ) ) {
			$params['model'] = sanitize_text_field( $atts['model'] );
		}
		if ( ! empty( $atts['year'] ) ) {
			$params['year'] = intval( $atts['year'] );
		}

		// Fetch parts from REST API.
		$response = wp_remote_get(
			add_query_arg( $params, rest_url( 'csf/v1/parts' ) ),
			array(
				'timeout' => 10,
			)
		);

		if ( is_wp_error( $response ) ) {
			return '<p class="csf-error">Failed to load parts.</p>';
		}

		$data = json_decode( wp_remote_retrieve_body( $response ), true );
		if ( empty( $data['parts'] ) ) {
			return '<p class="csf-empty">No parts found.</p>';
		}

		// Build grid HTML.
		$columns_class = 'csf-grid-cols-' . esc_attr( $atts['columns'] );
		$output        = '<div class="csf-parts-grid ' . $columns_class . '">';

		foreach ( $data['parts'] as $part ) {
			$output .= $this->render_part_card( $part );
		}

		$output .= '</div>';

		return $output;
	}

	/**
	 * Render single part shortcode.
	 *
	 * Usage: [csf_single_part sku="CSF-12345"]
	 *
	 * @since  2.0.0
	 * @param  array $atts Shortcode attributes.
	 * @return string Shortcode output.
	 */
	public function render_single_part( $atts ): string {
		$atts = shortcode_atts(
			array(
				'sku' => '',
			),
			$atts,
			'csf_single_part'
		);

		if ( empty( $atts['sku'] ) ) {
			return '<p class="csf-error">SKU is required.</p>';
		}

		// Enqueue styles.
		wp_enqueue_style( 'csf-parts-public' );

		// Fetch part from REST API.
		$response = wp_remote_get(
			rest_url( 'csf/v1/parts/' . urlencode( $atts['sku'] ) ),
			array(
				'timeout' => 10,
			)
		);

		if ( is_wp_error( $response ) ) {
			return '<p class="csf-error">Failed to load part.</p>';
		}

		$status_code = wp_remote_retrieve_response_code( $response );
		if ( 404 === $status_code ) {
			return '<p class="csf-error">Part not found.</p>';
		}

		$part = json_decode( wp_remote_retrieve_body( $response ), true );
		if ( empty( $part ) ) {
			return '<p class="csf-error">Invalid part data.</p>';
		}

		// Render detailed part view.
		return $this->render_part_detail( $part );
	}

	/**
	 * Render vehicle selector shortcode.
	 *
	 * Usage: [csf_vehicle_selector]
	 *
	 * @since  2.0.0
	 * @param  array $atts Shortcode attributes.
	 * @return string Shortcode output.
	 */
	public function render_vehicle_selector( $atts ): string {
		$atts = shortcode_atts(
			array(
				'redirect' => 'true',
			),
			$atts,
			'csf_vehicle_selector'
		);

		// Enqueue search assets (includes vehicle selector functionality).
		$this->enqueue_search_assets();

		// Generate unique ID.
		static $instance = 0;
		$instance++;
		$container_id = 'csf-vehicle-selector-' . $instance;

		return sprintf(
			'<div id="%s" class="csf-vehicle-selector" data-redirect="%s"></div>',
			esc_attr( $container_id ),
			esc_attr( $atts['redirect'] )
		);
	}

	/**
	 * Enqueue search assets.
	 *
	 * @since 2.0.0
	 */
	private function enqueue_search_assets(): void {
		// Only enqueue once.
		static $enqueued = false;
		if ( $enqueued ) {
			return;
		}
		$enqueued = true;

		// Enqueue CSS.
		wp_enqueue_style(
			'csf-parts-public',
			CSF_PARTS_PLUGIN_URL . 'public/css/frontend-styles.css',
			array(),
			CSF_PARTS_VERSION,
			'all'
		);

		// Enqueue JS.
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
				'restUrl' => rest_url( 'csf/v1/' ),
				'nonce'   => wp_create_nonce( 'wp_rest' ),
				'ajaxUrl' => admin_url( 'admin-ajax.php' ),
			)
		);
	}

	/**
	 * Render part card HTML.
	 *
	 * @since  2.0.0
	 * @param  array $part Part data.
	 * @return string Card HTML.
	 */
	private function render_part_card( array $part ): string {
		$price      = ! empty( $part['price'] ) ? '$' . number_format( (float) $part['price'], 2 ) : 'Contact for price';
		$stock_text = ! empty( $part['in_stock'] ) ? 'In Stock' : 'Out of Stock';
		$stock_class = ! empty( $part['in_stock'] ) ? 'in-stock' : 'out-of-stock';

		ob_start();
		?>
		<article class="csf-part-card">
			<a href="<?php echo esc_url( $part['link'] ); ?>" class="csf-part-card__link">
				<?php if ( ! empty( $part['image'] ) ) : ?>
					<div class="csf-part-card__image">
						<img src="<?php echo esc_url( $part['image'] ); ?>" alt="<?php echo esc_attr( $part['name'] ); ?>" loading="lazy" />
					</div>
				<?php else : ?>
					<div class="csf-part-card__image csf-part-card__image--placeholder">
						<svg width="48" height="48" viewBox="0 0 20 20" fill="currentColor" opacity="0.2">
							<path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd"/>
						</svg>
					</div>
				<?php endif; ?>
				<div class="csf-part-card__content">
					<p class="csf-part-card__category"><?php echo esc_html( $part['category'] ); ?></p>
					<h3 class="csf-part-card__title"><?php echo esc_html( $part['name'] ); ?></h3>
					<p class="csf-part-card__sku">SKU: <?php echo esc_html( $part['sku'] ); ?></p>
					<?php if ( ! empty( $part['manufacturer'] ) ) : ?>
						<p class="csf-part-card__manufacturer"><?php echo esc_html( $part['manufacturer'] ); ?></p>
					<?php endif; ?>
					<div class="csf-part-card__footer">
						<span class="csf-part-card__price"><?php echo esc_html( $price ); ?></span>
						<span class="csf-part-card__stock csf-part-card__stock--<?php echo esc_attr( $stock_class ); ?>">
							<?php echo esc_html( $stock_text ); ?>
						</span>
					</div>
				</div>
			</a>
		</article>
		<?php
		return ob_get_clean();
	}

	/**
	 * Render detailed part view.
	 *
	 * @since  2.0.0
	 * @param  array $part Part data with full details.
	 * @return string Detail HTML.
	 */
	private function render_part_detail( array $part ): string {
		$price      = ! empty( $part['price'] ) ? '$' . number_format( (float) $part['price'], 2 ) : 'Contact for price';
		$stock_text = ! empty( $part['in_stock'] ) ? 'In Stock' : 'Out of Stock';
		$stock_class = ! empty( $part['in_stock'] ) ? 'in-stock' : 'out-of-stock';

		ob_start();
		?>
		<div class="csf-part-detail">
			<div class="csf-part-detail__header">
				<div class="csf-part-detail__images">
					<?php if ( ! empty( $part['images'] ) ) : ?>
						<div class="csf-part-detail__image-main">
							<img src="<?php echo esc_url( $part['images'][0]['url'] ); ?>" alt="<?php echo esc_attr( $part['name'] ); ?>" />
						</div>
						<?php if ( count( $part['images'] ) > 1 ) : ?>
							<div class="csf-part-detail__image-thumbs">
								<?php foreach ( $part['images'] as $image ) : ?>
									<img src="<?php echo esc_url( $image['url'] ); ?>" alt="<?php echo esc_attr( $part['name'] ); ?>" />
								<?php endforeach; ?>
							</div>
						<?php endif; ?>
					<?php else : ?>
						<div class="csf-part-detail__image-placeholder">
							<svg width="128" height="128" viewBox="0 0 20 20" fill="currentColor" opacity="0.2">
								<path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd"/>
							</svg>
						</div>
					<?php endif; ?>
				</div>
				<div class="csf-part-detail__info">
					<p class="csf-part-detail__category"><?php echo esc_html( $part['category'] ); ?></p>
					<h1 class="csf-part-detail__title"><?php echo esc_html( $part['name'] ); ?></h1>
					<p class="csf-part-detail__sku">SKU: <code><?php echo esc_html( $part['sku'] ); ?></code></p>
					<?php if ( ! empty( $part['manufacturer'] ) ) : ?>
						<p class="csf-part-detail__manufacturer">Manufacturer: <?php echo esc_html( $part['manufacturer'] ); ?></p>
					<?php endif; ?>
					<div class="csf-part-detail__pricing">
						<span class="csf-part-detail__price"><?php echo esc_html( $price ); ?></span>
						<span class="csf-part-detail__stock csf-part-detail__stock--<?php echo esc_attr( $stock_class ); ?>">
							<?php echo esc_html( $stock_text ); ?>
						</span>
					</div>
					<?php if ( ! empty( $part['description'] ) ) : ?>
						<div class="csf-part-detail__description">
							<?php echo wp_kses_post( $part['description'] ); ?>
						</div>
					<?php endif; ?>
				</div>
			</div>

			<?php if ( ! empty( $part['specifications'] ) ) : ?>
				<div class="csf-part-detail__specifications">
					<h2>Specifications</h2>
					<dl>
						<?php foreach ( $part['specifications'] as $key => $value ) : ?>
							<dt><?php echo esc_html( ucfirst( str_replace( '_', ' ', $key ) ) ); ?></dt>
							<dd><?php echo esc_html( $value ); ?></dd>
						<?php endforeach; ?>
					</dl>
				</div>
			<?php endif; ?>

			<?php if ( ! empty( $part['features'] ) ) : ?>
				<div class="csf-part-detail__features">
					<h2>Features</h2>
					<ul>
						<?php foreach ( $part['features'] as $feature ) : ?>
							<li><?php echo esc_html( $feature ); ?></li>
						<?php endforeach; ?>
					</ul>
				</div>
			<?php endif; ?>

			<?php if ( ! empty( $part['compatibility'] ) ) : ?>
				<div class="csf-part-detail__compatibility">
					<h2>Vehicle Compatibility</h2>
					<div class="csf-compatibility-list">
						<?php foreach ( $part['compatibility'] as $vehicle ) : ?>
							<div class="csf-compatibility-item">
								<?php echo esc_html( $vehicle['year'] . ' ' . $vehicle['make'] . ' ' . $vehicle['model'] ); ?>
							</div>
						<?php endforeach; ?>
					</div>
				</div>
			<?php endif; ?>
		</div>
		<?php
		return ob_get_clean();
	}
}
