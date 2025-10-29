<?php
/**
 * Unit tests for Import_Source_Factory.
 *
 * Validates Factory Pattern implementation:
 * - Encapsulates object creation logic
 * - Returns objects implementing strategy interface
 * - Uses constants instead of magic strings
 * - Follows Open/Closed Principle (easy to add new types)
 *
 * @package CSF_Parts_Catalog
 */

use PHPUnit\Framework\TestCase;

/**
 * Test Import Source Factory.
 */
final class ImportSourceFactoryTest extends TestCase {

	/**
	 * Test that factory class exists.
	 */
	public function test_factory_class_exists(): void {
		// Assert
		$this->assertTrue(
			class_exists( Import_Source_Factory::class ),
			'Import_Source_Factory class should exist'
		);
	}

	/**
	 * Test that factory has static create method.
	 *
	 * Validates that factory uses static method pattern.
	 */
	public function test_factory_has_static_create_method(): void {
		// Arrange
		$reflection = new ReflectionClass( Import_Source_Factory::class );

		// Assert
		$this->assertTrue(
			$reflection->hasMethod( 'create' ),
			'Factory should have create() method'
		);

		$create_method = $reflection->getMethod( 'create' );

		$this->assertTrue(
			$create_method->isStatic(),
			'create() should be static method'
		);

		$this->assertTrue(
			$create_method->isPublic(),
			'create() should be public'
		);
	}

	/**
	 * Test that factory has create_from_options method.
	 *
	 * Validates convenience method for WordPress options integration.
	 */
	public function test_factory_has_create_from_options_method(): void {
		// Arrange
		$reflection = new ReflectionClass( Import_Source_Factory::class );

		// Assert
		$this->assertTrue(
			$reflection->hasMethod( 'create_from_options' ),
			'Factory should have create_from_options() method'
		);

		$method = $reflection->getMethod( 'create_from_options' );

		$this->assertTrue(
			$method->isStatic(),
			'create_from_options() should be static'
		);

		$this->assertTrue(
			$method->isPublic(),
			'create_from_options() should be public'
		);
	}

	/**
	 * Test that create method returns strategy interface.
	 *
	 * Validates Dependency Inversion - depends on abstraction, not concretion.
	 */
	public function test_create_method_returns_strategy_interface(): void {
		// Arrange
		$reflection = new ReflectionClass( Import_Source_Factory::class );
		$method     = $reflection->getMethod( 'create' );

		// Assert
		$this->assertTrue(
			$method->hasReturnType(),
			'create() should have return type'
		);

		$return_type = $method->getReturnType();

		// Return type should be the strategy interface.
		$this->assertEquals(
			Import_Source_Strategy::class,
			$return_type->getName(),
			'create() should return Import_Source_Strategy interface'
		);
	}

	/**
	 * Test that factory uses constants for source types.
	 *
	 * Validates DRY - no magic strings.
	 */
	public function test_factory_uses_constants_for_source_types(): void {
		// Arrange
		$reflection = new ReflectionClass( Import_Source_Factory::class );
		$method     = $reflection->getMethod( 'create' );
		$filename   = $method->getFileName();
		$start_line = $method->getStartLine();
		$end_line   = $method->getEndLine();

		// Get method source code.
		$source        = file( $filename );
		$method_source = implode(
			'',
			array_slice( $source, $start_line - 1, $end_line - $start_line + 1 )
		);

		// Assert - Should use constants, not magic strings.
		$this->assertStringContainsString(
			'CSF_Parts_Constants::IMPORT_SOURCE',
			$method_source,
			'Factory should use constants for source types (no magic strings)'
		);

		// Should NOT have hardcoded strings like 'url' or 'directory'.
		$this->assertStringNotContainsString(
			"'url'",
			str_replace( 'IMPORT_SOURCE_URL', '', $method_source ), // Exclude constant names
			'Factory should not use magic string "url"'
		);

		$this->assertStringNotContainsString(
			"'directory'",
			str_replace( 'IMPORT_SOURCE_DIRECTORY', '', $method_source ),
			'Factory should not use magic string "directory"'
		);
	}

