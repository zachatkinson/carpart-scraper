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

			<p class="csf-product-eyebrow">
				<a href="<?php echo esc_url( home_url( '/parts/?csf_category=' . rawurlencode( $part->category ) ) ); ?>" class="csf-product-eyebrow__link"><?php echo esc_html( $eyebrow ); ?></a>
				<?php if ( ! empty( $part->discontinued ) && 1 === (int) $part->discontinued ) : ?>
					<span class="csf-badge csf-discontinued-badge csf-discontinued-badge--inline">DISCONTINUED</span>
				<?php endif; ?>
			</p>

			<h1 class="csf-product-title"><?php echo esc_html( $heading ); ?></h1>

			<?php
			$intro = ! empty( $part->short_description ) ? $part->short_description : ( $part->description ?? '' );
			if ( ! empty( $intro ) ) :
				?>
				<div class="csf-product-intro"><?php echo wp_kses_post( wpautop( $intro ) ); ?></div>
			<?php endif; ?>

			<?php if ( '' !== $distributor_url || '' !== $tech_service_url ) : ?>
				<div class="csf-product-actions">
					<?php if ( '' !== $distributor_url ) : ?>
						<a class="csf-btn csf-product-actions__primary" href="<?php echo esc_url( $distributor_url ); ?>"><?php esc_html_e( 'Find a distributor', 'csf-parts' ); ?></a>
					<?php endif; ?>
					<?php if ( '' !== $tech_service_url ) : ?>
						<a class="csf-btn csf-btn--outline csf-product-actions__secondary" href="<?php echo esc_url( $tech_service_url ); ?>"><?php esc_html_e( 'Ask technical service', 'csf-parts' ); ?></a>
					<?php endif; ?>
				</div>
			<?php endif; ?>

			<?php if ( '' !== trim( $part_page_note ) ) : ?>
				<p class="csf-reference-note"><?php echo esc_html( $part_page_note ); ?></p>
			<?php endif; ?>

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
							<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
								<circle cx="12" cy="12" r="10"></circle>
								<line x1="12" y1="16" x2="12" y2="12"></line>
								<line x1="12" y1="8" x2="12.01" y2="8"></line>
							</svg>
							<div class="engine-notice__body">
								<strong class="engine-notice__title">Please select your vehicle's engine.</strong>
								<span class="engine-notice__hint">Unsure? Contact your local dealer or distributor to verify this part fits your specific vehicle configuration.</span>
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
						<div class="engine-verify-notice">
							Please verify this matches your vehicle's engine before purchasing.
						</div>
					<?php endif; ?>
				</div>
			<?php endif; ?>

			<!-- Key specifications -->
			<?php if ( ! empty( $spec_groups['key'] ) ) : ?>
				<div class="csf-quick-specs">
					<h3><?php esc_html_e( 'Key specifications', 'csf-parts' ); ?></h3>
					<ul>
						<?php foreach ( $spec_groups['key'] as $spec_label => $spec_value ) : ?>
							<li>
								<span class="spec-label"><?php echo esc_html( $spec_label ); ?></span>
								<span class="spec-value"><?php echo wp_kses( csf_format_dimension_fractions( $spec_value ), array( 'sup' => array(), 'sub' => array() ) ); ?></span>
							</li>
						<?php endforeach; ?>
					</ul>
				</div>
			<?php endif; ?>

			<!-- Replaces (interchange numbers) -->
			<?php if ( ! empty( $interchange_numbers ) ) : ?>
				<?php
				usort(
					$interchange_numbers,
					static function ( $a, $b ) {
						$type_compare = strcmp( $a['reference_type'] ?? '', $b['reference_type'] ?? '' );
						return 0 !== $type_compare ? $type_compare : strcmp( $a['reference_number'] ?? '', $b['reference_number'] ?? '' );
					}
				);
				?>
				<div class="csf-replaces">
					<span class="csf-replaces__label"><?php esc_html_e( 'Replaces', 'csf-parts' ); ?></span>
					<div class="csf-interchange-grid">
						<?php foreach ( $interchange_numbers as $reference ) : ?>
							<div class="csf-interchange-card">
								<span class="interchange-type"><?php echo esc_html( $reference['reference_type'] ?? 'OEM' ); ?></span>
								<span class="interchange-number"><?php echo esc_html( $reference['reference_number'] ?? '' ); ?></span>
							</div>
						<?php endforeach; ?>
					</div>
				</div>
			<?php endif; ?>

		</div>
	</div>

	<!-- Fits these vehicles -->
	<?php if ( ! empty( $compatibility ) ) : ?>
		<section class="csf-section csf-fitment">
			<div class="csf-section__header">
				<h2 class="csf-section__title"><?php esc_html_e( 'Fits these vehicles', 'csf-parts' ); ?></h2>
				<p class="csf-section__meta"><?php echo esc_html( CSF_Parts_Part_Page::fitment_counts( $fitment_rows ) ); ?></p>
			</div>
			<?php if ( CSF_Parts_Constants::FITMENT_LAYOUT_CARDS === $fitment_layout ) : ?>
				<?php include CSF_PARTS_PLUGIN_DIR . 'templates/parts/fitment-cards.php'; ?>
			<?php else : ?>
				<div class="csf-fitment-table-wrap">
					<table class="csf-fitment-table">
						<thead>
							<tr>
								<th scope="col"><?php esc_html_e( 'Make', 'csf-parts' ); ?></th>
								<th scope="col"><?php esc_html_e( 'Model', 'csf-parts' ); ?></th>
								<th scope="col"><?php esc_html_e( 'Years', 'csf-parts' ); ?></th>
								<th scope="col"><?php esc_html_e( 'Engine', 'csf-parts' ); ?></th>
								<th scope="col"><?php esc_html_e( 'Notes', 'csf-parts' ); ?></th>
							</tr>
						</thead>
						<tbody>
							<?php foreach ( $fitment_rows as $row ) : ?>
								<?php $row_is_yours = CSF_Parts_Part_Page::row_matches( $row, (string) $searched_year, (string) $searched_make, (string) $searched_model ); ?>
								<tr class="csf-fitment-row<?php echo $row_is_yours ? ' is-yours' : ''; ?>" data-make="<?php echo esc_attr( strtolower( $row['make'] ) ); ?>" data-model="<?php echo esc_attr( strtolower( $row['model'] ) ); ?>" data-engine="<?php echo esc_attr( $row['engine'] ); ?>">
									<td class="csf-fitment-row__make"><?php echo esc_html( $row['make'] ); ?></td>
									<td><?php echo esc_html( $row['model'] ); ?></td>
									<td><?php echo esc_html( $row['years_text'] ); ?></td>
									<td><?php echo esc_html( '' !== $row['engine'] ? $row['engine'] : '—' ); ?></td>
									<td class="csf-fitment-row__notes">
										<?php if ( $row_is_yours ) : ?>
											<span class="csf-fitment-yours"><?php esc_html_e( 'Your vehicle', 'csf-parts' ); ?></span>
										<?php endif; ?>
										<?php echo esc_html( '' !== $row['notes'] ? $row['notes'] : __( 'All trims', 'csf-parts' ) ); ?>
									</td>
								</tr>
							<?php endforeach; ?>
						</tbody>
					</table>
				</div>
			<?php endif; ?>
		</section>
	<?php endif; ?>

	<!-- Dimensions & construction -->
	<?php if ( ! empty( $spec_groups['dimensions'] ) || ! empty( $spec_groups['construction'] ) ) : ?>
		<section class="csf-section csf-spec-cards">
			<?php foreach ( array( 'dimensions' => __( 'Dimensions', 'csf-parts' ), 'construction' => __( 'Construction', 'csf-parts' ) ) as $group_key => $group_label ) : ?>
				<?php if ( ! empty( $spec_groups[ $group_key ] ) ) : ?>
					<div class="csf-spec-card">
						<h3 class="csf-spec-card__title"><?php echo esc_html( $group_label ); ?></h3>
						<dl class="csf-spec-card__list">
							<?php foreach ( $spec_groups[ $group_key ] as $spec_label => $spec_value ) : ?>
								<div class="csf-spec-card__row">
									<dt><?php echo esc_html( $spec_label ); ?></dt>
									<dd><?php echo wp_kses( csf_format_dimension_fractions( $spec_value ), array( 'sup' => array(), 'sub' => array() ) ); ?></dd>
								</div>
							<?php endforeach; ?>
						</dl>
					</div>
				<?php endif; ?>
			<?php endforeach; ?>
		</section>
	<?php endif; ?>

	<!-- Remaining specifications -->
	<?php if ( ! empty( $spec_groups['more'] ) ) : ?>
		<section class="csf-section">
			<div class="csf-section__header">
				<h2 class="csf-section__title"><?php esc_html_e( 'More specifications', 'csf-parts' ); ?></h2>
			</div>
			<div class="csf-specs-grid">
				<?php foreach ( $spec_groups['more'] as $spec_label => $spec_value ) : ?>
					<div class="csf-spec-row">
						<dt class="spec-label"><?php echo esc_html( $spec_label ); ?></dt>
						<dd class="spec-value"><?php echo wp_kses( csf_format_dimension_fractions( $spec_value ), array( 'sup' => array(), 'sub' => array() ) ); ?></dd>
					</div>
				<?php endforeach; ?>
			</div>
		</section>
	<?php endif; ?>

	<!-- Features -->
	<?php if ( ! empty( $features ) ) : ?>
		<section class="csf-section">
			<div class="csf-section__header">
				<h2 class="csf-section__title"><?php esc_html_e( 'Features & benefits', 'csf-parts' ); ?></h2>
			</div>
			<ul class="csf-features-list">
				<?php foreach ( $features as $feature ) : ?>
					<li>
						<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>
						<?php echo esc_html( $feature ); ?>
					</li>
				<?php endforeach; ?>
			</ul>
		</section>
	<?php endif; ?>

	<!-- Other parts for this vehicle -->
	<?php if ( ! empty( $related_parts['parts'] ) ) : ?>
		<section class="csf-section csf-related">
			<div class="csf-section__header">
				<h2 class="csf-section__title"><?php echo esc_html( sprintf( /* translators: %s: vehicle */ __( 'Other parts for this %s', 'csf-parts' ), $related_parts['vehicle'] ) ); ?></h2>
				<a class="csf-section__link" href="<?php echo esc_url( $related_parts['url'] ); ?>"><?php echo esc_html( sprintf( /* translators: %s: vehicle */ __( 'All %s parts →', 'csf-parts' ), $related_parts['vehicle'] ) ); ?></a>
			</div>
			<div class="csf-related__grid csf-grid-items">
				<?php foreach ( $related_parts['parts'] as $related ) : ?>
					<?php echo CSF_Parts_Part_Card::render( $related, csf_get_part_url( (string) $related->sku ), array( 'show_fitment_line' => true ) ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Escaped in the renderer. ?>
				<?php endforeach; ?>
			</div>
		</section>
	<?php endif; ?>

</div>

<!-- Gallery, engine selection and fitment scripts -->
<script>

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
