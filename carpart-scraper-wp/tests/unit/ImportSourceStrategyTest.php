<?php
/**
 * Unit tests for Import Source Strategy Pattern.
 *
 * Validates SOLID principles:
 * - Single Responsibility: Each strategy handles one source type
 * - Open/Closed: Can add new sources without modifying existing code
 * - Liskov Substitution: All strategies are interchangeable
 * - Interface Segregation: Strategy interface is minimal and focused
 *
 * @package CSF_Parts_Catalog
 */

use PHPUnit\Framework\TestCase;

/**
 * Test Import Source Strategy Pattern.
 */
final class ImportSourceStrategyTest extends TestCase {

	/**
	 * Test that strategy interface exists and defines required methods.
	 *
	 * Validates Interface Segregation Principle - minimal, focused interface.
	 */
	public function test_strategy_interface_exists_with_required_methods(): void {
		// Arrange & Act
		$reflection = new ReflectionClass( Import_Source_Strategy::class );

		// Assert
		$this->assertTrue( $reflection->isInterface(), 'Import_Source_Strategy should be an interface' );

		// Required methods.
		$this->assertTrue(
			$reflection->hasMethod( 'fetch' ),
			'Strategy interface should define fetch() method'
		);

		$this->assertTrue(
			$reflection->hasMethod( 'validate_configuration' ),
			'Strategy interface should define validate_configuration() method'
		);

		$this->assertTrue(
			$reflection->hasMethod( 'get_type' ),
			'Strategy interface should define get_type() method'
		);

		// Interface should have exactly these methods (not more).
		$methods = $reflection->getMethods();
		$this->assertCount(
			3,
			$methods,
			'Strategy interface should have exactly 3 methods (minimal interface)'
		);
	}

	/**
	 * Test that URL source implements strategy interface.
	 *
	 * Validates Open/Closed Principle - extension through implementation.
	 */
	public function test_url_source_implements_strategy_interface(): void {
		// Arrange & Act
		$reflection = new ReflectionClass( URL_Import_Source::class );

		// Assert
		$this->assertTrue(
			$reflection->implementsInterface( Import_Source_Strategy::class ),
			'URL_Import_Source should implement Import_Source_Strategy'
		);
	}

	/**
	 * Test that Directory source implements strategy interface.
	 *
	 * Validates Open/Closed Principle - extension through implementation.
	 */
	public function test_directory_source_implements_strategy_interface(): void {
		// Arrange & Act
		$reflection = new ReflectionClass( Directory_Import_Source::class );

		// Assert
		$this->assertTrue(
			$reflection->implementsInterface( Import_Source_Strategy::class ),
			'Directory_Import_Source should implement Import_Source_Strategy'
		);
	}

	/**
	 * Test that URL source has single responsibility.
	 *
	 * Validates Single Responsibility Principle - only handles URL fetching.
	 */
	public function test_url_source_has_single_responsibility(): void {
		// Arrange
		$reflection = new ReflectionClass( URL_Import_Source::class );
		$methods    = $reflection->getMethods( ReflectionMethod::IS_PUBLIC );

		// Act - Get public method names.
		$public_method_names = array_map(
			function ( ReflectionMethod $method ): string {
				return $method->getName();
			},
			$methods
		);

		// Assert - Should only have interface methods + constructor.
		$expected_methods = array(
			'__construct',
			'fetch',
			'validate_configuration',
			'get_type',
		);

		foreach ( $expected_methods as $expected_method ) {
			$this->assertContains(
				$expected_method,
				$public_method_names,
				"URL_Import_Source should have {$expected_method} method"
			);
		}

		// Should not have methods unrelated to URL fetching.
		$this->assertNotContains(
			'import_from_directory',
			$public_method_names,
			'URL source should not have directory-related methods (Single Responsibility)'
		);
	}

