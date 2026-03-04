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

// Helper functions for image handling (supports both array and string formats)
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

	<!-- Breadcrumbs with Schema -->
	<nav class="csf-breadcrumbs" aria-label="Breadcrumb">
		<ol itemscope itemtype="https://schema.org/BreadcrumbList">
			<li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem">
				<a itemprop="item" href="<?php echo esc_url( home_url( '/' ) ); ?>">
					<span itemprop="name">Home</span>
				</a>
				<meta itemprop="position" content="1" />
			</li>
			<li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem">
				<a itemprop="item" href="<?php echo esc_url( home_url( '/parts/' ) ); ?>">
					<span itemprop="name">Parts</span>
				</a>
				<meta itemprop="position" content="2" />
			</li>
			<li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem">
				<a itemprop="item" href="<?php echo esc_url( home_url( '/parts/?csf_category=' . urlencode( $part->category ) ) ); ?>">
					<span itemprop="name"><?php echo esc_html( $part->category ); ?></span>
				</a>
				<meta itemprop="position" content="3" />
			</li>
			<li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem">
				<span itemprop="name"><?php echo esc_html( csf_format_sku_display( $part->sku ) ); ?></span>
				<meta itemprop="position" content="4" />
			</li>
		</ol>
	</nav>

	<!-- Product Grid: Two-Column Layout -->
	<div class="csf-product-grid">

		<!-- Left Column: Image Gallery -->
		<div class="csf-product-gallery">
			<?php if ( ! empty( $images ) ) : ?>
				<?php
				$first_image_url = $get_image_url( $images[0] );
				$first_image_alt = $get_image_alt( $images[0], $title );
				?>

				<!-- Main Image -->
				<div class="csf-gallery-main">
					<?php if ( ! empty( $first_image_url ) ) : ?>
						<img
							id="csf-main-image"
							src="<?php echo esc_url( $first_image_url ); ?>"
							alt="<?php echo esc_attr( $first_image_alt ); ?>"
							class="csf-main-image"
						>
					<?php else : ?>
						<div class="csf-no-image-placeholder">
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
								<rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
								<circle cx="8.5" cy="8.5" r="1.5"></circle>
								<polyline points="21 15 16 10 5 21"></polyline>
							</svg>
							<p>No image available</p>
						</div>
					<?php endif; ?>
				</div>

				<!-- Thumbnail Gallery -->
				<?php if ( count( $images ) > 1 ) : ?>
					<div class="csf-gallery-thumbs">
						<?php foreach ( $images as $index => $image ) : ?>
							<?php
							$thumb_url = $get_image_url( $image );
							$thumb_alt = $get_image_alt( $image, $title );
							?>
							<?php if ( ! empty( $thumb_url ) ) : ?>
								<button
									class="csf-thumb <?php echo 0 === $index ? 'active' : ''; ?>"
									onclick="csfSwitchImage('<?php echo esc_js( $thumb_url ); ?>', this)"
									aria-label="View image <?php echo esc_attr( $index + 1 ); ?>"
								>
									<img
										src="<?php echo esc_url( $thumb_url ); ?>"
										alt="<?php echo esc_attr( $thumb_alt ); ?>"
									>
								</button>
							<?php endif; ?>
						<?php endforeach; ?>
					</div>
				<?php endif; ?>
			<?php else : ?>
				<div class="csf-no-image-placeholder">
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
						<circle cx="8.5" cy="8.5" r="1.5"></circle>
						<polyline points="21 15 16 10 5 21"></polyline>
					</svg>
					<p>No image available</p>
				</div>
			<?php endif; ?>
		</div>

		<!-- Right Column: Product Info -->
		<div class="csf-product-info">

			<!-- Discontinued Badge (if applicable) -->
			<?php if ( ! empty( $part->discontinued ) && 1 === (int) $part->discontinued ) : ?>
				<div class="csf-category-badge">
					<span class="csf-badge csf-discontinued-badge" style="display: inline-block; padding: 6px 14px; background: transparent; color: var(--global-palette1, #C41C10); border: 2px solid var(--global-palette1, #C41C10); font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; border-radius: 20px;">DISCONTINUED</span>
				</div>
			<?php endif; ?>

			<!-- Product Title -->
			<h1 class="csf-product-title">
				<?php echo esc_html( str_replace( '-', '', $part->sku ) ); ?>
			</h1>

			<!-- Manufacturer -->

			<!-- Your Vehicle Box (if applicable) -->
			<?php if ( $is_vehicle_specific ) : ?>
				<?php
				// Extract unique engine variants for this specific YMM
				$engine_variants = array();
				if ( ! empty( $compatibility ) && is_array( $compatibility ) ) {
					foreach ( $compatibility as $vehicle ) {
						// Match the searched YMM
						$year_match  = empty( $year ) || (string) $vehicle['year'] === (string) $year;
						$make_match  = empty( $make ) || strcasecmp( $vehicle['make'], $make ) === 0;
						$model_match = empty( $model ) || strcasecmp( $vehicle['model'], $model ) === 0;

						if ( $year_match && $make_match && $model_match ) {
							$engine = isset( $vehicle['engine'] ) && ! empty( $vehicle['engine'] ) ? $vehicle['engine'] : '';
							if ( $engine && ! in_array( $engine, $engine_variants, true ) ) {
								$engine_variants[] = $engine;
							}
						}
					}
				}

				// Sort engine variants naturally
				sort( $engine_variants );
				?>
				<div class="csf-your-vehicle-box">
					<div class="your-vehicle-header">
						<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
							<path d="M5 17h14v-5H5v5z"></path>
							<path d="M7 18v2"></path>
							<path d="M17 18v2"></path>
							<path d="M2 8l2-3h16l2 3"></path>
						</svg>
						<strong>Your Vehicle</strong>
					</div>
					<div class="your-vehicle-ymm">
						<?php echo esc_html( "$year $make $model" ); ?>
					</div>
					<?php if ( count( $engine_variants ) > 1 ) : ?>
						<div class="your-vehicle-engine-selector">
						<div class="engine-notice">
							<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
								<circle cx="12" cy="12" r="10"></circle>
								<line x1="12" y1="16" x2="12" y2="12"></line>
								<line x1="12" y1="8" x2="12.01" y2="8"></line>
							</svg>
							<div style="line-height: 1.4;">
								<strong style="display: block; margin-bottom: 4px;">Please select your vehicle's engine.</strong>
								<span style="font-size: 13px; font-style: italic;">Unsure? Contact your local dealer or distributor to verify this part fits your specific vehicle configuration.</span>
							</div>
						</div>
							<label for="csf-engine-variant">Select Engine:</label>
							<?php
							// Use helper function for consistent dropdown rendering.
							echo csf_render_select(
								array(
									'id'           => 'csf-engine-variant',
									'name'         => 'csf_engine',
									'options'      => array_combine( $engine_variants, $engine_variants ),
									'placeholder'  => 'Not Sure / Don\'t Know',
									'class'        => 'csf-engine-variant-dropdown',
									'show_wrapper' => false,
								)
							);
							?>
						</div>
					<?php elseif ( count( $engine_variants ) === 1 ) : ?>
						<div class="your-vehicle-engine-single">
							<span class="engine-label">Engine:</span>
							<span class="engine-value"><?php echo esc_html( $engine_variants[0] ); ?></span>
						</div>
						<div class="engine-verify-notice" style="margin-top: 8px; padding: 8px 12px; background: var(--global-palette8, #F7FAFC); border-left: 3px solid var(--global-palette5, #4A5568); border-radius: 0 4px 4px 0; font-size: 13px; color: var(--global-palette5, #4A5568);">
							Please verify this matches your vehicle's engine before purchasing.
						</div>
					<?php endif; ?>
				</div>
			<?php endif; ?>

			<!-- Quick Specs Highlights -->
			<?php if ( ! empty( $specifications ) ) : ?>
				<div class="csf-quick-specs">
					<h3>Key Specifications</h3>
					<ul>
						<?php
						// First, display Part Type (category)
						$part_type_value = null;
						foreach ( $specifications as $key => $value ) {
							if ( preg_match( '/^(CSF-?)?\d+$/', $key ) ) {
								$part_type_value = $value;
								break;
							}
						}
						if ( $part_type_value ) :
						?>
							<li>
								<span class="spec-label">Part Type:</span>
								<span class="spec-value"><?php echo esc_html( $part_type_value ); ?></span>
							</li>
						<?php endif; ?>

						<?php
						// Define key spec fields with possible field name variations and display labels.
						// Each entry: 'Display Label' => ['field_name_1', 'field_name_2', ...]
						$key_spec_definitions = array(
							'Construction'    => array( 'Construction' ),
							'Core Length'     => array( 'Core Length (in)', 'Core Length' ),
							'Core Thickness'  => array( 'Core Thickness (in)', 'Core Thickness' ),
							'Core Width'      => array( 'Core Width (in)', 'Core Width' ),
							'Flow'            => array( 'Flow', 'Flow Type', 'Flow Direction', 'Cross-flow/Down-flow' ),
							'Number of Rows'  => array( 'Number of Rows', '# of Rows', 'Rows', 'Row Count', 'No. Of Rows' ),
							'Tank Material'   => array( 'Tank Material' ),
						);

						// Fields that should be capitalized (not formatted as dimensions).
						$capitalize_fields = array( 'Construction', 'Tank Material', 'Flow', 'Number of Rows' );

						// Find matching specs and collect them.
						$found_specs = array();
						foreach ( $key_spec_definitions as $label => $possible_fields ) {
							foreach ( $possible_fields as $field_name ) {
								if ( isset( $specifications[ $field_name ] ) && ! empty( $specifications[ $field_name ] ) ) {
									$found_specs[ $label ] = array(
										'value'      => $specifications[ $field_name ],
										'capitalize' => in_array( $label, $capitalize_fields, true ),
									);
									break; // Stop at first match.
								}
							}
						}

						// Handle Inlet/Outlet specially — combine Length × Width when both exist.
						foreach ( array( 'Inlet', 'Outlet' ) as $port_label ) {
							// Prefer descriptive text values first.
							$text_fields = array( "{$port_label} Size", "{$port_label} Tube", $port_label );
							$found_text  = false;
							foreach ( $text_fields as $field_name ) {
								if ( isset( $specifications[ $field_name ] ) && ! empty( $specifications[ $field_name ] ) ) {
									$found_specs[ $port_label ] = array(
										'value'      => $specifications[ $field_name ],
										'capitalize' => true,
									);
									$found_text = true;
									break;
								}
							}

							// If no text value, combine Length × Width dimensions.
							if ( ! $found_text ) {
								$length = $specifications[ "{$port_label} Length (in)" ] ?? '';
								$width  = $specifications[ "{$port_label} Width (in)" ] ?? '';
								if ( ! empty( $length ) && ! empty( $width ) ) {
									$found_specs[ $port_label ] = array(
										'value'      => trim( $length ) . '" × ' . trim( $width ) . '"',
										'capitalize' => false,
									);
								} elseif ( ! empty( $length ) ) {
									$found_specs[ $port_label ] = array(
										'value'      => $length,
										'capitalize' => false,
									);
								} elseif ( ! empty( $width ) ) {
									$found_specs[ $port_label ] = array(
										'value'      => $width,
										'capitalize' => false,
									);
								}
							}
						}

						// Sort alphabetically by label
						ksort( $found_specs );

						// Display specs (limit to 8 for visual balance)
						$count = 0;
						foreach ( $found_specs as $label => $spec_data ) :
							if ( $count >= 8 ) break;
							$count++;
						?>
							<li>
								<span class="spec-label"><?php echo esc_html( $label ); ?>:</span>
								<span class="spec-value"><?php
									$spec_val = $spec_data['value'];
									if ( $spec_data['capitalize'] ) {
										$spec_val = ucwords( strtolower( $spec_val ) );
									}
									echo wp_kses( csf_format_dimension_fractions( $spec_val ), array( 'sup' => array(), 'sub' => array() ) );
								?></span>
							</li>
						<?php endforeach; ?>
					</ul>
				</div>
			<?php endif; ?>

			<!-- Interchange Numbers -->
			<?php if ( ! empty( $interchange_numbers ) ) : ?>
				<?php
				// Sort interchange numbers alphabetically by reference_type, then by reference_number.
				usort(
					$interchange_numbers,
					function( $a, $b ) {
						$type_compare = strcmp( $a['reference_type'] ?? '', $b['reference_type'] ?? '' );
						if ( 0 !== $type_compare ) {
							return $type_compare;
						}
						return strcmp( $a['reference_number'] ?? '', $b['reference_number'] ?? '' );
					}
				);
				?>
				<h3 style="margin: 24px 0 12px; font-size: 16px; font-weight: 600; color: var(--global-palette3, #0A0A0A);">Interchange Numbers</h3>
				<p class="csf-interchange-description" style="margin: 0 0 16px; font-size: 14px; color: var(--csf-text-light);">This part replaces the following OEM and aftermarket part numbers:</p>
				<div class="csf-interchange-grid">
					<?php foreach ( $interchange_numbers as $reference ) : ?>
						<div class="csf-interchange-card">
							<div class="interchange-type"><?php echo esc_html( $reference['reference_type'] ?? 'OEM' ); ?></div>
							<div class="interchange-number"><?php echo esc_html( $reference['reference_number'] ?? '' ); ?></div>
						</div>
					<?php endforeach; ?>
				</div>
			<?php endif; ?>

			<!-- CTA Section (Reference Catalog) -->
			<div class="csf-cta-section">
				<p class="csf-reference-note">
					<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<circle cx="12" cy="12" r="10"></circle>
						<line x1="12" y1="16" x2="12" y2="12"></line>
						<line x1="12" y1="8" x2="12.01" y2="8"></line>
					</svg>
					This is a reference catalog. Contact your local dealer for pricing and availability.
				</p>
			</div>

		</div>
	</div>

	<!-- Product Description (full-width) -->
	<?php if ( ! empty( $part->description ) ) : ?>
		<div class="csf-product-description-section">
			<div class="csf-product-description">
				<?php echo wp_kses_post( $part->description ); ?>
			</div>
		</div>
	<?php endif; ?>

	<!-- Tabbed Content Section -->
	<div class="csf-tabs-section">
		<div class="csf-tabs-nav">
			<?php if ( ! empty( $compatibility ) ) : ?>
				<button class="csf-tab-btn active" data-tab="compatibility">Vehicle Fitment</button>
			<?php endif; ?>
			<?php if ( ! empty( $specifications ) ) : ?>
				<button class="csf-tab-btn <?php echo empty( $compatibility ) ? 'active' : ''; ?>" data-tab="specifications">Full Specifications</button>
			<?php endif; ?>
			<?php if ( ! empty( $features ) ) : ?>
				<button class="csf-tab-btn" data-tab="features">Features & Benefits</button>
			<?php endif; ?>
		</div>

		<div class="csf-tabs-content">

						<!-- Compatibility Tab -->
			<?php if ( ! empty( $compatibility ) ) : ?>
				<div class="csf-tab-panel active" id="tab-compatibility">
					<h2>Vehicle Fitment</h2>
					<p class="tab-description">This part is compatible with the following vehicles:</p>
					<div class="csf-fitment-grid">
					<?php
					// Group by make/model and keep complete engine+aspiration+qualifiers as variants
					$by_make_model = array();
					foreach ( $compatibility as $vehicle ) {
						$key = $vehicle['make'] . '|' . $vehicle['model'];

						if ( ! isset( $by_make_model[ $key ] ) ) {
							$by_make_model[ $key ] = array(
								'make'     => $vehicle['make'],
								'model'    => $vehicle['model'],
								'variants' => array(),
							);
						}

						// Create unique key for this engine+aspiration+qualifiers combination
						$engine = isset( $vehicle['engine'] ) && ! empty( $vehicle['engine'] ) ? $vehicle['engine'] : '';
						$aspiration = isset( $vehicle['aspiration'] ) && ! empty( $vehicle['aspiration'] ) && 'None' !== $vehicle['aspiration'] ? $vehicle['aspiration'] : '';
						$qualifiers = isset( $vehicle['qualifiers'] ) && is_array( $vehicle['qualifiers'] ) ? $vehicle['qualifiers'] : array();

						// Create variant key from all three components
						$variant_key = $engine . '||' . $aspiration . '||' . implode( '|', $qualifiers );

						if ( ! isset( $by_make_model[ $key ]['variants'][ $variant_key ] ) ) {
							$by_make_model[ $key ]['variants'][ $variant_key ] = array(
								'engine'      => $engine,
								'aspiration'  => $aspiration,
								'qualifiers'  => $qualifiers,
								'years'       => array(),
							);
						}

						$by_make_model[ $key ]['variants'][ $variant_key ]['years'][] = $vehicle['year'];
					}

					// Group variants by year set
					$final_groups = array();
					foreach ( $by_make_model as $key => $mm_data ) {
						$by_year_set = array();

						foreach ( $mm_data['variants'] as $variant_data ) {
							// Deduplicate years before sorting
							$variant_data['years'] = array_unique( $variant_data['years'] );
							sort( $variant_data['years'] );
							$year_set_key = implode( ',', $variant_data['years'] );

							if ( ! isset( $by_year_set[ $year_set_key ] ) ) {
								$by_year_set[ $year_set_key ] = array(
									'make'     => $mm_data['make'],
									'model'    => $mm_data['model'],
									'years'    => $variant_data['years'],
									'variants' => array(),
								);
							}

							// Keep each engine+aspiration+qualifiers as a complete variant
							$by_year_set[ $year_set_key ]['variants'][] = array(
								'engine'      => $variant_data['engine'],
								'aspiration'  => $variant_data['aspiration'],
								'qualifiers'  => $variant_data['qualifiers'],
							);
						}

						foreach ( $by_year_set as $group ) {
							$final_groups[] = $group;
						}
					}

				// Sort: user's vehicle first, then alphabetically by make > model > year
				if ( ! empty( $searched_make ) && ! empty( $searched_model ) ) {
					usort(
						$final_groups,
						function( $a, $b ) use ( $searched_make, $searched_model, $searched_year ) {
							// Check if 'a' matches user's vehicle
							$a_make_match  = strcasecmp( $a['make'], $searched_make ) === 0;
							$a_model_match = strcasecmp( $a['model'], $searched_model ) === 0;
							$a_year_match  = empty( $searched_year ) || in_array( strval( $searched_year ), array_map( 'strval', $a['years'] ), true );
							$a_is_match    = $a_make_match && $a_model_match && $a_year_match;

							// Check if 'b' matches user's vehicle
							$b_make_match  = strcasecmp( $b['make'], $searched_make ) === 0;
							$b_model_match = strcasecmp( $b['model'], $searched_model ) === 0;
							$b_year_match  = empty( $searched_year ) || in_array( strval( $searched_year ), array_map( 'strval', $b['years'] ), true );
							$b_is_match    = $b_make_match && $b_model_match && $b_year_match;

							// Matching vehicles go first
							if ( $a_is_match && ! $b_is_match ) {
								return -1; // a comes before b
							}
							if ( ! $a_is_match && $b_is_match ) {
								return 1; // b comes before a
							}

							// For non-matching (or both matching), sort alphabetically by make > model > year
							$make_compare = strcasecmp( $a['make'], $b['make'] );
							if ( 0 !== $make_compare ) {
								return $make_compare;
							}

							$model_compare = strcasecmp( $a['model'], $b['model'] );
							if ( 0 !== $model_compare ) {
								return $model_compare;
							}

							// Sort by earliest year (ascending)
							$a_min_year = ! empty( $a['years'] ) ? min( $a['years'] ) : 0;
							$b_min_year = ! empty( $b['years'] ) ? min( $b['years'] ) : 0;
							return $a_min_year - $b_min_year;
						}
					);
				} else {
					// No user vehicle - just sort alphabetically by make > model > year
					usort(
						$final_groups,
						function( $a, $b ) {
							$make_compare = strcasecmp( $a['make'], $b['make'] );
							if ( 0 !== $make_compare ) {
								return $make_compare;
							}

							$model_compare = strcasecmp( $a['model'], $b['model'] );
							if ( 0 !== $model_compare ) {
								return $model_compare;
							}

							// Sort by earliest year (ascending)
							$a_min_year = ! empty( $a['years'] ) ? min( $a['years'] ) : 0;
							$b_min_year = ! empty( $b['years'] ) ? min( $b['years'] ) : 0;
							return $a_min_year - $b_min_year;
						}
					);
				}

					// Display fitment cards
					foreach ( $final_groups as $group ) :
						sort( $group['years'] );
						$year_ranges = array();
						$start       = $group['years'][0];
						$end         = $group['years'][0];

						// Build year ranges
						for ( $i = 1; $i < count( $group['years'] ); $i++ ) {
							if ( $group['years'][ $i ] == $end + 1 ) {
								$end = $group['years'][ $i ];
							} else {
								// Smart formatting: 3 or less = comma list, 4+ = en-dash range
								$range_size = $end - $start + 1;
								if ( $range_size <= 3 ) {
									$year_ranges[] = implode( ', ', range( $start, $end ) );
								} else {
									$year_ranges[] = $start . '–' . $end;
								}
								$start = $group['years'][ $i ];
								$end   = $group['years'][ $i ];
							}
						}
						// Handle final range
						$range_size = $end - $start + 1;
						if ( $range_size <= 3 ) {
							$year_ranges[] = implode( ', ', range( $start, $end ) );
						} else {
							$year_ranges[] = $start . '–' . $end;
						}

						// Check if this vehicle matches the searched parameters
					$is_match          = false;
					$is_possible_match = false;
						if ( ! empty( $searched_make ) && ! empty( $searched_model ) ) {
							$make_match  = strcasecmp( $group['make'], $searched_make ) === 0;
							$model_match = strcasecmp( $group['model'], $searched_model ) === 0;
							$year_match  = empty( $searched_year ) || in_array( strval( $searched_year ), array_map( 'strval', $group['years'] ), true );
						$ymm_match   = $make_match && $model_match && $year_match;

						// Count non-empty engine variants
						$variant_count = 0;
						if ( ! empty( $group['variants'] ) ) {
							foreach ( $group['variants'] as $variant ) {
								if ( ! empty( $variant['engine'] ) ) {
									$variant_count++;
								}
							}
						}

						// Confirmed match: YMM matches AND (no engine data OR only one engine option)
						// Possible match: YMM matches AND multiple engine options exist
						if ( $ymm_match ) {
							if ( $variant_count <= 1 ) {
								// No engine data (universal fit) or single engine (unambiguous)
								$is_match = true;
							} else {
								// Multiple engines - user must verify their specific engine
								$is_possible_match = true;
							}
						}
						}

					$highlight_class = ( $is_match || $is_possible_match ) ? ' csf-fitment-highlighted' : '';
					// Prepare variants data for JS (extract just engines for backward compatibility)
					$engines_for_js = array();
					if ( ! empty( $group['variants'] ) ) {
						foreach ( $group['variants'] as $variant ) {
							if ( ! empty( $variant['engine'] ) ) {
								$engines_for_js[] = $variant['engine'];
							}
						}
					}
					$engines_json = wp_json_encode( $engines_for_js );
						?>
						<div class="csf-fitment-card<?php echo esc_attr( $highlight_class ); ?>"
							data-make="<?php echo esc_attr( strtolower( $group['make'] ) ); ?>"
							data-model="<?php echo esc_attr( strtolower( $group['model'] ) ); ?>"
							data-engines="<?php echo esc_attr( $engines_json ); ?>">

							<?php if ( $is_match ) : ?>
								<div class="fitment-match-badge">Your Vehicle</div>
							<?php elseif ( $is_possible_match ) : ?>
								<div class="fitment-match-badge fitment-possible-match">Possible Match</div>
							<?php endif; ?>

							<button class="fitment-card-header"
								aria-expanded="false"
								aria-controls="fitment-details-<?php echo esc_attr( md5( $group['make'] . $group['model'] . implode( ',', $group['years'] ) ) ); ?>">
								<div class="fitment-header-content">
									<div class="fitment-make-model">
										<span class="fitment-make"><?php echo esc_html( $group['make'] ); ?></span>
										<span class="fitment-model"><?php echo esc_html( $group['model'] ); ?></span>
									</div>
									<div class="fitment-years"><?php echo esc_html( implode( ', ', $year_ranges ) ); ?></div>
									<?php if ( ! empty( $group['variants'] ) ) : ?>
										<div class="fitment-variant-count">
											<?php echo esc_html( count( $group['variants'] ) ); ?>
											<?php echo count( $group['variants'] ) === 1 ? 'configuration' : 'configurations'; ?>
										</div>
									<?php endif; ?>
								</div>
								<svg class="fitment-expand-icon" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
									<polyline points="6 9 12 15 18 9"></polyline>
								</svg>
							</button>

							<?php if ( ! empty( $group['variants'] ) ) : ?>
								<div class="fitment-details"
									id="fitment-details-<?php echo esc_attr( md5( $group['make'] . $group['model'] . implode( ',', $group['years'] ) ) ); ?>"
									aria-hidden="true">
									<table class="fitment-table">
										<thead>
											<tr>
												<th scope="col">Engine</th>
												<th scope="col">Configuration</th>
											</tr>
										</thead>
										<tbody>
											<?php foreach ( $group['variants'] as $variant ) : ?>
												<tr>
													<td class="fitment-engine">
														<?php echo esc_html( ! empty( $variant['engine'] ) ? $variant['engine'] : '—' ); ?>
													</td>
													<td class="fitment-config">
														<?php if ( ! empty( $variant['aspiration'] ) ) : ?>
															<div class="config-item config-aspiration">
																<?php echo esc_html( $variant['aspiration'] ); ?>
															</div>
														<?php endif; ?>
														<?php if ( ! empty( $variant['qualifiers'] ) ) : ?>
															<?php foreach ( $variant['qualifiers'] as $qualifier ) : ?>
																<div class="config-item config-qualifier">
																	<?php echo esc_html( $qualifier ); ?>
																</div>
															<?php endforeach; ?>
														<?php endif; ?>
														<?php if ( empty( $variant['aspiration'] ) && empty( $variant['qualifiers'] ) ) : ?>
															<div class="config-item config-standard">Standard</div>
														<?php endif; ?>
													</td>
												</tr>
											<?php endforeach; ?>
										</tbody>
									</table>
								</div>
							<?php endif; ?>
						</div>
					<?php endforeach; ?>
					</div>
				</div>
			<?php endif; ?>


			<!-- Specifications Tab -->
			<?php if ( ! empty( $specifications ) ) : ?>
				<div class="csf-tab-panel <?php echo empty( $compatibility ) ? 'active' : ''; ?>" id="tab-specifications">
					<h2>Full Specifications</h2>
					<div class="csf-specs-grid">
						<?php foreach ( $specifications as $key => $value ) : ?>
							<?php
							// Special handling: if key looks like a part number (digits or CSF-####), it's the part type
							$label = $key;
							if ( preg_match( '/^(CSF-?)?\d+$/', $key ) ) {
								$label = 'Part Type';
							} else {
								$label = ucwords( str_replace( '_', ' ', $key ) );
							}
							?>
							<div class="csf-spec-row">
								<dt class="spec-label"><?php echo esc_html( $label ); ?></dt>
								<dd class="spec-value"><?php echo wp_kses( csf_format_dimension_fractions( $value ), array( 'sup' => array(), 'sub' => array() ) ); ?></dd>
							</div>
						<?php endforeach; ?>
					</div>
				</div>
			<?php endif; ?>

			<!-- Features Tab -->
			<?php if ( ! empty( $features ) ) : ?>
				<div class="csf-tab-panel" id="tab-features">
					<h2>Features & Benefits</h2>
					<ul class="csf-features-list">
						<?php foreach ( $features as $feature ) : ?>
							<li>
								<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
									<polyline points="20 6 9 17 4 12"></polyline>
								</svg>
								<?php echo esc_html( $feature ); ?>
							</li>
						<?php endforeach; ?>
					</ul>
				</div>
			<?php endif; ?>

		</div>
	</div>

