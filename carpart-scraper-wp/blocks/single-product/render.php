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
	return '<p>' . esc_html( 'Product not found.' ) . '</p>';
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
		$raw_url       = is_string( $images[0] ) ? $images[0] : ( $images[0]['url'] ?? '' );
		$primary_image = ! empty( $raw_url ) ? csf_resolve_image_url( $raw_url ) : '';
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
		// Display title: Remove hyphen from SKU (CSF-3680 -> CSF3680).
		$display_title = ! empty( $part->name ) ? $part->name : str_replace( '-', '', $part->sku );
		?>
		<h2 class="csf-product-title"><?php echo esc_html( $display_title ); ?></h2>

		<div class="csf-product-meta">
			<p class="csf-sku"><strong><?php echo esc_html( 'SKU:' ); ?></strong> <?php echo esc_html( $part->sku ); ?></p>
			<?php if ( $part->manufacturer ) : ?>
				<p class="csf-manufacturer"><strong><?php echo esc_html( 'Manufacturer:' ); ?></strong> <?php echo esc_html( $part->manufacturer ); ?></p>
			<?php endif; ?>
			<?php if ( $part->category ) : ?>
				<p class="csf-category">
					<strong><?php echo esc_html( 'Category:' ); ?></strong> <?php echo esc_html( $part->category ); ?>
					<?php if ( ! empty( $part->discontinued ) && 1 === (int) $part->discontinued ) : ?>
						<span class="csf-badge csf-discontinued-badge" style="display: inline-block; margin-left: 8px; padding: 6px 14px; background: transparent; color: var(--global-palette1, #C41C10); border: 2px solid var(--global-palette1, #C41C10); font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; border-radius: 20px;">DISCONTINUED</span>
					<?php endif; ?>
				</p>
			<?php endif; ?>
			<?php if ( $show_price ) : ?>
				<?php if ( null !== $part->price && $part->price > 0 ) : ?>
					<p class="csf-price"><strong><?php echo esc_html( 'Price:' ); ?></strong> $<?php echo esc_html( number_format( (float) $part->price, 2 ) ); ?></p>
				<?php else : ?>
					<p class="csf-price"><strong><?php echo esc_html( 'Price:' ); ?></strong> <?php echo esc_html( 'Contact for pricing' ); ?></p>
				<?php endif; ?>
			<?php endif; ?>
			<p class="csf-stock">
				<strong><?php echo esc_html( 'Availability:' ); ?></strong>
				<?php echo $part->in_stock ? esc_html( 'In Stock' ) : esc_html( 'Out of Stock' ); ?>
			</p>
		</div>

		<?php if ( $part->description ) : ?>
			<div class="csf-product-description">
				<?php echo wp_kses_post( $part->description ); ?>
			</div>
		<?php endif; ?>

		<?php if ( $show_specs && ! empty( $specs ) ) : ?>
			<div class="csf-specifications">
				<h3><?php echo esc_html( 'Specifications' ); ?></h3>
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
				<h3><?php echo esc_html( 'Features' ); ?></h3>
				<ul>
					<?php foreach ( $features as $feature ) : ?>
						<li><?php echo esc_html( $feature ); ?></li>
					<?php endforeach; ?>
				</ul>
			</div>
		<?php endif; ?>

		<?php if ( ! empty( $compatibility ) ) : ?>
			<div class="csf-compatibility">
				<h3><?php echo esc_html( 'Vehicle Compatibility' ); ?></h3>
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
				<h3><?php echo esc_html( 'Technical Notes' ); ?></h3>
				<p><?php echo esc_html( $part->tech_notes ); ?></p>
			</div>
		<?php endif; ?>
	</div>
</div>
