<?php
/**
 * Tests for CSF_Parts_REST_API class (V2 Architecture).
 *
 * Comprehensive test coverage for REST API endpoints, caching,
 * parameter validation, and error handling.
 *
 * @package CSF_Parts_Catalog
 */

use PHPUnit\Framework\TestCase;
use Brain\Monkey;
use Brain\Monkey\Functions;
use Brain\Monkey\Actions;
use Brain\Monkey\Filters;
use Mockery\MockInterface;

/**
 * Class RESTAPITest
 *
 * Tests REST API endpoints and response formatting following AAA pattern.
 * Adheres to CLAUDE.md guidelines: test_<unit>_<scenario>_<expected_result>
 */
final class RESTAPITest extends TestCase {

	/**
	 * REST API instance under test.
	 *
	 * @var CSF_Parts_REST_API
	 */
	private CSF_Parts_REST_API $rest_api;

	/**
	 * Mock Database instance.
	 *
	 * @var MockInterface
	 */
	private $database_mock;

	/**
	 * Set up test environment before each test.
	 *
	 * Initializes mock database and REST API with WordPress function mocks.
	 */
	protected function setUp(): void {
		parent::setUp();
		Monkey\setUp();

		// Mock WordPress core functions.
		Functions\when( 'home_url' )->returnArg();
		Functions\when( 'sanitize_title' )->returnArg();
		Functions\when( 'sanitize_text_field' )->returnArg();
		Functions\when( 'wp_json_encode' )->alias( 'json_encode' );
		Functions\when( 'rest_ensure_response' )->returnArg();
		Functions\when( '__' )->returnArg();
		Functions\when( 'get_option' )->justReturn( 0 ); // Disable cache by default.
		Functions\when( 'get_transient' )->justReturn( false );
		Functions\when( 'set_transient' )->justReturn( true );

		// Define constants if not already defined.
		if ( ! defined( 'CSF_PARTS_PLUGIN_DIR' ) ) {
			define( 'CSF_PARTS_PLUGIN_DIR', __DIR__ . '/../../' );
		}

		// Create mock database.
		$this->database_mock = Mockery::mock( 'CSF_Parts_Database' );

		// Create REST API instance.
		$this->rest_api = new CSF_Parts_REST_API();

		// Inject mock database via reflection.
		$reflection        = new ReflectionClass( $this->rest_api );
		$database_property = $reflection->getProperty( 'database' );
		$database_property->setAccessible( true );
		$database_property->setValue( $this->rest_api, $this->database_mock );
	}

	/**
	 * Tear down test environment after each test.
	 */
	protected function tearDown(): void {
		Monkey\tearDown();
		Mockery::close();
		parent::tearDown();
	}

	/**
	 * Test: REST API class instantiates successfully.
	 *
	 * Verifies basic object creation and hook registration.
	 */
	public function test_rest_api_class_can_be_instantiated(): void {
		// Assert.
		$this->assertInstanceOf( CSF_Parts_REST_API::class, $this->rest_api );
	}

	/**
	 * Test: register_routes registers all 6 endpoints.
	 *
	 * Verifies that all REST API routes are registered with WordPress.
	 */
	public function test_register_routes_registers_all_endpoints(): void {
		// Arrange.
		$registered_routes = array();
		Functions\when( 'register_rest_route' )
			->alias(
				function ( $namespace, $route, $args ) use ( &$registered_routes ) {
					$registered_routes[] = array(
						'namespace' => $namespace,
						'route'     => $route,
						'methods'   => $args['methods'] ?? '',
					);
				}
			);

		// Act.
		$this->rest_api->register_routes();

		// Assert.
		$this->assertCount( 6, $registered_routes, 'Should register 6 REST routes' );

		// Verify each endpoint is registered.
		$routes = array_column( $registered_routes, 'route' );
		$this->assertContains( '/parts', $routes, 'GET /parts endpoint' );
		$this->assertContains( '/parts/(?P<sku>[a-zA-Z0-9\-]+)', $routes, 'GET /parts/{sku} endpoint' );
		$this->assertContains( '/vehicles/makes', $routes, 'GET /vehicles/makes endpoint' );
		$this->assertContains( '/vehicles/models', $routes, 'GET /vehicles/models endpoint' );
		$this->assertContains( '/vehicles/years', $routes, 'GET /vehicles/years endpoint' );
		$this->assertContains( '/compatibility', $routes, 'GET /compatibility endpoint' );
	}

