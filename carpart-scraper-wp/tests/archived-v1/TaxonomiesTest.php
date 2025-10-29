<?php
/**
 * Unit tests for CSF_Parts_Taxonomies class.
 *
 * Validates DRY principle implementation - single method generates all label variations.
 *
 * @package CSF_Parts_Catalog
 */

use PHPUnit\Framework\TestCase;

/**
 * Test Taxonomies class.
 */
final class TaxonomiesTest extends TestCase {

	/**
	 * Test that category labels are generated correctly.
	 *
	 * Validates DRY - uses shared generation method.
	 */
	public function test_category_labels_are_generated_correctly(): void {
		// Arrange
		$reflection = new ReflectionClass( CSF_Parts_Taxonomies::class );
		$method     = $reflection->getMethod( 'get_category_labels' );
		$method->setAccessible( true );

		// Act
		$labels = $method->invoke( null );

		// Assert
		$this->assertIsArray( $labels );
		$this->assertArrayHasKey( 'name', $labels );
		$this->assertArrayHasKey( 'singular_name', $labels );
		$this->assertArrayHasKey( 'menu_name', $labels );
		$this->assertArrayHasKey( 'all_items', $labels );

		// Category is hierarchical, should have parent labels.
		$this->assertArrayHasKey( 'parent_item', $labels );
		$this->assertArrayHasKey( 'parent_item_colon', $labels );
	}

	/**
	 * Test that make labels are generated correctly.
	 *
	 * Validates DRY - uses shared generation method.
	 */
	public function test_make_labels_are_generated_correctly(): void {
		// Arrange
		$reflection = new ReflectionClass( CSF_Parts_Taxonomies::class );
		$method     = $reflection->getMethod( 'get_make_labels' );
		$method->setAccessible( true );

		// Act
		$labels = $method->invoke( null );

		// Assert
		$this->assertIsArray( $labels );
		$this->assertArrayHasKey( 'name', $labels );
		$this->assertArrayHasKey( 'singular_name', $labels );

		// Make is NOT hierarchical, should NOT have parent labels.
		$this->assertArrayNotHasKey( 'parent_item', $labels );
		$this->assertArrayNotHasKey( 'parent_item_colon', $labels );
	}

	/**
	 * Test that model labels are generated correctly.
	 */
	public function test_model_labels_are_generated_correctly(): void {
		// Arrange
		$reflection = new ReflectionClass( CSF_Parts_Taxonomies::class );
		$method     = $reflection->getMethod( 'get_model_labels' );
		$method->setAccessible( true );

		// Act
		$labels = $method->invoke( null );

		// Assert
		$this->assertIsArray( $labels );
		$this->assertArrayHasKey( 'name', $labels );
		$this->assertArrayHasKey( 'singular_name', $labels );
		$this->assertArrayNotHasKey( 'parent_item', $labels );
	}

	/**
	 * Test that year labels are generated correctly.
	 */
	public function test_year_labels_are_generated_correctly(): void {
		// Arrange
		$reflection = new ReflectionClass( CSF_Parts_Taxonomies::class );
		$method     = $reflection->getMethod( 'get_year_labels' );
		$method->setAccessible( true );

		// Act
		$labels = $method->invoke( null );

		// Assert
		$this->assertIsArray( $labels );
		$this->assertArrayHasKey( 'name', $labels );
		$this->assertArrayHasKey( 'singular_name', $labels );
		$this->assertArrayNotHasKey( 'parent_item', $labels );
	}

	/**
	 * Test that label generation method produces complete label sets.
	 *
	 * Validates DRY - single method generates all required labels.
	 */
	public function test_label_generation_produces_complete_label_set(): void {
		// Arrange
		$reflection = new ReflectionClass( CSF_Parts_Taxonomies::class );
		$method     = $reflection->getMethod( 'generate_taxonomy_labels' );
		$method->setAccessible( true );

		$expected_labels = array(
			'name',
			'singular_name',
			'menu_name',
			'all_items',
			'new_item_name',
			'add_new_item',
			'edit_item',
			'update_item',
			'view_item',
			'separate_items_with_commas',
			'add_or_remove_items',
			'choose_from_most_used',
			'popular_items',
			'search_items',
			'not_found',
			'no_terms',
			'items_list',
			'items_list_navigation',
		);

		// Act
		$labels = $method->invoke(
			null,
			'Test Term',
			'Test Terms',
			'test term',
			'test terms',
			false
		);

		// Assert
		foreach ( $expected_labels as $label_key ) {
			$this->assertArrayHasKey(
				$label_key,
				$labels,
				"Label '{$label_key}' should be present in generated labels"
			);
		}
	}