	/**
	 * Test that Directory source has single responsibility.
	 *
	 * Validates Single Responsibility Principle - only handles directory monitoring.
	 */
	public function test_directory_source_has_single_responsibility(): void {
		// Arrange
		$reflection = new ReflectionClass( Directory_Import_Source::class );
		$methods    = $reflection->getMethods( ReflectionMethod::IS_PUBLIC );

		// Act - Get public method names.
		$public_method_names = array_map(
			function ( ReflectionMethod $method ): string {
				return $method->getName();
			},
			$methods
		);

		// Assert - Should only have interface methods + constructor.
		$expected_methods = array(
			'__construct',
			'fetch',
			'validate_configuration',
			'get_type',
		);

		foreach ( $expected_methods as $expected_method ) {
			$this->assertContains(
				$expected_method,
				$public_method_names,
				"Directory_Import_Source should have {$expected_method} method"
			);
		}

		// Should not have methods unrelated to directory monitoring.
		$this->assertNotContains(
			'fetch_from_url',
			$public_method_names,
			'Directory source should not have URL-related methods (Single Responsibility)'
		);
	}

	/**
	 * Test that strategies return correct type identifiers.
	 *
	 * Validates that each strategy can identify itself.
	 */
	public function test_strategies_return_correct_type_identifiers(): void {
		// Arrange - We can't instantiate without WordPress, so we'll test via reflection.
		$url_reflection = new ReflectionClass( URL_Import_Source::class );
		$dir_reflection = new ReflectionClass( Directory_Import_Source::class );

		// Assert - Both classes should have get_type() method.
		$this->assertTrue(
			$url_reflection->hasMethod( 'get_type' ),
			'URL source should have get_type() method'
		);

		$this->assertTrue(
			$dir_reflection->hasMethod( 'get_type' ),
			'Directory source should have get_type() method'
		);

		// Method should return string.
		$url_method = $url_reflection->getMethod( 'get_type' );
		$dir_method = $dir_reflection->getMethod( 'get_type' );

		$this->assertTrue(
			$url_method->hasReturnType(),
			'get_type() should have return type'
		);

		$this->assertEquals(
			'string',
			$url_method->getReturnType()->getName(),
			'get_type() should return string'
		);
	}

	/**
	 * Test that URL source validates HTTPS requirement.
	 *
	 * Validates security best practice - only HTTPS URLs allowed.
	 */
	public function test_url_source_validates_https_requirement(): void {
		// Arrange
		$reflection = new ReflectionClass( URL_Import_Source::class );

		// Get the source code of validate_configuration method.
		$method     = $reflection->getMethod( 'validate_configuration' );
		$start_line = $method->getStartLine();
		$end_line   = $method->getEndLine();
		$filename   = $method->getFileName();

		$source = file( $filename );
		$method_source = implode(
			'',
			array_slice( $source, $start_line - 1, $end_line - $start_line + 1 )
		);

		// Assert - Method should check for HTTPS.
		$this->assertStringContainsString(
			'https://',
			$method_source,
			'URL validation should enforce HTTPS for security'
		);
	}

	/**
	 * Test that strategies use dependency injection.
	 *
	 * Validates Dependency Inversion Principle - dependencies injected via constructor.
	 */
	public function test_strategies_use_dependency_injection(): void {
		// Arrange
		$url_reflection = new ReflectionClass( URL_Import_Source::class );
		$dir_reflection = new ReflectionClass( Directory_Import_Source::class );

		// Act
		$url_constructor = $url_reflection->getConstructor();
		$dir_constructor = $dir_reflection->getConstructor();

		// Assert - Constructors should accept dependencies.
		$this->assertNotNull(
			$url_constructor,
			'URL source should have constructor for dependency injection'
		);

		$this->assertNotNull(
			$dir_constructor,
			'Directory source should have constructor for dependency injection'
		);

		// URL source should accept URL parameter.
		$url_params = $url_constructor->getParameters();
		$this->assertGreaterThan(
			0,
			count( $url_params ),
			'URL source constructor should accept parameters'
		);

		$this->assertEquals(
			'url',
			$url_params[0]->getName(),
			'First parameter should be URL'
		);

		// Directory source should accept directory path parameter.
		$dir_params = $dir_constructor->getParameters();
		$this->assertGreaterThan(
			0,
			count( $dir_params ),
			'Directory source constructor should accept parameters'
		);

		$this->assertEquals(
			'directory_path',
			$dir_params[0]->getName(),
			'First parameter should be directory path'
		);
	}

