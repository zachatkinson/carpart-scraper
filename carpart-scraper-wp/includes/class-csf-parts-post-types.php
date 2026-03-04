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
			'name'                  => 'Parts',
			'singular_name'         => 'Part',
			'menu_name'             => 'Parts',
			'name_admin_bar'        => 'Part',
			'add_new'               => 'Add New',
			'add_new_item'          => 'Add New Part',
			'new_item'              => 'New Part',
			'edit_item'             => 'Edit Part',
			'view_item'             => 'View Part',
			'all_items'             => 'All Parts',
			'search_items'          => 'Search Parts',
			'parent_item_colon'     => 'Parent Parts:',
			'not_found'             => 'No parts found.',
			'not_found_in_trash'    => 'No parts found in Trash.',
			'featured_image'        => 'Part Image',
			'set_featured_image'    => 'Set part image',
			'remove_featured_image' => 'Remove part image',
			'use_featured_image'    => 'Use as part image',
			'archives'              => 'Part archives',
			'insert_into_item'      => 'Insert into part',
			'uploaded_to_this_item' => 'Uploaded to this part',
			'filter_items_list'     => 'Filter parts list',
			'items_list_navigation' => 'Parts list navigation',
			'items_list'            => 'Parts list',
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
				'description'  => 'Part SKU',
				'single'       => true,
				'show_in_rest' => true,
			),
			CSF_Parts_Constants::META_PRICE          => array(
				'type'         => 'number',
				'description'  => 'Part price',
				'single'       => true,
				'show_in_rest' => true,
			),
			CSF_Parts_Constants::META_MANUFACTURER   => array(
				'type'         => 'string',
				'description'  => 'Manufacturer name',
				'single'       => true,
				'show_in_rest' => true,
			),
			CSF_Parts_Constants::META_IN_STOCK       => array(
				'type'         => 'boolean',
				'description'  => 'In stock status',
				'single'       => true,
				'show_in_rest' => true,
			),
			CSF_Parts_Constants::META_POSITION       => array(
				'type'         => 'string',
				'description'  => 'Part position/location',
				'single'       => true,
				'show_in_rest' => true,
			),
			CSF_Parts_Constants::META_SPECIFICATIONS => array(
				'type'         => 'string',
				'description'  => 'Part specifications (JSON)',
				'single'       => true,
				'show_in_rest' => true,
			),
			CSF_Parts_Constants::META_FEATURES       => array(
				'type'         => 'string',
				'description'  => 'Part features (JSON)',
				'single'       => true,
				'show_in_rest' => true,
			),
			CSF_Parts_Constants::META_TECH_NOTES     => array(
				'type'         => 'string',
				'description'  => 'Technical notes',
				'single'       => true,
				'show_in_rest' => true,
			),
			CSF_Parts_Constants::META_SCRAPED_AT     => array(
				'type'         => 'string',
				'description'  => 'Last scrape timestamp',
				'single'       => true,
				'show_in_rest' => true,
			),
		);

		foreach ( $meta_fields as $meta_key => $args ) {
			register_post_meta( CSF_Parts_Constants::POST_TYPE, $meta_key, $args );
		}
	}
}