	/**
	 * Test that factory method accepts source type parameter.
	 *
	 * Validates that factory is configurable.
	 */
	public function test_create_method_accepts_source_type_parameter(): void {
		// Arrange
		$reflection = new ReflectionClass( Import_Source_Factory::class );
		$method     = $reflection->getMethod( 'create' );
		$params     = $method->getParameters();

		// Assert
		$this->assertGreaterThan(
			0,
			count( $params ),
			'create() should accept parameters'
		);

		$first_param = $params[0];

		$this->assertEquals(
			'source_type',
			$first_param->getName(),
			'First parameter should be source_type'
		);

		// Should have type hint.
		$this->assertTrue(
			$first_param->hasType(),
			'source_type parameter should have type hint'
		);

		$this->assertEquals(
			'string',
			$first_param->getType()->getName(),
			'source_type should be string'
		);
	}

	/**
	 * Test that factory has separate creation methods for each strategy.
	 *
	 * Validates Single Responsibility - each creation method handles one type.
	 */
	public function test_factory_has_separate_creation_methods(): void {
		// Arrange
		$reflection = new ReflectionClass( Import_Source_Factory::class );

		// Assert - Should have specific factory methods.
		$this->assertTrue(
			$reflection->hasMethod( 'create_url_source' ),
			'Factory should have create_url_source() method'
		);

		$this->assertTrue(
			$reflection->hasMethod( 'create_directory_source' ),
			'Factory should have create_directory_source() method'
		);

		// These methods should be private (implementation details).
		$url_method = $reflection->getMethod( 'create_url_source' );
		$dir_method = $reflection->getMethod( 'create_directory_source' );

		$this->assertTrue(
			$url_method->isPrivate() || $url_method->isProtected(),
			'create_url_source() should be private/protected (implementation detail)'
		);

		$this->assertTrue(
			$dir_method->isPrivate() || $dir_method->isProtected(),
			'create_directory_source() should be private/protected (implementation detail)'
		);
	}

	/**
	 * Test that factory throws exception for unknown source type.
	 *
	 * Validates error handling.
	 */
	public function test_factory_handles_unknown_source_type(): void {
		// Arrange
		$reflection = new ReflectionClass( Import_Source_Factory::class );
		$method     = $reflection->getMethod( 'create' );
		$filename   = $method->getFileName();
		$start_line = $method->getStartLine();
		$end_line   = $method->getEndLine();

		// Get method source code.
		$source        = file( $filename );
		$method_source = implode(
			'',
			array_slice( $source, $start_line - 1, $end_line - $start_line + 1 )
		);

		// Assert - Should throw exception for unknown type.
		$this->assertStringContainsString(
			'Exception',
			$method_source,
			'Factory should throw exception for unknown source type'
		);

		$this->assertStringContainsString(
			'default:',
			$method_source,
			'Factory should have default case in switch statement'
		);
	}

	/**
	 * Test that factory uses switch statement for type selection.
	 *
	 * Validates Open/Closed - switch makes it easy to add new types.
	 */
	public function test_factory_uses_switch_for_type_selection(): void {
		// Arrange
		$reflection = new ReflectionClass( Import_Source_Factory::class );
		$method     = $reflection->getMethod( 'create' );
		$filename   = $method->getFileName();
		$start_line = $method->getStartLine();
		$end_line   = $method->getEndLine();

		// Get method source code.
		$source        = file( $filename );
		$method_source = implode(
			'',
			array_slice( $source, $start_line - 1, $end_line - $start_line + 1 )
		);

		// Assert - Should use switch statement.
		$this->assertStringContainsString(
			'switch',
			$method_source,
			'Factory should use switch statement for type selection'
		);

		$this->assertStringContainsString(
			'case',
			$method_source,
			'Factory should have case statements for each type'
		);
	}

