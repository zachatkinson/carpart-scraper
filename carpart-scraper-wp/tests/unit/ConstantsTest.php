<?php
/**
 * Unit tests for CSF_Parts_Constants class.
 *
 * Validates that all constants are properly defined and eliminates magic strings/numbers.
 *
 * @package CSF_Parts_Catalog
 */

use PHPUnit\Framework\TestCase;

/**
 * Test Constants class.
 */
final class ConstantsTest extends TestCase {

	/**
	 * Test that post type constant is defined.
	 */
	public function test_post_type_constant_is_defined(): void {
		// Arrange & Act
		$post_type = CSF_Parts_Constants::POST_TYPE;

		// Assert
		$this->assertIsString( $post_type );
		$this->assertEquals( 'csf_part', $post_type );
	}

	/**
	 * Test that all taxonomy constants are defined.
	 */
	public function test_taxonomy_constants_are_defined(): void {
		// Arrange & Act
		$category = CSF_Parts_Constants::TAXONOMY_CATEGORY;
		$make     = CSF_Parts_Constants::TAXONOMY_MAKE;
		$model    = CSF_Parts_Constants::TAXONOMY_MODEL;
		$year     = CSF_Parts_Constants::TAXONOMY_YEAR;

		// Assert
		$this->assertEquals( 'part_category', $category );
		$this->assertEquals( 'vehicle_make', $make );
		$this->assertEquals( 'vehicle_model', $model );
		$this->assertEquals( 'vehicle_year', $year );
	}

	/**
	 * Test that all meta field constants are defined.
	 */
	public function test_meta_field_constants_are_defined(): void {
		// Arrange
		$expected_meta_fields = array(
			'META_SKU'            => '_csf_sku',
			'META_PRICE'          => '_csf_price',
			'META_MANUFACTURER'   => '_csf_manufacturer',
			'META_IN_STOCK'       => '_csf_in_stock',
			'META_POSITION'       => '_csf_position',
			'META_SPECIFICATIONS' => '_csf_specifications',
			'META_FEATURES'       => '_csf_features',
			'META_TECH_NOTES'     => '_csf_tech_notes',
			'META_SCRAPED_AT'     => '_csf_scraped_at',
		);

		// Act & Assert
		foreach ( $expected_meta_fields as $constant_name => $expected_value ) {
			$actual_value = constant( 'CSF_Parts_Constants::' . $constant_name );
			$this->assertEquals(
				$expected_value,
				$actual_value,
				"Constant {$constant_name} should equal {$expected_value}"
			);
		}
	}

	/**
	 * Test REST API constants are defined.
	 */
	public function test_rest_api_constants_are_defined(): void {
		// Arrange & Act
		$namespace = CSF_Parts_Constants::REST_NAMESPACE;

		// Assert
		$this->assertEquals( 'csf/v1', $namespace );
	}

	/**
	 * Test cache duration constant is defined with sensible default.
	 */
	public function test_cache_duration_constant_has_sensible_default(): void {
		// Arrange & Act
		$cache_duration = CSF_Parts_Constants::CACHE_DURATION_DEFAULT;

		// Assert
		$this->assertIsInt( $cache_duration );
		$this->assertGreaterThan( 0, $cache_duration );
		$this->assertEquals( 3600, $cache_duration ); // 1 hour
	}

	/**
	 * Test import batch size constant is defined.
	 */
	public function test_import_batch_size_constant_is_defined(): void {
		// Arrange & Act
		$batch_size = CSF_Parts_Constants::IMPORT_BATCH_SIZE_DEFAULT;

		// Assert
		$this->assertIsInt( $batch_size );
		$this->assertGreaterThan( 0, $batch_size );
		$this->assertEquals( 50, $batch_size );
	}

	/**
	 * Test HTTP status code constants are defined.
	 */
	public function test_http_status_constants_are_defined(): void {
		// Arrange & Act
		$http_ok                 = CSF_Parts_Constants::HTTP_OK;
		$http_unauthorized       = CSF_Parts_Constants::HTTP_UNAUTHORIZED;
		$http_not_found          = CSF_Parts_Constants::HTTP_NOT_FOUND;
		$http_internal_error     = CSF_Parts_Constants::HTTP_INTERNAL_SERVER_ERROR;

		// Assert
		$this->assertEquals( 200, $http_ok );
		$this->assertEquals( 401, $http_unauthorized );
		$this->assertEquals( 404, $http_not_found );
		$this->assertEquals( 500, $http_internal_error );
	}

	/**
	 * Test text domain constant is defined.
	 */
	public function test_text_domain_constant_is_defined(): void {
		// Arrange & Act
		$text_domain = CSF_Parts_Constants::TEXT_DOMAIN;

		// Assert
		$this->assertEquals( 'csf-parts', $text_domain );
	}

	/**
	 * Test import source constants are defined.
	 */
	public function test_import_source_constants_are_defined(): void {
		// Arrange & Act
		$url_source       = CSF_Parts_Constants::IMPORT_SOURCE_URL;
		$directory_source = CSF_Parts_Constants::IMPORT_SOURCE_DIRECTORY;

		// Assert
		$this->assertEquals( 'url', $url_source );
		$this->assertEquals( 'directory', $directory_source );
	}

	/**
	 * Test that Constants class cannot be instantiated.
	 *
	 * Validates Single Responsibility - this is a constants container, not an object.
	 */
	public function test_constants_class_is_final(): void {
		// Arrange
		$reflection = new ReflectionClass( CSF_Parts_Constants::class );

		// Assert
		$this->assertTrue(
			$reflection->isFinal(),
			'CSF_Parts_Constants should be final to prevent inheritance'
		);
	}
}