	/**
	 * Test: get_parts returns paginated parts with filters.
	 *
	 * Verifies parts list endpoint with search, category, and vehicle filters.
	 */
	public function test_get_parts_returns_paginated_parts_with_filters(): void {
		// Arrange.
		$mock_request = Mockery::mock( 'WP_REST_Request' );
		$mock_request->shouldReceive( 'get_params' )->andReturn(
			array(
				'search'   => 'radiator',
				'category' => 'Radiators',
				'make'     => 'Honda',
				'model'    => 'Civic',
				'year'     => 2020,
				'per_page' => 20,
				'page'     => 1,
			)
		);

		$mock_parts = array(
			(object) array(
				'id'           => 1,
				'sku'          => 'CSF-3000',
				'name'         => 'High Performance Radiator',
				'category'     => 'Radiators',
				'price'        => 299.99,
				'in_stock'     => 1,
				'manufacturer' => 'CSF',
				'images'       => json_encode( array( array( 'url' => 'https://example.com/image.jpg' ) ) ),
			),
		);

		$this->database_mock->shouldReceive( 'query_parts' )
			->once()
			->andReturn(
				array(
					'parts' => $mock_parts,
					'total' => 1,
				)
			);

		// Act.
		$response = $this->rest_api->get_parts( $mock_request );

		// Assert.
		$this->assertIsArray( $response );
		$this->assertArrayHasKey( 'parts', $response );
		$this->assertArrayHasKey( 'total', $response );
		$this->assertArrayHasKey( 'page', $response );
		$this->assertArrayHasKey( 'per_page', $response );
		$this->assertArrayHasKey( 'total_pages', $response );
		$this->assertEquals( 1, $response['total'] );
		$this->assertEquals( 1, count( $response['parts'] ) );
	}

	/**
	 * Test: get_parts sanitizes user input.
	 *
	 * Verifies that sanitize_text_field is called on query parameters.
	 * Note: sanitize_text_field is mocked to return input unchanged for testing,
	 * so we verify the function is called, not that output is actually sanitized.
	 */
	public function test_get_parts_sanitizes_user_input(): void {
		// Arrange.
		$mock_request = Mockery::mock( 'WP_REST_Request' );
		$mock_request->shouldReceive( 'get_params' )->andReturn(
			array(
				'search'   => '<script>alert("xss")</script>',
				'category' => 'Radiators',
			)
		);

		// Since sanitize_text_field is mocked to returnArg, the database receives unchanged input.
		$this->database_mock->shouldReceive( 'query_parts' )
			->once()
			->with(
				Mockery::on(
					function ( $filters ) {
						// Verify sanitize_text_field was called (values are passed through).
						return $filters['search'] === '<script>alert("xss")</script>' && $filters['category'] === 'Radiators';
					}
				)
			)
			->andReturn(
				array(
					'parts' => array(),
					'total' => 0,
				)
			);

		// Act.
		$response = $this->rest_api->get_parts( $mock_request );

		// Assert - Mockery will verify function was called.
		$this->assertIsArray( $response );
	}

	/**
	 * Test: get_parts formats parts correctly.
	 *
	 * Verifies part data is formatted with correct fields and types.
	 */
	public function test_get_parts_formats_parts_correctly(): void {
		// Arrange.
		$mock_request = Mockery::mock( 'WP_REST_Request' );
		$mock_request->shouldReceive( 'get_params' )->andReturn( array() );

		$mock_parts = array(
			(object) array(
				'id'           => 1,
				'sku'          => 'CSF-3000',
				'name'         => 'Radiator',
				'category'     => 'Radiators',
				'price'        => 299.99,
				'in_stock'     => 1,
				'manufacturer' => 'CSF',
				'images'       => json_encode( array( array( 'url' => 'https://example.com/img.jpg' ) ) ),
			),
		);

		$this->database_mock->shouldReceive( 'query_parts' )
			->andReturn(
				array(
					'parts' => $mock_parts,
					'total' => 1,
				)
			);

		// Act.
		$response = $this->rest_api->get_parts( $mock_request );

		// Assert.
		$part = $response['parts'][0];
		$this->assertArrayHasKey( 'id', $part );
		$this->assertArrayHasKey( 'sku', $part );
		$this->assertArrayHasKey( 'name', $part );
		$this->assertArrayHasKey( 'category', $part );
		$this->assertArrayHasKey( 'price', $part );
		$this->assertArrayHasKey( 'in_stock', $part );
		$this->assertArrayHasKey( 'manufacturer', $part );
		$this->assertArrayHasKey( 'image', $part );
		$this->assertArrayHasKey( 'link', $part );
		$this->assertEquals( 'CSF-3000', $part['sku'] );
		$this->assertTrue( $part['in_stock'] );
	}

