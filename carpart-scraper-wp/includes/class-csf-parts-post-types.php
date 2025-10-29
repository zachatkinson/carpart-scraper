<?php
/**
 * Register custom post types.
 *
 * @package CSF_Parts_Catalog
 * @since   1.0.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

/**
 * Class CSF_Parts_Post_Types
 */
class CSF_Parts_Post_Types {

	/**
	 * Constructor.
	 */
	public function __construct() {
		add_action( 'init', array( $this, 'register' ) );
	}

	/**
	 * Register custom post types.
	 *
	 * @since 1.0.0
	 */
	public static function register() {
		// Register csf_part post type.
		register_post_type(
			CSF_Parts_Constants::POST_TYPE,
			array(
				'labels'              => self::get_part_labels(),
				'public'              => true,
				'publicly_queryable'  => true,
				'show_ui'             => true,
				'show_in_menu'        => true,
				'query_var'           => true,
				'rewrite'             => array( 'slug' => 'parts' ),
				'capability_type'     => 'post',
				'has_archive'         => true,
				'hierarchical'        => false,
				'menu_position'       => 20,
				'menu_icon'           => 'dashicons-car',
				'supports'            => array( 'title', 'editor', 'excerpt', 'thumbnail', 'custom-fields' ),
				'taxonomies'          => array(
					CSF_Parts_Constants::TAXONOMY_CATEGORY,
					CSF_Parts_Constants::TAXONOMY_MAKE,
					CSF_Parts_Constants::TAXONOMY_MODEL,
					CSF_Parts_Constants::TAXONOMY_YEAR,
				),
				'show_in_rest'        => true,
				'rest_base'           => 'parts',
				'rest_controller_class' => 'WP_REST_Posts_Controller',
			)
		);

		// Register custom meta fields for REST API.
		self::register_meta_fields();
	}

	/**
	 * Get part post type labels.
	 *
	 * @since 1.0.0
	 * @return array Labels array.
	 */
	private static function get_part_labels() {
		return array(
			'name'                  => _x( 'Parts', 'Post type general name', CSF_Parts_Constants::TEXT_DOMAIN ),
			'singular_name'         => _x( 'Part', 'Post type singular name', CSF_Parts_Constants::TEXT_DOMAIN ),
			'menu_name'             => _x( 'Parts', 'Admin Menu text', CSF_Parts_Constants::TEXT_DOMAIN ),
			'name_admin_bar'        => _x( 'Part', 'Add New on Toolbar', CSF_Parts_Constants::TEXT_DOMAIN ),
			'add_new'               => __( 'Add New', CSF_Parts_Constants::TEXT_DOMAIN ),
			'add_new_item'          => __( 'Add New Part', CSF_Parts_Constants::TEXT_DOMAIN ),
			'new_item'              => __( 'New Part', CSF_Parts_Constants::TEXT_DOMAIN ),
			'edit_item'             => __( 'Edit Part', CSF_Parts_Constants::TEXT_DOMAIN ),
			'view_item'             => __( 'View Part', CSF_Parts_Constants::TEXT_DOMAIN ),
			'all_items'             => __( 'All Parts', CSF_Parts_Constants::TEXT_DOMAIN ),
			'search_items'          => __( 'Search Parts', CSF_Parts_Constants::TEXT_DOMAIN ),
			'parent_item_colon'     => __( 'Parent Parts:', CSF_Parts_Constants::TEXT_DOMAIN ),
			'not_found'             => __( 'No parts found.', CSF_Parts_Constants::TEXT_DOMAIN ),
			'not_found_in_trash'    => __( 'No parts found in Trash.', CSF_Parts_Constants::TEXT_DOMAIN ),
			'featured_image'        => _x( 'Part Image', 'Overrides the "Featured Image" phrase', CSF_Parts_Constants::TEXT_DOMAIN ),
			'set_featured_image'    => _x( 'Set part image', 'Overrides the "Set featured image" phrase', CSF_Parts_Constants::TEXT_DOMAIN ),
			'remove_featured_image' => _x( 'Remove part image', 'Overrides the "Remove featured image" phrase', CSF_Parts_Constants::TEXT_DOMAIN ),
			'use_featured_image'    => _x( 'Use as part image', 'Overrides the "Use as featured image" phrase', CSF_Parts_Constants::TEXT_DOMAIN ),
			'archives'              => _x( 'Part archives', 'The post type archive label', CSF_Parts_Constants::TEXT_DOMAIN ),
			'insert_into_item'      => _x( 'Insert into part', 'Overrides the "Insert into post"/"Insert into page" phrase', CSF_Parts_Constants::TEXT_DOMAIN ),
			'uploaded_to_this_item' => _x( 'Uploaded to this part', 'Overrides the "Uploaded to this post"/"Uploaded to this page" phrase', CSF_Parts_Constants::TEXT_DOMAIN ),
			'filter_items_list'     => _x( 'Filter parts list', 'Screen reader text for the filter links', CSF_Parts_Constants::TEXT_DOMAIN ),
			'items_list_navigation' => _x( 'Parts list navigation', 'Screen reader text for the pagination', CSF_Parts_Constants::TEXT_DOMAIN ),
			'items_list'            => _x( 'Parts list', 'Screen reader text for the items list', CSF_Parts_Constants::TEXT_DOMAIN ),
		);
	}

