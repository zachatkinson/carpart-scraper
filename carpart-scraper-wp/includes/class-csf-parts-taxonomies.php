<?php
/**
 * Register custom taxonomies.
 *
 * @package CSF_Parts_Catalog
 * @since   1.0.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

/**
 * Class CSF_Parts_Taxonomies
 */
class CSF_Parts_Taxonomies {

	/**
	 * Constructor.
	 */
	public function __construct() {
		add_action( 'init', array( $this, 'register' ) );
	}

	/**
	 * Register all custom taxonomies.
	 *
	 * @since 1.0.0
	 */
	public static function register(): void {
		// Register Part Category taxonomy.
		register_taxonomy(
			CSF_Parts_Constants::TAXONOMY_CATEGORY,
			array( CSF_Parts_Constants::POST_TYPE ),
			array(
				'labels'            => self::get_category_labels(),
				'hierarchical'      => true,
				'public'            => true,
				'show_ui'           => true,
				'show_admin_column' => true,
				'show_in_nav_menus' => true,
				'show_tagcloud'     => true,
				'show_in_rest'      => true,
				'rest_base'         => 'part-categories',
				'rewrite'           => array( 'slug' => 'part-category' ),
			)
		);

		// Register Vehicle Make taxonomy.
		register_taxonomy(
			CSF_Parts_Constants::TAXONOMY_MAKE,
			array( CSF_Parts_Constants::POST_TYPE ),
			array(
				'labels'            => self::get_make_labels(),
				'hierarchical'      => false,
				'public'            => true,
				'show_ui'           => true,
				'show_admin_column' => true,
				'show_in_nav_menus' => true,
				'show_tagcloud'     => false,
				'show_in_rest'      => true,
				'rest_base'         => 'vehicle-makes',
				'rewrite'           => array( 'slug' => 'make' ),
			)
		);

		// Register Vehicle Model taxonomy.
		register_taxonomy(
			CSF_Parts_Constants::TAXONOMY_MODEL,
			array( CSF_Parts_Constants::POST_TYPE ),
			array(
				'labels'            => self::get_model_labels(),
				'hierarchical'      => false,
				'public'            => true,
				'show_ui'           => true,
				'show_admin_column' => true,
				'show_in_nav_menus' => true,
				'show_tagcloud'     => false,
				'show_in_rest'      => true,
				'rest_base'         => 'vehicle-models',
				'rewrite'           => array( 'slug' => 'model' ),
			)
		);

		// Register Vehicle Year taxonomy.
		register_taxonomy(
			CSF_Parts_Constants::TAXONOMY_YEAR,
			array( CSF_Parts_Constants::POST_TYPE ),
			array(
				'labels'            => self::get_year_labels(),
				'hierarchical'      => false,
				'public'            => true,
				'show_ui'           => true,
				'show_admin_column' => true,
				'show_in_nav_menus' => true,
				'show_tagcloud'     => false,
				'show_in_rest'      => true,
				'rest_base'         => 'vehicle-years',
				'rewrite'           => array( 'slug' => 'year' ),
			)
		);
	}

