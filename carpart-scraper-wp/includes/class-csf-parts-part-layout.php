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
	 * Register the private layout post type and the admin entry point.
	 *
	 * The layout is a plugin-owned post: never public, never in the Pages
	 * list, but editable with the block editor via CSF Parts → Part Page Layout.
	 */
	public static function init(): void {
		add_action( 'init', array( self::class, 'register_post_type' ) );
		add_action( 'admin_menu', array( self::class, 'register_menu' ), 20 );
	}

	/**
	 * Register the layout post type.
	 */
	public static function register_post_type(): void {
		register_post_type(
			CSF_Parts_Constants::LAYOUT_POST_TYPE,
			array(
				'labels'              => array(
					'name'          => 'CSF Layouts',
					'singular_name' => 'CSF Layout',
					'edit_item'     => 'Edit Part Page Layout',
				),
				'public'              => false,
				'publicly_queryable'  => false,
				'exclude_from_search' => true,
				'show_ui'             => true,
				'show_in_menu'        => false,
				'show_in_nav_menus'   => false,
				'show_in_rest'        => true,
				'rewrite'             => false,
				'query_var'           => false,
				'supports'            => array( 'editor' ),
				'capability_type'     => 'page',
				'map_meta_cap'        => true,
			)
		);
	}

	/**
	 * CSF Parts → Part Page Layout opens the layout in the block editor.
	 */
	public static function register_menu(): void {
		$post_id = self::layout_post_id();
		if ( $post_id <= 0 ) {
			return;
		}
		add_submenu_page(
			'csf-parts',
			'Part Page Layout',
			'Part Page Layout',
			'manage_options',
			'post.php?post=' . $post_id . '&action=edit'
		);
	}

	/**
	 * ID of the part page layout post, created from the built-in layout when missing.
	 *
	 * A layout page chosen with the 1.16.0 setting is migrated once.
	 *
	 * @return int 0 when it cannot be created.
	 */
	public static function layout_post_id(): int {
		$found = get_posts(
			array(
				'post_type'      => CSF_Parts_Constants::LAYOUT_POST_TYPE,
				'post_status'    => 'any',
				'posts_per_page' => 1,
				'meta_key'       => '_csf_layout_key', // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key
				'meta_value'     => CSF_Parts_Constants::LAYOUT_KEY_PART_PAGE, // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_value
				'fields'         => 'ids',
			)
		);
		if ( ! empty( $found ) ) {
			return (int) $found[0];
		}

		$content     = self::default_markup();
		$legacy_page = (int) get_option( CSF_Parts_Constants::OPTION_PART_LAYOUT_PAGE, 0 );
		if ( $legacy_page > 0 ) {
			$page = get_post( $legacy_page );
			if ( $page && 'trash' !== $page->post_status && '' !== trim( (string) $page->post_content ) ) {
				$content = (string) $page->post_content;
			}
			delete_option( CSF_Parts_Constants::OPTION_PART_LAYOUT_PAGE );
		}

		$post_id = wp_insert_post(
			array(
				'post_type'    => CSF_Parts_Constants::LAYOUT_POST_TYPE,
				'post_status'  => 'publish',
				'post_title'   => 'Part page layout',
				'post_content' => $content,
				'meta_input'   => array( '_csf_layout_key' => CSF_Parts_Constants::LAYOUT_KEY_PART_PAGE ),
			),
			true
		);

		return is_wp_error( $post_id ) ? 0 : (int) $post_id;
	}

	/**
	 * The layout markup in effect: the layout post's content, else the built-in default.
	 *
	 * @return string
	 */
	public static function markup(): string {
		$post_id = self::layout_post_id();
		if ( $post_id > 0 ) {
			$post = get_post( $post_id );
			if ( $post && '' !== trim( (string) $post->post_content ) ) {
				return (string) $post->post_content;
			}
		}
		return self::default_markup();
	}

	/**
	 * Put the built-in layout back.
	 *
	 * @return bool
	 */
	public static function reset(): bool {
		$post_id = self::layout_post_id();
		if ( $post_id <= 0 ) {
			return false;
		}
		$result = wp_update_post( array( 'ID' => $post_id, 'post_content' => self::default_markup() ), true );
		return ! is_wp_error( $result );
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
}