	/**
	 * Register custom meta fields.
	 *
	 * @since 1.0.0
	 */
	private static function register_meta_fields() {
		$meta_fields = array(
			CSF_Parts_Constants::META_SKU            => array(
				'type'         => 'string',
				'description'  => __( 'Part SKU', CSF_Parts_Constants::TEXT_DOMAIN ),
				'single'       => true,
				'show_in_rest' => true,
			),
			CSF_Parts_Constants::META_PRICE          => array(
				'type'         => 'number',
				'description'  => __( 'Part price', CSF_Parts_Constants::TEXT_DOMAIN ),
				'single'       => true,
				'show_in_rest' => true,
			),
			CSF_Parts_Constants::META_MANUFACTURER   => array(
				'type'         => 'string',
				'description'  => __( 'Manufacturer name', CSF_Parts_Constants::TEXT_DOMAIN ),
				'single'       => true,
				'show_in_rest' => true,
			),
			CSF_Parts_Constants::META_IN_STOCK       => array(
				'type'         => 'boolean',
				'description'  => __( 'In stock status', CSF_Parts_Constants::TEXT_DOMAIN ),
				'single'       => true,
				'show_in_rest' => true,
			),
			CSF_Parts_Constants::META_POSITION       => array(
				'type'         => 'string',
				'description'  => __( 'Part position/location', CSF_Parts_Constants::TEXT_DOMAIN ),
				'single'       => true,
				'show_in_rest' => true,
			),
			CSF_Parts_Constants::META_SPECIFICATIONS => array(
				'type'         => 'string',
				'description'  => __( 'Part specifications (JSON)', CSF_Parts_Constants::TEXT_DOMAIN ),
				'single'       => true,
				'show_in_rest' => true,
			),
			CSF_Parts_Constants::META_FEATURES       => array(
				'type'         => 'string',
				'description'  => __( 'Part features (JSON)', CSF_Parts_Constants::TEXT_DOMAIN ),
				'single'       => true,
				'show_in_rest' => true,
			),
			CSF_Parts_Constants::META_TECH_NOTES     => array(
				'type'         => 'string',
				'description'  => __( 'Technical notes', CSF_Parts_Constants::TEXT_DOMAIN ),
				'single'       => true,
				'show_in_rest' => true,
			),
			CSF_Parts_Constants::META_SCRAPED_AT     => array(
				'type'         => 'string',
				'description'  => __( 'Last scrape timestamp', CSF_Parts_Constants::TEXT_DOMAIN ),
				'single'       => true,
				'show_in_rest' => true,
			),
		);

		foreach ( $meta_fields as $meta_key => $args ) {
			register_post_meta( CSF_Parts_Constants::POST_TYPE, $meta_key, $args );
		}
	}
}
