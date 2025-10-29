<?php
/**
 * Template for single part page (dynamically generated).
 *
 * Variables available from URL handler:
 * - $part: Database object with all part data
 * - $title: Generated page title
 * - $canonical_url: Canonical URL (points to generic SKU page)
 * - $compatibility: Array of vehicles
 * - $specifications: Array of specs
 * - $features: Array of features
 * - $images: Array of images
 * - $is_vehicle_specific: Boolean
 * - $year, $make, $model: Vehicle context (if applicable)
 *
 * @package CSF_Parts_Catalog
 * @since   2.0.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

// Check if this is a block theme
$is_block_theme = function_exists( 'wp_is_block_theme' ) && wp_is_block_theme();

if ( ! $is_block_theme ) {
	// Classic theme - use traditional header
	get_header();
} else {
	// Block theme - render our own header
	?>
	<!DOCTYPE html>
	<html <?php language_attributes(); ?>>
	<head>
		<meta charset="<?php bloginfo( 'charset' ); ?>">
		<meta name="viewport" content="width=device-width, initial-scale=1">
		<?php wp_head(); ?>
	</head>
	<body <?php body_class( 'csf-block-theme' ); ?>>
	<?php wp_body_open(); ?>
	<div class="wp-site-blocks">
		<header class="wp-block-template-part">
			<div class="wp-block-group alignfull" style="padding: 1.5rem;">
				<div style="max-width: 1200px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center;">
					<a href="<?php echo esc_url( home_url( '/' ) ); ?>" style="text-decoration: none; font-size: 1.5rem; font-weight: bold;">
						<?php bloginfo( 'name' ); ?>
					</a>
					<nav>
						<a href="<?php echo esc_url( home_url( '/' ) ); ?>" style="margin-left: 1rem;">Home</a>
						<a href="<?php echo esc_url( home_url( '/parts-search-test/' ) ); ?>" style="margin-left: 1rem;">Search Parts</a>
					</nav>
				</div>
			</div>
		</header>
		<main class="wp-block-group" style="padding: 2rem 1.5rem;">
			<div style="max-width: 1200px; margin: 0 auto;">
	<?php
}
?>

<div class="csf-part-single">
	<div class="csf-part-container">

		<!-- Breadcrumbs -->
		<nav class="csf-breadcrumbs" aria-label="Breadcrumb">
			<a href="<?php echo esc_url( home_url( '/' ) ); ?>">Home</a>
			<span> &gt; </span>
			<a href="<?php echo esc_url( home_url( '/parts' ) ); ?>">Parts</a>
			<span> &gt; </span>
			<span><?php echo esc_html( $title ); ?></span>
		</nav>

		<!-- Product Title -->
		<h1 class="csf-part-title"><?php echo esc_html( $title ); ?></h1>

		<?php if ( $is_vehicle_specific ) : ?>
			<p class="csf-vehicle-context">
				Showing product information for:
				<strong><?php echo esc_html( "$year $make $model" ); ?></strong>
			</p>
		<?php endif; ?>

		<div class="csf-part-grid">

			<!-- Product Image -->
			<div class="csf-part-image">
				<?php if ( ! empty( $images ) && isset( $images[0]['url'] ) ) : ?>
					<img
						src="<?php echo esc_url( $images[0]['url'] ); ?>"
						alt="<?php echo esc_attr( $images[0]['alt_text'] ?? $title ); ?>"
						loading="lazy"
					>
				<?php else : ?>
					<div class="csf-no-image">No image available</div>
				<?php endif; ?>
			</div>

			<!-- Product Details -->
			<div class="csf-part-details">

				<!-- SKU & Manufacturer -->
				<p class="csf-sku">
					<strong>SKU:</strong> <?php echo esc_html( $part->sku ); ?>
				</p>
				<?php if ( $part->manufacturer ) : ?>
					<p class="csf-manufacturer">
						<strong>Manufacturer:</strong> <?php echo esc_html( $part->manufacturer ); ?>
					</p>
				<?php endif; ?>

				<!-- Price & Availability -->
				<div class="csf-pricing">
					<p class="csf-price">
						<strong>Price:</strong>
						<span class="amount">$<?php echo esc_html( number_format( $part->price, 2 ) ); ?></span>
					</p>
					<p class="csf-stock <?php echo $part->in_stock ? 'in-stock' : 'out-of-stock'; ?>">
						<?php echo $part->in_stock ? 'In Stock' : 'Out of Stock'; ?>
					</p>
				</div>

				<!-- Description -->
				<div class="csf-description">
					<?php echo wp_kses_post( $part->description ); ?>
				</div>

			</div>

		</div>

		<!-- Vehicle Compatibility -->
		<?php if ( ! empty( $compatibility ) ) : ?>
			<div class="csf-compatibility">
				<h2>Vehicle Fitment</h2>
				<p>This part fits the following vehicles:</p>
				<ul class="csf-fitment-list">
					<?php
					// Group by make/model with year ranges.
					$grouped = array();
					foreach ( $compatibility as $vehicle ) {
						$key = $vehicle['make'] . '|' . $vehicle['model'];
						if ( ! isset( $grouped[ $key ] ) ) {
							$grouped[ $key ] = array(
								'make'  => $vehicle['make'],
								'model' => $vehicle['model'],
								'years' => array(),
							);
						}
						$grouped[ $key ]['years'][] = $vehicle['year'];
					}

					foreach ( $grouped as $group ) {
						sort( $group['years'] );
						$year_ranges = array();
						$start       = $group['years'][0];
						$end         = $group['years'][0];

						for ( $i = 1; $i < count( $group['years'] ); $i++ ) {
							if ( $group['years'][ $i ] === $end + 1 ) {
								$end = $group['years'][ $i ];
							} else {
								$year_ranges[] = $start === $end ? $start : "$start-$end";
								$start         = $group['years'][ $i ];
								$end           = $group['years'][ $i ];
							}
						}
						$year_ranges[] = $start === $end ? $start : "$start-$end";

						echo '<li>' . esc_html( implode( ', ', $year_ranges ) . ' ' . $group['make'] . ' ' . $group['model'] ) . '</li>';
					}
					?>
				</ul>
			</div>
		<?php endif; ?>

		<!-- Specifications -->
		<?php if ( ! empty( $specifications ) ) : ?>
			<div class="csf-specifications">
				<h2>Specifications</h2>
				<dl>
					<?php foreach ( $specifications as $key => $value ) : ?>
						<dt><?php echo esc_html( ucwords( str_replace( '_', ' ', $key ) ) ); ?></dt>
						<dd><?php echo esc_html( $value ); ?></dd>
					<?php endforeach; ?>
				</dl>
			</div>
		<?php endif; ?>

		<!-- Features -->
		<?php if ( ! empty( $features ) ) : ?>
			<div class="csf-features">
				<h2>Features</h2>
				<ul>
					<?php foreach ( $features as $feature ) : ?>
						<li><?php echo esc_html( $feature ); ?></li>
					<?php endforeach; ?>
				</ul>
			</div>
		<?php endif; ?>

		<!-- Technical Notes -->
		<?php if ( ! empty( $part->tech_notes ) ) : ?>
			<div class="csf-tech-notes">
				<h2>Technical Notes</h2>
				<?php echo wp_kses_post( $part->tech_notes ); ?>
			</div>
		<?php endif; ?>

	</div>
</div>

<?php
if ( ! $is_block_theme ) {
	// Classic theme - use traditional footer
	get_footer();
} else {
	// Block theme - render our own footer
	?>
			</div>
		</main>
		<footer class="wp-block-template-part" style="border-top: 1px solid #ddd; padding: 2rem 1.5rem; margin-top: 3rem;">
			<div style="max-width: 1200px; margin: 0 auto; text-align: center;">
				<p>&copy; <?php echo esc_html( date( 'Y' ) ); ?> <?php bloginfo( 'name' ); ?>. All rights reserved.</p>
			</div>
		</footer>
	</div>
	<?php wp_footer(); ?>
	</body>
	</html>
	<?php
}