	/**
	 * Test that hierarchical parameter adds parent labels.
	 *
	 * Validates DRY - single method handles both hierarchical and flat taxonomies.
	 */
	public function test_hierarchical_parameter_adds_parent_labels(): void {
		// Arrange
		$reflection = new ReflectionClass( CSF_Parts_Taxonomies::class );
		$method     = $reflection->getMethod( 'generate_taxonomy_labels' );
		$method->setAccessible( true );

		// Act - Non-hierarchical.
		$flat_labels = $method->invoke(
			null,
			'Term',
			'Terms',
			'term',
			'terms',
			false
		);

		// Act - Hierarchical.
		$hierarchical_labels = $method->invoke(
			null,
			'Term',
			'Terms',
			'term',
			'terms',
			true
		);

		// Assert
		$this->assertArrayNotHasKey( 'parent_item', $flat_labels );
		$this->assertArrayNotHasKey( 'parent_item_colon', $flat_labels );

		$this->assertArrayHasKey( 'parent_item', $hierarchical_labels );
		$this->assertArrayHasKey( 'parent_item_colon', $hierarchical_labels );
	}

	/**
	 * Test that all taxonomy methods use the shared generator.
	 *
	 * Validates DRY - no duplicate label generation code.
	 */
	public function test_all_taxonomy_methods_use_shared_generator(): void {
		// Arrange
		$reflection         = new ReflectionClass( CSF_Parts_Taxonomies::class );
		$generator_method   = $reflection->getMethod( 'generate_taxonomy_labels' );
		$category_method    = $reflection->getMethod( 'get_category_labels' );
		$make_method        = $reflection->getMethod( 'get_make_labels' );
		$model_method       = $reflection->getMethod( 'get_model_labels' );
		$year_method        = $reflection->getMethod( 'get_year_labels' );

		$generator_method->setAccessible( true );
		$category_method->setAccessible( true );
		$make_method->setAccessible( true );
		$model_method->setAccessible( true );
		$year_method->setAccessible( true );

		// Get source code of each method.
		$category_source = $this->get_method_source( $category_method );
		$make_source     = $this->get_method_source( $make_method );
		$model_source    = $this->get_method_source( $model_method );
		$year_source     = $this->get_method_source( $year_method );

		// Assert - Each method should call generate_taxonomy_labels.
		$this->assertStringContainsString(
			'generate_taxonomy_labels',
			$category_source,
			'get_category_labels should use generate_taxonomy_labels'
		);

		$this->assertStringContainsString(
			'generate_taxonomy_labels',
			$make_source,
			'get_make_labels should use generate_taxonomy_labels'
		);

		$this->assertStringContainsString(
			'generate_taxonomy_labels',
			$model_source,
			'get_model_labels should use generate_taxonomy_labels'
		);

		$this->assertStringContainsString(
			'generate_taxonomy_labels',
			$year_source,
			'get_year_labels should use generate_taxonomy_labels'
		);

		// Assert - Methods should be SHORT (just call generator with params).
		$this->assertLessThan(
			10,
			substr_count( $category_source, "\n" ),
			'get_category_labels should be short (just calls generator)'
		);

		$this->assertLessThan(
			10,
			substr_count( $make_source, "\n" ),
			'get_make_labels should be short (just calls generator)'
		);
	}

	/**
	 * Test that label strings contain proper parameterization.
	 *
	 * Validates DRY - singular/plural forms properly substituted.
	 */
	public function test_label_strings_use_proper_parameterization(): void {
		// Arrange
		$reflection = new ReflectionClass( CSF_Parts_Taxonomies::class );
		$method     = $reflection->getMethod( 'generate_taxonomy_labels' );
		$method->setAccessible( true );

		// Act
		$labels = $method->invoke(
			null,
			'Radiator',
			'Radiators',
			'radiator',
			'radiators',
			false
		);

		// Assert - Check that parameters are properly used in labels.
		$this->assertStringContainsString( 'Radiator', $labels['singular_name'] );
		$this->assertStringContainsString( 'Radiators', $labels['name'] );
		$this->assertStringContainsString( 'radiators', $labels['separate_items_with_commas'] );
	}

	/**
	 * Helper method to get method source code.
	 *
	 * @param ReflectionMethod $method Method to get source for.
	 * @return string Method source code.
	 */
	private function get_method_source( ReflectionMethod $method ): string {
		$filename = $method->getFileName();
		$start    = $method->getStartLine() - 1;
		$end      = $method->getEndLine();
		$length   = $end - $start;

		$source = file( $filename );
		return implode( '', array_slice( $source, $start, $length ) );
	}
}