	/**
	 * Test that factory follows Open/Closed Principle.
	 *
	 * Validates that adding new source types is straightforward.
	 */
	public function test_factory_follows_open_closed_principle(): void {
		// Arrange
		$reflection = new ReflectionClass( Import_Source_Factory::class );

		// Assert - Factory should not have hardcoded if/else chains.
		$source = file_get_contents( $reflection->getFileName() );

		// Count switch statements (should have one).
		$switch_count = substr_count( $source, 'switch' );

		$this->assertGreaterThanOrEqual(
			1,
			$switch_count,
			'Factory should use switch for extensibility'
		);

		// Factory should have minimal public methods (just create() and create_from_options()).
		$public_methods = $reflection->getMethods( ReflectionMethod::IS_PUBLIC );
		$method_names   = array_map(
			function ( ReflectionMethod $method ): string {
				return $method->getName();
			},
			$public_methods
		);

		$this->assertContains( 'create', $method_names );
		$this->assertContains( 'create_from_options', $method_names );

		// Should not have many public methods (indicates tight coupling).
		$this->assertLessThanOrEqual(
			3,
			count( $public_methods ),
			'Factory should have minimal public interface'
		);
	}

	/**
	 * Test that factory encapsulates WordPress option reading.
	 *
	 * Validates separation of concerns.
	 */
	public function test_factory_encapsulates_wordpress_option_reading(): void {
		// Arrange
		$reflection = new ReflectionClass( Import_Source_Factory::class );
		$method     = $reflection->getMethod( 'create_from_options' );
		$filename   = $method->getFileName();
		$start_line = $method->getStartLine();
		$end_line   = $method->getEndLine();

		// Get method source code.
		$source        = file( $filename );
		$method_source = implode(
			'',
			array_slice( $source, $start_line - 1, $end_line - $start_line + 1 )
		);

		// Assert - Should call get_option().
		$this->assertStringContainsString(
			'get_option',
			$method_source,
			'create_from_options() should read WordPress options'
		);

		// Should use constant for option name.
		$this->assertStringContainsString(
			'csf_parts_import_source',
			$method_source,
			'Should use standard option name'
		);

		// Should delegate to create() method.
		$this->assertStringContainsString(
			'self::create',
			$method_source,
			'create_from_options() should delegate to create() method'
		);
	}

	/**
	 * Test that factory methods return correct types.
	 *
	 * Validates type safety.
	 */
	public function test_factory_methods_have_proper_return_types(): void {
		// Arrange
		$reflection         = new ReflectionClass( Import_Source_Factory::class );
		$create_method      = $reflection->getMethod( 'create' );
		$url_method         = $reflection->getMethod( 'create_url_source' );
		$directory_method   = $reflection->getMethod( 'create_directory_source' );
		$from_options_method = $reflection->getMethod( 'create_from_options' );

		// Assert - All should have return types.
		$this->assertTrue(
			$create_method->hasReturnType(),
			'create() should have return type'
		);

		$this->assertTrue(
			$url_method->hasReturnType(),
			'create_url_source() should have return type'
		);

		$this->assertTrue(
			$directory_method->hasReturnType(),
			'create_directory_source() should have return type'
		);

		$this->assertTrue(
			$from_options_method->hasReturnType(),
			'create_from_options() should have return type'
		);

		// All should return strategy interface or concrete implementations.
		$this->assertEquals(
			Import_Source_Strategy::class,
			$create_method->getReturnType()->getName()
		);

		// Specific factory methods return concrete types.
		$this->assertEquals(
			URL_Import_Source::class,
			$url_method->getReturnType()->getName()
		);

		$this->assertEquals(
			Directory_Import_Source::class,
			$directory_method->getReturnType()->getName()
		);
	}

	/**
	 * Test that factory does not have constructor.
	 *
	 * Validates that factory is stateless utility class.
	 */
	public function test_factory_is_stateless(): void {
		// Arrange
		$reflection = new ReflectionClass( Import_Source_Factory::class );

		// Assert - Should not have properties (stateless).
		$properties = $reflection->getProperties();

		$this->assertCount(
			0,
			$properties,
			'Factory should be stateless (no properties)'
		);

		// All methods should be static.
		$public_methods = $reflection->getMethods( ReflectionMethod::IS_PUBLIC );

		foreach ( $public_methods as $method ) {
			$this->assertTrue(
				$method->isStatic(),
				"{$method->getName()} should be static"
			);
		}
	}
}
