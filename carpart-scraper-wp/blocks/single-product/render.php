<?php
/**
 * Server-side render for Single Product block (V2 Architecture).
 *
 * Uses custom database table instead of WordPress posts.
 *
 * @package CSF_Parts_Catalog
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

$sku           = $attributes['sku'] ?? '';
$show_price    = $attributes['showPrice'] ?? true;
$show_specs    = $attributes['showSpecs'] ?? true;
$show_features = $attributes['showFeatures'] ?? true;

if ( empty( $sku ) ) {
	return '';
}

// Get database instance and query for part by SKU (V2).
$database = new CSF_Parts_Database();
$part     = $database->get_part_by_sku( $sku );

if ( ! $part ) {
	return '<p>' . esc_html__( 'Product not found.', 'csf-parts' ) . '</p>';
}

// Parse JSON fields.
$specs        = ! empty( $part->specifications ) ? json_decode( $part->specifications, true ) : array();
$features     = ! empty( $part->features ) ? json_decode( $part->features, true ) : array();
$images       = ! empty( $part->images ) ? json_decode( $part->images, true ) : array();
$compatibility = ! empty( $part->compatibility ) ? json_decode( $part->compatibility, true ) : array();

// Get primary image.
$primary_image = '';
if ( ! empty( $images ) ) {
	if ( is_array( $images ) ) {
		$primary_image = is_string( $images[0] ) ? $images[0] : ( $images[0]['url'] ?? '' );
	}
}

// Render block.
?>
<div class="csf-single-product">
	<?php if ( $primary_image ) : ?>
		<div class="csf-product-image">
			<?php
			// Use name if available, otherwise use category for alt text.
			$image_alt = ! empty( $part->name ) ? $part->name : $part->category . ' ' . $part->sku;
			?>
			<img src="<?php echo esc_url( $primary_image ); ?>" alt="<?php echo esc_attr( $image_alt ); ?>" />
		</div>
	<?php endif; ?>

	<div class="csf-product-details">
		<?php
		// Display name if available, otherwise fall back to category + SKU.
		$display_title = ! empty( $part->name ) ? $part->name : $part->category . ' - ' . $part->sku;
		?>
		<h2 class="csf-product-title"><?php echo esc_html( $display_title ); ?></h2>

		<div class="csf-product-meta">
			<p class="csf-sku"><strong><?php esc_html_e( 'SKU:', 'csf-parts' ); ?></strong> <?php echo esc_html( $part->sku ); ?></p>
			<?php if ( $part->manufacturer ) : ?>
				<p class="csf-manufacturer"><strong><?php esc_html_e( 'Manufacturer:', 'csf-parts' ); ?></strong> <?php echo esc_html( $part->manufacturer ); ?></p>
			<?php endif; ?>
			<?php if ( $part->category ) : ?>
				<p class="csf-category"><strong><?php esc_html_e( 'Category:', 'csf-parts' ); ?></strong> <?php echo esc_html( $part->category ); ?></p>
			<?php endif; ?>
			<?php if ( $show_price && $part->price ) : ?>
				<p class="csf-price"><strong><?php esc_html_e( 'Price:', 'csf-parts' ); ?></strong> $<?php echo esc_html( number_format( $part->price, 2 ) ); ?></p>
			<?php endif; ?>
			<p class="csf-stock">
				<strong><?php esc_html_e( 'Availability:', 'csf-parts' ); ?></strong>
				<?php echo $part->in_stock ? esc_html__( 'In Stock', 'csf-parts' ) : esc_html__( 'Out of Stock', 'csf-parts' ); ?>
			</p>
		</div>

		<?php if ( $part->description ) : ?>
			<div class="csf-product-description">
				<?php echo wp_kses_post( $part->description ); ?>
			</div>
		<?php endif; ?>

		<?php if ( $show_specs && ! empty( $specs ) ) : ?>
			<div class="csf-specifications">
				<h3><?php esc_html_e( 'Specifications', 'csf-parts' ); ?></h3>
				<dl>
					<?php foreach ( $specs as $key => $value ) : ?>
						<dt><?php echo esc_html( ucwords( str_replace( '_', ' ', $key ) ) ); ?></dt>
						<dd><?php echo esc_html( $value ); ?></dd>
					<?php endforeach; ?>
				</dl>
			</div>
		<?php endif; ?>

		<?php if ( $show_features && ! empty( $features ) ) : ?>
			<div class="csf-features">
				<h3><?php esc_html_e( 'Features', 'csf-parts' ); ?></h3>
				<ul>
					<?php foreach ( $features as $feature ) : ?>
						<li><?php echo esc_html( $feature ); ?></li>
					<?php endforeach; ?>
				</ul>
			</div>
		<?php endif; ?>

		<?php if ( ! empty( $compatibility ) ) : ?>
			<div class="csf-compatibility">
				<h3><?php esc_html_e( 'Vehicle Compatibility', 'csf-parts' ); ?></h3>
				<ul>
					<?php foreach ( $compatibility as $vehicle ) : ?>
						<li>
							<?php
							echo esc_html(
								sprintf(
									'%s %s %s',
									$vehicle['year'] ?? '',
									$vehicle['make'] ?? '',
									$vehicle['model'] ?? ''
								)
							);
							if ( ! empty( $vehicle['submodel'] ) ) {
								echo ' - ' . esc_html( $vehicle['submodel'] );
							}
							?>
						</li>
					<?php endforeach; ?>
				</ul>
			</div>
		<?php endif; ?>

		<?php if ( $part->tech_notes ) : ?>
			<div class="csf-tech-notes">
				<h3><?php esc_html_e( 'Technical Notes', 'csf-parts' ); ?></h3>
				<p><?php echo esc_html( $part->tech_notes ); ?></p>
			</div>
		<?php endif; ?>
	</div>
</div>