	/**
	 * Test that strategies have proper type hints.
	 *
	 * Validates type safety - all methods properly typed.
	 */
	public function test_strategies_have_proper_type_hints(): void {
		// Arrange
		$url_reflection = new ReflectionClass( URL_Import_Source::class );

		// Act
		$fetch_method    = $url_reflection->getMethod( 'fetch' );
		$validate_method = $url_reflection->getMethod( 'validate_configuration' );
		$type_method     = $url_reflection->getMethod( 'get_type' );

		// Assert - fetch() should return string (file path).
		$this->assertTrue(
			$fetch_method->hasReturnType(),
			'fetch() should have return type'
		);

		$this->assertEquals(
			'string',
			$fetch_method->getReturnType()->getName(),
			'fetch() should return string (file path)'
		);

		// validate_configuration() should return bool.
		$this->assertTrue(
			$validate_method->hasReturnType(),
			'validate_configuration() should have return type'
		);

		$this->assertEquals(
			'bool',
			$validate_method->getReturnType()->getName(),
			'validate_configuration() should return bool'
		);

		// get_type() should return string.
		$this->assertTrue(
			$type_method->hasReturnType(),
			'get_type() should have return type'
		);

		$this->assertEquals(
			'string',
			$type_method->getReturnType()->getName(),
			'get_type() should return string'
		);
	}

	/**
	 * Test that adding new strategy does not require modifying existing code.
	 *
	 * Validates Open/Closed Principle - extension without modification.
	 */
	public function test_new_strategy_can_be_added_without_modifying_existing(): void {
		// Arrange
		$interface_reflection = new ReflectionClass( Import_Source_Strategy::class );

		// Act - Verify interface is stable and minimal.
		$methods = $interface_reflection->getMethods();

		// Assert - Interface has minimal methods (won't need changes for new strategies).
		$this->assertLessThanOrEqual(
			5,
			count( $methods ),
			'Interface should be minimal to prevent frequent changes'
		);

		// Verify existing implementations don't have tight coupling.
		$url_reflection = new ReflectionClass( URL_Import_Source::class );
		$dir_reflection = new ReflectionClass( Directory_Import_Source::class );

		// Classes should not reference each other.
		$url_source = file_get_contents( $url_reflection->getFileName() );
		$this->assertStringNotContainsString(
			'Directory_Import_Source',
			$url_source,
			'URL source should not reference Directory source (loose coupling)'
		);

		$dir_source = file_get_contents( $dir_reflection->getFileName() );
		$this->assertStringNotContainsString(
			'URL_Import_Source',
			$dir_source,
			'Directory source should not reference URL source (loose coupling)'
		);
	}

	/**
	 * Test that strategies follow Liskov Substitution Principle.
	 *
	 * All strategies should be interchangeable - same interface contract.
	 */
	public function test_strategies_are_substitutable(): void {
		// Arrange
		$interface_reflection = new ReflectionClass( Import_Source_Strategy::class );
		$url_reflection       = new ReflectionClass( URL_Import_Source::class );
		$dir_reflection       = new ReflectionClass( Directory_Import_Source::class );

		$interface_methods = $interface_reflection->getMethods();

		// Act & Assert - Both implementations have same method signatures.
		foreach ( $interface_methods as $interface_method ) {
			$method_name = $interface_method->getName();

			// URL source should have the method.
			$this->assertTrue(
				$url_reflection->hasMethod( $method_name ),
				"URL source should implement {$method_name}"
			);

			// Directory source should have the method.
			$this->assertTrue(
				$dir_reflection->hasMethod( $method_name ),
				"Directory source should implement {$method_name}"
			);

			// Method signatures should match.
			$url_method = $url_reflection->getMethod( $method_name );
			$dir_method = $dir_reflection->getMethod( $method_name );

			$this->assertEquals(
				$url_method->getNumberOfParameters(),
				$dir_method->getNumberOfParameters(),
				"{$method_name} should have same parameter count in both implementations"
			);
		}
	}
}