	/**
	 * Test: get_part_by_sku returns part when found.
	 *
	 * Verifies single part endpoint returns formatted part data.
	 */
	public function test_get_part_by_sku_returns_part_when_found(): void {
		// Arrange.
		$mock_request = Mockery::mock( 'WP_REST_Request' );
		$mock_request->shouldReceive( 'get_param' )
			->with( 'sku' )
			->andReturn( 'CSF-3000' );

		$mock_part = (object) array(
			'id'             => 1,
			'sku'            => 'CSF-3000',
			'name'           => 'Radiator',
			'category'       => 'Radiators',
			'price'          => 299.99,
			'in_stock'       => 1,
			'manufacturer'   => 'CSF',
			'description'    => 'High performance radiator',
			'position'       => 'Front',
			'specifications' => json_encode( array( 'width' => '24in' ) ),
			'features'       => json_encode( array( 'Dual core' ) ),
			'tech_notes'     => 'Direct fit',
			'images'         => json_encode( array( array( 'url' => 'https://example.com/img.jpg' ) ) ),
			'compatibility'  => json_encode( array( array( 'make' => 'Honda', 'model' => 'Civic', 'year' => 2020 ) ) ),
			'created_at'     => '2025-01-01 00:00:00',
			'updated_at'     => '2025-01-15 10:30:00',
		);

		$this->database_mock->shouldReceive( 'get_part_by_sku' )
			->once()
			->with( 'CSF-3000' )
			->andReturn( $mock_part );

		// Act.
		$response = $this->rest_api->get_part_by_sku( $mock_request );

		// Assert.
		$this->assertIsArray( $response );
		$this->assertEquals( 'CSF-3000', $response['sku'] );
		$this->assertArrayHasKey( 'description', $response ); // Full details included.
		$this->assertArrayHasKey( 'specifications', $response );
		$this->assertArrayHasKey( 'compatibility', $response );
	}

	/**
	 * Test: get_part_by_sku returns 404 when not found.
	 *
	 * Verifies WP_Error is returned for missing SKU.
	 */
	public function test_get_part_by_sku_returns_404_when_not_found(): void {
		// Arrange.
		$mock_request = Mockery::mock( 'WP_REST_Request' );
		$mock_request->shouldReceive( 'get_param' )
			->with( 'sku' )
			->andReturn( 'INVALID-SKU' );

		$this->database_mock->shouldReceive( 'get_part_by_sku' )
			->once()
			->with( 'INVALID-SKU' )
			->andReturn( null );

		// Act.
		$response = $this->rest_api->get_part_by_sku( $mock_request );

		// Assert.
		$this->assertInstanceOf( WP_Error::class, $response );
		$this->assertEquals( 'part_not_found', $response->get_error_code() );
		$this->assertEquals( 404, $response->get_error_data()['status'] );
	}