	/**
	 * Generate taxonomy labels from singular and plural forms.
	 *
	 * DRY implementation - single method generates all label variations.
	 *
	 * @since 1.0.0
	 * @param string $singular Singular form (e.g., 'Category').
	 * @param string $plural   Plural form (e.g., 'Categories').
	 * @param string $lowercase_singular Lowercase singular (e.g., 'category').
	 * @param string $lowercase_plural   Lowercase plural (e.g., 'categories').
	 * @param bool   $hierarchical Whether taxonomy is hierarchical.
	 * @return array Complete labels array.
	 */
	private static function generate_taxonomy_labels(
		string $singular,
		string $plural,
		string $lowercase_singular,
		string $lowercase_plural,
		bool $hierarchical = false
	): array {
		$labels = array(
			'name'                       => _x( $plural, 'Taxonomy general name', CSF_Parts_Constants::TEXT_DOMAIN ),
			'singular_name'              => _x( $singular, 'Taxonomy singular name', CSF_Parts_Constants::TEXT_DOMAIN ),
			'menu_name'                  => __( $plural, CSF_Parts_Constants::TEXT_DOMAIN ),
			'all_items'                  => sprintf( __( 'All %s', CSF_Parts_Constants::TEXT_DOMAIN ), $plural ),
			'new_item_name'              => sprintf( __( 'New %s Name', CSF_Parts_Constants::TEXT_DOMAIN ), $singular ),
			'add_new_item'               => sprintf( __( 'Add New %s', CSF_Parts_Constants::TEXT_DOMAIN ), $singular ),
			'edit_item'                  => sprintf( __( 'Edit %s', CSF_Parts_Constants::TEXT_DOMAIN ), $singular ),
			'update_item'                => sprintf( __( 'Update %s', CSF_Parts_Constants::TEXT_DOMAIN ), $singular ),
			'view_item'                  => sprintf( __( 'View %s', CSF_Parts_Constants::TEXT_DOMAIN ), $singular ),
			'separate_items_with_commas' => sprintf( __( 'Separate %s with commas', CSF_Parts_Constants::TEXT_DOMAIN ), $lowercase_plural ),
			'add_or_remove_items'        => sprintf( __( 'Add or remove %s', CSF_Parts_Constants::TEXT_DOMAIN ), $lowercase_plural ),
			'choose_from_most_used'      => __( 'Choose from the most used', CSF_Parts_Constants::TEXT_DOMAIN ),
			'popular_items'              => sprintf( __( 'Popular %s', CSF_Parts_Constants::TEXT_DOMAIN ), $plural ),
			'search_items'               => sprintf( __( 'Search %s', CSF_Parts_Constants::TEXT_DOMAIN ), $plural ),
			'not_found'                  => sprintf( __( 'No %s found', CSF_Parts_Constants::TEXT_DOMAIN ), $lowercase_plural ),
			'no_terms'                   => sprintf( __( 'No %s', CSF_Parts_Constants::TEXT_DOMAIN ), $lowercase_plural ),
			'items_list'                 => sprintf( __( '%s list', CSF_Parts_Constants::TEXT_DOMAIN ), $plural ),
			'items_list_navigation'      => sprintf( __( '%s list navigation', CSF_Parts_Constants::TEXT_DOMAIN ), $plural ),
		);

		// Add hierarchical-specific labels.
		if ( $hierarchical ) {
			$labels['parent_item']       = sprintf( __( 'Parent %s', CSF_Parts_Constants::TEXT_DOMAIN ), $singular );
			$labels['parent_item_colon'] = sprintf( __( 'Parent %s:', CSF_Parts_Constants::TEXT_DOMAIN ), $singular );
		}

		return $labels;
	}

	/**
	 * Get part category taxonomy labels.
	 *
	 * @since 1.0.0
	 * @return array Labels array.
	 */
	private static function get_category_labels(): array {
		return self::generate_taxonomy_labels(
			'Part Category',
			'Part Categories',
			'category',
			'categories',
			true
		);
	}

	/**
	 * Get vehicle make taxonomy labels.
	 *
	 * @since 1.0.0
	 * @return array Labels array.
	 */
	private static function get_make_labels(): array {
		return self::generate_taxonomy_labels(
			'Vehicle Make',
			'Vehicle Makes',
			'make',
			'makes',
			false
		);
	}

	/**
	 * Get vehicle model taxonomy labels.
	 *
	 * @since 1.0.0
	 * @return array Labels array.
	 */
	private static function get_model_labels(): array {
		return self::generate_taxonomy_labels(
			'Vehicle Model',
			'Vehicle Models',
			'model',
			'models',
			false
		);
	}

	/**
	 * Get vehicle year taxonomy labels.
	 *
	 * @since 1.0.0
	 * @return array Labels array.
	 */
	private static function get_year_labels(): array {
		return self::generate_taxonomy_labels(
			'Vehicle Year',
			'Vehicle Years',
			'year',
			'years',
			false
		);
	}
}