</div>

<!-- Tab Switching Script -->
<script>
document.addEventListener('DOMContentLoaded', function() {
	const tabButtons = document.querySelectorAll('.csf-tab-btn');
	const tabPanels = document.querySelectorAll('.csf-tab-panel');

	tabButtons.forEach(button => {
		button.addEventListener('click', function() {
			const targetTab = this.dataset.tab;

			// Remove active class from all
			tabButtons.forEach(btn => btn.classList.remove('active'));
			tabPanels.forEach(panel => panel.classList.remove('active'));

			// Add active class to clicked
			this.classList.add('active');
			document.getElementById('tab-' + targetTab).classList.add('active');
		});
	});
});

// Image gallery switching
function csfSwitchImage(imageUrl, thumbElement) {
	document.getElementById('csf-main-image').src = imageUrl;

	// Update active thumb
	document.querySelectorAll('.csf-thumb').forEach(thumb => {
		thumb.classList.remove('active');
	});
	thumbElement.classList.add('active');
}

// Engine variant selection - update fitment badges dynamically
document.addEventListener('DOMContentLoaded', function() {
	const engineDropdown = document.getElementById('csf-engine-variant');
	if (!engineDropdown) return;

	// Store original order of cards for re-sorting
	const fitmentGrid = document.querySelector('.csf-fitment-grid');
	if (!fitmentGrid) return;

	const cards = Array.from(fitmentGrid.querySelectorAll('.csf-fitment-card'));

	// Get user's vehicle from "Your Vehicle" box
	const vehicleBox = document.querySelector('.csf-your-vehicle-box');
	if (!vehicleBox) return;

	const ymmText = vehicleBox.querySelector('.your-vehicle-ymm')?.textContent.trim();
	if (!ymmText) return;

	const [userYear, userMake, ...modelParts] = ymmText.split(' ');
	const userModel = modelParts.join(' ').toLowerCase();

	engineDropdown.addEventListener('change', function() {
		const selectedEngine = this.value;

		// Reset all cards first
		cards.forEach(card => {
			const badge = card.querySelector('.fitment-match-badge');
			if (badge) {
				badge.remove();
			}
			card.classList.remove('csf-fitment-highlighted');
			card.style.display = ''; // Show all cards by default
		});

		if (!selectedEngine) {
			// No engine selected - show all as "Possible Match"
			cards.forEach(card => {
				const make = card.dataset.make;
				const model = card.dataset.model;

				if (make === userMake.toLowerCase() && model === userModel) {
					card.classList.add('csf-fitment-highlighted');
					const badge = document.createElement('div');
					badge.className = 'fitment-match-badge fitment-possible-match';
					badge.textContent = 'Possible Match';
					card.appendChild(badge);
				}
			});

			// Re-sort: possible matches first, then alphabetical
			sortCards(false);
		} else {
			// Engine selected - find exact match and hide non-matches
			let exactMatch = null;

			cards.forEach(card => {
				const make = card.dataset.make;
				const model = card.dataset.model;
				const engines = JSON.parse(card.dataset.engines || '[]');

				// Check if this card matches user's vehicle
				if (make === userMake.toLowerCase() && model === userModel) {
					// Check if it matches the selected engine
					if (engines.includes(selectedEngine)) {
						// Exact match - show as "Your Vehicle"
						exactMatch = card;
						card.classList.add('csf-fitment-highlighted');
						card.style.display = ''; // Ensure it's visible
						const badge = document.createElement('div');
						badge.className = 'fitment-match-badge';
						badge.textContent = 'Your Vehicle';
						card.appendChild(badge);
					} else {
						// Same make/model but different engine - hide it
						card.style.display = 'none';
					}
				}
				// Non-matching vehicles stay visible
			});

			// Re-sort: exact match first, then alphabetical
			sortCards(true);
		}
	});

	function sortCards(hasExactMatch) {
		const sortedCards = cards.slice().sort((a, b) => {
			const aHasBadge = a.querySelector('.fitment-match-badge') !== null;
			const bHasBadge = b.querySelector('.fitment-match-badge') !== null;

			// Matching cards go first
			if (aHasBadge && !bHasBadge) return -1;
			if (!aHasBadge && bHasBadge) return 1;

			// For non-matching cards, sort alphabetically by make > model
			const aMake = a.querySelector('.fitment-make')?.textContent || '';
			const bMake = b.querySelector('.fitment-make')?.textContent || '';
			const makeCompare = aMake.localeCompare(bMake);
			if (makeCompare !== 0) return makeCompare;

			const aModel = a.querySelector('.fitment-model')?.textContent || '';
			const bModel = b.querySelector('.fitment-model')?.textContent || '';
			return aModel.localeCompare(bModel);
		});

		// Re-append cards in new order
		sortedCards.forEach(card => fitmentGrid.appendChild(card));
	}
});

// Expandable fitment cards
document.addEventListener('DOMContentLoaded', function() {
	const cardHeaders = document.querySelectorAll('.fitment-card-header');

	cardHeaders.forEach(header => {
		header.addEventListener('click', function() {
			const expanded = this.getAttribute('aria-expanded') === 'true';
			const detailsId = this.getAttribute('aria-controls');
			const details = document.getElementById(detailsId);

			if (!details) return;

			// Toggle expanded state
			this.setAttribute('aria-expanded', !expanded);
			details.setAttribute('aria-hidden', expanded);
		});

		// Keyboard accessibility - Space and Enter
		header.addEventListener('keydown', function(e) {
			if (e.key === ' ' || e.key === 'Enter') {
				e.preventDefault();
				this.click();
			}
		});
	});

	// Auto-expand user's vehicle card
	const highlightedCard = document.querySelector('.csf-fitment-highlighted .fitment-card-header');
	if (highlightedCard) {
		// Small delay to ensure smooth animation
		setTimeout(() => {
			highlightedCard.click();
		}, 300);
	}
});
</script>

<?php
// Use WordPress's theme system - handles both traditional and block themes
get_footer();
?>
