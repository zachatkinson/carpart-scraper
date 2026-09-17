<?php
/**
 * Part page layout: the block markup that composes the part blocks.
 *
 * The default mirrors the design mock. An administrator can point the plugin
 * at a page whose content becomes the layout (Settings → Part Page), so the
 * part page is editable in the block editor with any blocks.
 *
 * @package CSF_Parts_Catalog
 * @since   1.16.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

/**
 * Class CSF_Parts_Part_Layout
 */
final class CSF_Parts_Part_Layout {

	/** Part blocks, in the order the default layout uses them. */
	public const BLOCKS = array(
		'part-breadcrumbs',
		'part-gallery',
		'part-header',
		'part-key-specs',
		'part-replaces',
		'part-fitment',
		'part-spec-cards',
		'part-features',
		'part-related',
	);

	/**
	 * Built-in layout: breadcrumbs, gallery beside header/specs/replaces, then full-width sections.
	 *
	 * @return string Block markup.
	 */
	public static function default_markup(): string {
		return <<<'HTML'
<!-- wp:csf-parts/part-breadcrumbs /-->

<!-- wp:columns {"className":"csf-part-layout__top"} -->
<div class="wp-block-columns csf-part-layout__top"><!-- wp:column {"width":"50%"} -->
<div class="wp-block-column" style="flex-basis:50%"><!-- wp:csf-parts/part-gallery /--></div>
<!-- /wp:column -->

<!-- wp:column {"width":"50%"} -->
<div class="wp-block-column" style="flex-basis:50%"><!-- wp:csf-parts/part-header /-->

<!-- wp:csf-parts/part-key-specs /-->

<!-- wp:csf-parts/part-replaces /--></div>
<!-- /wp:column --></div>
<!-- /wp:columns -->

<!-- wp:csf-parts/part-fitment /-->

<!-- wp:csf-parts/part-spec-cards /-->

<!-- wp:csf-parts/part-features /-->

<!-- wp:csf-parts/part-related /-->
HTML;
	}

	/**
	 * The layout markup in effect: the configured layout page's content, else the default.
	 *
	 * @return string
	 */
	public static function markup(): string {
		$page_id = (int) get_option( CSF_Parts_Constants::OPTION_PART_LAYOUT_PAGE, 0 );
		if ( $page_id > 0 ) {
			$page = get_post( $page_id );
			if ( $page && 'trash' !== $page->post_status && '' !== trim( (string) $page->post_content ) ) {
				return (string) $page->post_content;
			}
		}
		return self::default_markup();
	}

	/**
	 * Render the layout for a part view.
	 *
	 * @param array<string, mixed> $view View from CSF_Parts_Part_Page::build_view().
	 * @return string HTML.
	 */
	public static function render( array $view ): string {
		CSF_Parts_Part_Context::set( $view );
		$html = do_blocks( self::markup() );
		CSF_Parts_Part_Context::clear();
		return $html;
	}

	/**
	 * Create a draft page holding the default layout and select it.
	 *
	 * @return int New page ID, or 0 on failure.
	 */
	public static function create_layout_page(): int {
		$page_id = wp_insert_post(
			array(
				'post_type'    => 'page',
				'post_status'  => 'draft',
				'post_title'   => 'Part page layout',
				'post_content' => self::default_markup(),
			),
			true
		);
		if ( is_wp_error( $page_id ) || ! $page_id ) {
			return 0;
		}
		update_option( CSF_Parts_Constants::OPTION_PART_LAYOUT_PAGE, (int) $page_id );
		return (int) $page_id;
	}
}