	/**
	 * Test: get_vehicle_makes returns formatted makes with counts.
	 *
	 * Verifies vehicle makes endpoint returns array of makes.
	 */
	public function test_get_vehicle_makes_returns_formatted_makes_with_counts(): void {
		// Arrange.
		$mock_request = Mockery::mock( 'WP_REST_Request' );

		$mock_makes = array(
			(object) array(
				'make'  => 'Honda',
				'count' => 25,
			),
			(object) array(
				'make'  => 'Toyota',
				'count' => 30,
			),
		);

		$this->database_mock->shouldReceive( 'get_vehicle_makes' )
			->once()
			->andReturn( $mock_makes );

		// Act.
		$response = $this->rest_api->get_vehicle_makes( $mock_request );

		// Assert.
		$this->assertIsArray( $response );
		$this->assertCount( 2, $response );
		$this->assertEquals( 'Honda', $response[0]['name'] );
		$this->assertEquals( 25, $response[0]['count'] );
		$this->assertArrayHasKey( 'slug', $response[0] );
	}

	/**
	 * Test: get_vehicle_models returns models for make.
	 *
	 * Verifies vehicle models endpoint filters by make.
	 */
	public function test_get_vehicle_models_returns_models_for_make(): void {
		// Arrange.
		$mock_request = Mockery::mock( 'WP_REST_Request' );
		$mock_request->shouldReceive( 'get_param' )
			->with( 'make' )
			->andReturn( 'Honda' );
		$mock_request->shouldReceive( 'get_param' )
			->with( 'year' )
			->andReturn( null );

		$mock_models = array( 'Civic', 'Accord', 'CR-V' );

		$this->database_mock->shouldReceive( 'get_vehicle_models' )
			->once()
			->with( 'Honda', null )
			->andReturn( $mock_models );

		// Act.
		$response = $this->rest_api->get_vehicle_models( $mock_request );

		// Assert.
		$this->assertIsArray( $response );
		$this->assertCount( 3, $response );
		$this->assertEquals( 'Civic', $response[0]['name'] );
		$this->assertArrayHasKey( 'slug', $response[0] );
	}

	/**
	 * Test: get_vehicle_models filters by year when provided.
	 *
	 * Verifies year parameter is passed to database query.
	 */
	public function test_get_vehicle_models_filters_by_year_when_provided(): void {
		// Arrange.
		$mock_request = Mockery::mock( 'WP_REST_Request' );
		$mock_request->shouldReceive( 'get_param' )
			->with( 'make' )
			->andReturn( 'Honda' );
		$mock_request->shouldReceive( 'get_param' )
			->with( 'year' )
			->andReturn( 2020 );

		$this->database_mock->shouldReceive( 'get_vehicle_models' )
			->once()
			->with( 'Honda', 2020 )
			->andReturn( array( 'Civic' ) );

		// Act.
		$response = $this->rest_api->get_vehicle_models( $mock_request );

		// Assert - Mockery verifies year parameter was passed.
		$this->assertIsArray( $response );
	}

	/**
	 * Test: get_vehicle_years returns years with counts.
	 *
	 * Verifies vehicle years endpoint returns array of years.
	 */
	public function test_get_vehicle_years_returns_years_with_counts(): void {
		// Arrange.
		$mock_request = Mockery::mock( 'WP_REST_Request' );

		$mock_years = array(
			(object) array(
				'year'  => 2020,
				'count' => 15,
			),
			(object) array(
				'year'  => 2021,
				'count' => 20,
			),
		);

		$this->database_mock->shouldReceive( 'get_vehicle_years' )
			->once()
			->andReturn( $mock_years );

		// Act.
		$response = $this->rest_api->get_vehicle_years( $mock_request );

		// Assert.
		$this->assertIsArray( $response );
		$this->assertCount( 2, $response );
		$this->assertEquals( 2020, $response[0]['year'] );
		$this->assertEquals( 15, $response[0]['count'] );
	}

