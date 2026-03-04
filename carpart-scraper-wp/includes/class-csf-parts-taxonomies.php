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
			'name'                       => $plural,
			'singular_name'              => $singular,
			'menu_name'                  => $plural,
			'all_items'                  => sprintf( 'All %s', $plural ),
			'new_item_name'              => sprintf( 'New %s Name', $singular ),
			'add_new_item'               => sprintf( 'Add New %s', $singular ),
			'edit_item'                  => sprintf( 'Edit %s', $singular ),
			'update_item'                => sprintf( 'Update %s', $singular ),
			'view_item'                  => sprintf( 'View %s', $singular ),
			'separate_items_with_commas' => sprintf( 'Separate %s with commas', $lowercase_plural ),
			'add_or_remove_items'        => sprintf( 'Add or remove %s', $lowercase_plural ),
			'choose_from_most_used'      => 'Choose from the most used',
			'popular_items'              => sprintf( 'Popular %s', $plural ),
			'search_items'               => sprintf( 'Search %s', $plural ),
			'not_found'                  => sprintf( 'No %s found', $lowercase_plural ),
			'no_terms'                   => sprintf( 'No %s', $lowercase_plural ),
			'items_list'                 => sprintf( '%s list', $plural ),
			'items_list_navigation'      => sprintf( '%s list navigation', $plural ),
		);

		// Add hierarchical-specific labels.
		if ( $hierarchical ) {
			$labels['parent_item']       = sprintf( 'Parent %s', $singular );
			$labels['parent_item_colon'] = sprintf( 'Parent %s:', $singular );
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
