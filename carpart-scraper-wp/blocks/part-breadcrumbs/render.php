<?php
/**
 * Render: CSF Part Breadcrumbs block.
 *
 * Reads the current part from CSF_Parts_Part_Context (set by the URL handler on
 * part pages; a sample part in the editor). Markup mirrors the pre-1.16 template.
 *
 * @package CSF_Parts_Catalog
 * @since   1.16.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

$view = CSF_Parts_Part_Context::current();
if ( null === $view ) {
	return '';
}
extract( $view ); // phpcs:ignore WordPress.PHP.DontExtract.extract_extract -- Template variables.
$block_attrs = $attributes ?? array();
?>
<div <?php echo get_block_wrapper_attributes( array( 'class' => 'csf-part-block csf-part-block--breadcrumbs' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Escaped by core. ?>>
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


</div>