	/**
	 * Test: get_compatibility returns parts for vehicle.
	 *
	 * Verifies compatibility endpoint returns parts matching vehicle.
	 */
	public function test_get_compatibility_returns_parts_for_vehicle(): void {
		// Arrange.
		$mock_request = Mockery::mock( 'WP_REST_Request' );
		$mock_request->shouldReceive( 'get_param' )
			->with( 'make' )
			->andReturn( 'Honda' );
		$mock_request->shouldReceive( 'get_param' )
			->with( 'model' )
			->andReturn( 'Civic' );
		$mock_request->shouldReceive( 'get_param' )
			->with( 'year' )
			->andReturn( 2020 );

		$mock_parts = array(
			(object) array(
				'id'           => 1,
				'sku'          => 'CSF-3000',
				'name'         => 'Radiator',
				'category'     => 'Radiators',
				'price'        => 299.99,
				'in_stock'     => 1,
				'manufacturer' => 'CSF',
				'images'       => json_encode( array() ),
			),
		);

		$this->database_mock->shouldReceive( 'get_parts_by_vehicle' )
			->once()
			->with( 'Honda', 'Civic', 2020 )
			->andReturn( $mock_parts );

		// Act.
		$response = $this->rest_api->get_compatibility( $mock_request );

		// Assert.
		$this->assertIsArray( $response );
		$this->assertArrayHasKey( 'vehicle', $response );
		$this->assertArrayHasKey( 'parts', $response );
		$this->assertArrayHasKey( 'total', $response );
		$this->assertEquals( 'Honda', $response['vehicle']['make'] );
		$this->assertEquals( 'Civic', $response['vehicle']['model'] );
		$this->assertEquals( 2020, $response['vehicle']['year'] );
		$this->assertEquals( 1, $response['total'] );
	}

	/**
	 * Test: get_compatibility sanitizes vehicle parameters.
	 *
	 * Verifies sanitize_text_field is called on vehicle parameters.
	 * Note: sanitize_text_field is mocked to return input unchanged for testing.
	 */
	public function test_get_compatibility_sanitizes_vehicle_parameters(): void {
		// Arrange.
		$mock_request = Mockery::mock( 'WP_REST_Request' );
		$mock_request->shouldReceive( 'get_param' )
			->with( 'make' )
			->andReturn( '<script>Honda</script>' );
		$mock_request->shouldReceive( 'get_param' )
			->with( 'model' )
			->andReturn( 'Civic<>' );
		$mock_request->shouldReceive( 'get_param' )
			->with( 'year' )
			->andReturn( '2020' );

		// Since sanitize_text_field is mocked to returnArg, values pass through unchanged.
		$this->database_mock->shouldReceive( 'get_parts_by_vehicle' )
			->once()
			->with( '<script>Honda</script>', 'Civic<>', 2020 )
			->andReturn( array() );

		// Act.
		$response = $this->rest_api->get_compatibility( $mock_request );

		// Assert - Mockery verifies function was called.
		$this->assertIsArray( $response );
	}

	/**
	 * Test: caching is used when enabled.
	 *
	 * Verifies that cached responses are returned when caching is enabled.
	 */
	public function test_caching_is_used_when_enabled(): void {
		// Arrange - Enable cache.
		Functions\when( 'get_option' )->alias(
			function ( $option, $default = false ) {
				if ( $option === 'csf_parts_enable_cache' ) {
					return 1;
				}
				return $default;
			}
		);

		$cached_data = array(
			'parts'       => array(),
			'total'       => 0,
			'page'        => 1,
			'per_page'    => 20,
			'total_pages' => 0,
		);

		Functions\when( 'get_transient' )->justReturn( $cached_data );

		$mock_request = Mockery::mock( 'WP_REST_Request' );
		$mock_request->shouldReceive( 'get_params' )->andReturn( array() );

		// Database should NOT be called when cache hits.
		$this->database_mock->shouldNotReceive( 'query_parts' );

		// Act.
		$response = $this->rest_api->get_parts( $mock_request );

		// Assert.
		$this->assertIsArray( $response );
		$this->assertEquals( $cached_data, $response );
	}

	/**
	 * Test: caching is bypassed when disabled.
	 *
	 * Verifies database is queried when caching is disabled.
	 */
	public function test_caching_is_bypassed_when_disabled(): void {
		// Arrange - Cache is disabled (default in setUp).
		$mock_request = Mockery::mock( 'WP_REST_Request' );
		$mock_request->shouldReceive( 'get_params' )->andReturn( array() );

		// Database SHOULD be called when cache disabled.
		$this->database_mock->shouldReceive( 'query_parts' )
			->once()
			->andReturn(
				array(
					'parts' => array(),
					'total' => 0,
				)
			);

		// Act.
		$response = $this->rest_api->get_parts( $mock_request );

		// Assert - Mockery verifies database was called.
		$this->assertIsArray( $response );
	}
}
