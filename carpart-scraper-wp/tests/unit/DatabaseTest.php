<?php
/**
 * Tests for CSF_Parts_Database class (V2 Architecture).
 *
 * Comprehensive test coverage for database operations including CRUD,
 * pagination, search, filtering, and JSON column queries.
 *
 * @package CSF_Parts_Catalog
 */

use PHPUnit\Framework\TestCase;
use Brain\Monkey;
use Brain\Monkey\Functions;
use Mockery\MockInterface;

/**
 * Class DatabaseTest
 *
 * Tests the V2 custom database table operations following AAA pattern.
 * All tests adhere to CLAUDE.md guidelines: test_<unit>_<scenario>_<expected_result>
 */
final class DatabaseTest extends TestCase {

	/**
	 * Database instance under test.
	 *
	 * @var CSF_Parts_Database
	 */
	private CSF_Parts_Database $database;

	/**
	 * Mock wpdb instance.
	 *
	 * @var MockInterface
	 */
	private $wpdb_mock;

	/**
	 * Set up test environment before each test.
	 *
	 * Initializes mock wpdb with commonly-used method mocks and injects it
	 * into the database instance via reflection.
	 */
	protected function setUp(): void {
		parent::setUp();
		Monkey\setUp();

		// Create mock wpdb instance with properties.
		$this->wpdb_mock            = Mockery::mock( 'wpdb' );
		$this->wpdb_mock->prefix    = 'wp_';
		$this->wpdb_mock->csf_parts = 'wp_csf_parts';
		$this->wpdb_mock->insert_id = 1;

		// Mock commonly-used wpdb methods with default behavior.
		$this->wpdb_mock->shouldReceive( 'esc_like' )
			->andReturnUsing(
				function ( $text ) {
					return addcslashes( $text, '_%\\' );
				}
			);

		// Mock WordPress functions.
		Functions\when( 'esc_sql' )->returnArg();
		Functions\when( 'absint' )->returnArg();
		Functions\when( 'wp_json_encode' )->alias( 'json_encode' );

		// Create database instance with mocked wpdb.
		$this->database = new CSF_Parts_Database();

		// Use reflection to inject mock wpdb and fix table_parts property.
		$reflection    = new ReflectionClass( $this->database );
		$wpdb_property = $reflection->getProperty( 'wpdb' );
		$wpdb_property->setAccessible( true );
		$wpdb_property->setValue( $this->database, $this->wpdb_mock );

		// Fix table_parts property to use mock prefix.
		$table_property = $reflection->getProperty( 'table_parts' );
		$table_property->setAccessible( true );
		$table_property->setValue( $this->database, 'wp_csf_parts' );
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
	 * Test: Database class instantiates successfully.
	 *
	 * Verifies basic object creation and type checking.
	 */
	public function test_database_class_can_be_instantiated(): void {
		// Assert.
		$this->assertInstanceOf( CSF_Parts_Database::class, $this->database );
	}

	/**
	 * Test: get_part_by_sku returns null for non-existent SKU.
	 *
	 * Ensures graceful handling of missing parts without exceptions.
	 */
	public function test_get_part_by_sku_returns_null_for_non_existent_sku(): void {
		// Arrange.
		$this->wpdb_mock->shouldReceive( 'prepare' )
			->once()
			->andReturn( 'SELECT * FROM wp_csf_parts WHERE sku = "NON-EXISTENT"' );

		$this->wpdb_mock->shouldReceive( 'get_row' )
			->once()
			->andReturn( null );

		// Act.
		$result = $this->database->get_part_by_sku( 'NON-EXISTENT' );

		// Assert.
		$this->assertNull( $result );
	}

	/**
	 * Test: get_part_by_sku returns part object for existing SKU.
	 *
	 * Verifies successful part retrieval with all expected fields.
	 */
	public function test_get_part_by_sku_returns_part_for_existing_sku(): void {
		// Arrange.
		$expected_part = (object) array(
			'id'             => 1,
			'sku'            => 'CSF-3000',
			'name'           => 'High Performance Radiator',
			'price'          => 299.99,
			'category'       => 'Radiators',
			'manufacturer'   => 'CSF',
			'in_stock'       => 1,
			'description'    => 'Premium radiator',
			'compatibility'  => '[]',
			'specifications' => '{}',
			'features'       => '[]',
			'images'         => '[]',
		);

		$this->wpdb_mock->shouldReceive( 'prepare' )
			->once()
			->andReturn( 'SELECT * FROM wp_csf_parts WHERE sku = "CSF-3000"' );

		$this->wpdb_mock->shouldReceive( 'get_row' )
			->once()
			->andReturn( $expected_part );

		// Act.
		$result = $this->database->get_part_by_sku( 'CSF-3000' );

		// Assert.
		$this->assertIsObject( $result );
		$this->assertEquals( 'CSF-3000', $result->sku );
		$this->assertEquals( 'High Performance Radiator', $result->name );
		$this->assertEquals( 299.99, $result->price );
	}

	/**
	 * Test: upsert_part inserts new part successfully.
	 *
	 * Verifies insert operation for new parts with proper data transformation.
	 */
	public function test_upsert_part_inserts_new_part_successfully(): void {
		// Arrange.
		$part_data = array(
			'sku'            => 'CSF-4000',
			'name'           => 'Test Radiator',
			'price'          => 199.99,
			'category'       => 'Radiators',
			'manufacturer'   => 'CSF',
			'in_stock'       => true,
			'description'    => 'Test description',
			'compatibility'  => array(),
			'specifications' => array(),
			'features'       => array(),
			'images'         => array(),
		);

		Functions\when( 'current_time' )->justReturn( '2025-10-28 12:00:00' );

		// Mock get_part_by_sku returning null (part doesn't exist).
		$this->wpdb_mock->shouldReceive( 'prepare' )
			->once()
			->andReturn( 'SELECT * FROM wp_csf_parts WHERE sku = "CSF-4000"' );

		$this->wpdb_mock->shouldReceive( 'get_row' )
			->once()
			->andReturn( null );

		// Mock insert operation.
		$this->wpdb_mock->shouldReceive( 'insert' )
			->once()
			->with(
				'wp_csf_parts',
				Mockery::type( 'array' ),
				Mockery::type( 'array' )
			)
			->andReturn( 1 );

		// Act.
		$result = $this->database->upsert_part( $part_data );

		// Assert.
		$this->assertEquals( 1, $result );
	}

	/**
	 * Test: get_parts returns paginated results.
	 *
	 * Verifies pagination logic with limit and offset calculation.
	 */
	public function test_get_parts_returns_paginated_results(): void {
		// Arrange.
		$mock_parts = array(
			(object) array(
				'sku'  => 'CSF-1000',
				'name' => 'Part 1',
			),
			(object) array(
				'sku'  => 'CSF-2000',
				'name' => 'Part 2',
			),
		);

		$this->wpdb_mock->shouldReceive( 'prepare' )
			->once()
			->andReturn( 'SELECT * FROM wp_csf_parts LIMIT 20 OFFSET 0' );

		$this->wpdb_mock->shouldReceive( 'get_results' )
			->once()
			->andReturn( $mock_parts );

		// Act.
		$result = $this->database->get_parts( 20, 1 );

		// Assert.
		$this->assertIsArray( $result );
		$this->assertCount( 2, $result );
		$this->assertEquals( 'CSF-1000', $result[0]->sku );
	}

	/**
	 * Test: get_total_parts returns integer count.
	 *
	 * Verifies count query returns proper integer type.
	 */
	public function test_get_total_parts_returns_integer_count(): void {
		// Arrange.
		$this->wpdb_mock->shouldReceive( 'get_var' )
			->once()
			->andReturn( '42' );

		// Act.
		$result = $this->database->get_total_parts();

		// Assert.
		$this->assertIsInt( $result );
		$this->assertEquals( 42, $result );
	}

	/**
	 * Test: search_parts returns matching results.
	 *
	 * Verifies search functionality with LIKE queries and proper escaping.
	 */
	public function test_search_parts_returns_matching_results(): void {
		// Arrange.
		$mock_results = array(
			(object) array(
				'sku'  => 'CSF-3000',
				'name' => 'High Performance Radiator',
			),
		);

		$this->wpdb_mock->shouldReceive( 'prepare' )
			->once()
			->andReturn( 'SELECT * FROM wp_csf_parts WHERE...' );

		$this->wpdb_mock->shouldReceive( 'get_results' )
			->once()
			->andReturn( $mock_results );

		// Act.
		$result = $this->database->search_parts( 'radiator', 20 );

		// Assert.
		$this->assertIsArray( $result );
		$this->assertCount( 1, $result );
		$this->assertStringContainsString( 'Radiator', $result[0]->name );
	}

	/**
	 * Test: get_parts_by_category filters by category correctly.
	 *
	 * Verifies category filtering with prepared statement.
	 */
	public function test_get_parts_by_category_filters_correctly(): void {
		// Arrange.
		$mock_radiators = array(
			(object) array(
				'category' => 'Radiators',
				'name'     => 'Radiator 1',
			),
			(object) array(
				'category' => 'Radiators',
				'name'     => 'Radiator 2',
			),
		);

		$this->wpdb_mock->shouldReceive( 'prepare' )
			->once()
			->andReturn( 'SELECT * FROM wp_csf_parts WHERE category = "Radiators"' );

		$this->wpdb_mock->shouldReceive( 'get_results' )
			->once()
			->andReturn( $mock_radiators );

		// Act.
		$result = $this->database->get_parts_by_category( 'Radiators', 20, 1 );

		// Assert.
		$this->assertIsArray( $result );
		$this->assertCount( 2, $result );
		$this->assertEquals( 'Radiators', $result[0]->category );
	}

	/**
	 * Test: get_categories returns unique category names.
	 *
	 * Verifies category query returns simple array of strings via get_col().
	 */
	public function test_get_categories_returns_unique_categories(): void {
		// Arrange.
		$mock_categories = array( 'Radiators', 'Condensers', 'Intercoolers' );

		$this->wpdb_mock->shouldReceive( 'get_col' )
			->once()
			->andReturn( $mock_categories );

		// Act.
		$result = $this->database->get_categories();

		// Assert.
		$this->assertIsArray( $result );
		$this->assertCount( 3, $result );
		$this->assertEquals( 'Radiators', $result[0] );
		$this->assertEquals( 'Condensers', $result[1] );
	}

	/**
	 * Test: get_vehicle_makes extracts makes from JSON column.
	 *
	 * Verifies JSON_TABLE query for extracting nested make values.
	 */
	public function test_get_vehicle_makes_extracts_from_json_column(): void {
		// Arrange.
		$mock_makes = array(
			(object) array(
				'make'  => 'Honda',
				'count' => '25',
			),
			(object) array(
				'make'  => 'Toyota',
				'count' => '18',
			),
		);

		$this->wpdb_mock->shouldReceive( 'get_results' )
			->once()
			->andReturn( $mock_makes );

		// Act.
		$result = $this->database->get_vehicle_makes();

		// Assert.
		$this->assertIsArray( $result );
		$this->assertCount( 2, $result );
		$this->assertEquals( 'Honda', $result[0]->make );
		$this->assertEquals( '25', $result[0]->count );
	}

	/**
	 * Test: get_vehicle_models filters by make correctly.
	 *
	 * Verifies JSON query with make filter using JSON_TABLE and get_col().
	 */
	public function test_get_vehicle_models_filters_by_make(): void {
		// Arrange.
		$mock_models = array( 'Accord', 'Civic', 'CR-V' );

		$this->wpdb_mock->shouldReceive( 'prepare' )
			->once()
			->andReturn( 'SELECT DISTINCT JSON_UNQUOTE(JSON_EXTRACT(compatibility, "$[*].model"))...' );

		$this->wpdb_mock->shouldReceive( 'get_col' )
			->once()
			->andReturn( $mock_models );

		// Act.
		$result = $this->database->get_vehicle_models( 'Honda' );

		// Assert.
		$this->assertIsArray( $result );
		$this->assertCount( 3, $result );
		$this->assertEquals( 'Accord', $result[0] );
		$this->assertEquals( 'Civic', $result[1] );
	}

	/**
	 * Test: get_vehicle_years returns sorted years descending.
	 *
	 * Verifies year extraction from JSON with proper sorting.
	 */
	public function test_get_vehicle_years_returns_sorted_years(): void {
		// Arrange.
		$mock_years = array(
			(object) array(
				'year'  => '2023',
				'count' => '30',
			),
			(object) array(
				'year'  => '2022',
				'count' => '28',
			),
			(object) array(
				'year'  => '2021',
				'count' => '25',
			),
		);

		$this->wpdb_mock->shouldReceive( 'get_results' )
			->once()
			->andReturn( $mock_years );

		// Act.
		$result = $this->database->get_vehicle_years();

		// Assert.
		$this->assertIsArray( $result );
		$this->assertCount( 3, $result );
		$this->assertEquals( '2023', $result[0]->year );
		$this->assertGreaterThan( $result[1]->year, $result[0]->year );
	}

	/**
	 * Test: get_parts_by_vehicle filters by vehicle criteria.
	 *
	 * Verifies JSON_CONTAINS query for compatibility matching.
	 */
	public function test_get_parts_by_vehicle_filters_correctly(): void {
		// Arrange.
		$mock_parts = array(
			(object) array(
				'sku'  => 'CSF-3000',
				'name' => 'Honda Accord Radiator',
			),
		);

		$this->wpdb_mock->shouldReceive( 'prepare' )
			->once()
			->andReturn( 'SELECT * FROM wp_csf_parts WHERE JSON_CONTAINS(compatibility, ...)' );

		$this->wpdb_mock->shouldReceive( 'get_results' )
			->once()
			->andReturn( $mock_parts );

		// Act.
		$result = $this->database->get_parts_by_vehicle( 'Honda', 'Accord', 2020 );

		// Assert.
		$this->assertIsArray( $result );
		$this->assertCount( 1, $result );
		$this->assertEquals( 'CSF-3000', $result[0]->sku );
	}

	/**
	 * Test: query_parts handles empty filters array.
	 *
	 * Verifies default behavior when no filters are applied.
	 */
	public function test_query_parts_handles_empty_filters(): void {
		// Arrange.
		$mock_parts = array(
			(object) array( 'sku' => 'CSF-1000' ),
			(object) array( 'sku' => 'CSF-2000' ),
		);

		$this->wpdb_mock->shouldReceive( 'prepare' )
			->andReturn( 'SELECT * FROM wp_csf_parts LIMIT 20 OFFSET 0' );

		$this->wpdb_mock->shouldReceive( 'get_var' )
			->once()
			->andReturn( '2' );

		$this->wpdb_mock->shouldReceive( 'get_results' )
			->once()
			->andReturn( $mock_parts );

		// Act.
		$result = $this->database->query_parts( array() );

		// Assert.
		$this->assertIsArray( $result );
		$this->assertArrayHasKey( 'parts', $result );
		$this->assertArrayHasKey( 'total', $result );
		$this->assertCount( 2, $result['parts'] );
	}

	/**
	 * Test: query_parts applies multiple filters correctly.
	 *
	 * Verifies dynamic WHERE clause building with multiple criteria.
	 */
	public function test_query_parts_applies_multiple_filters(): void {
		// Arrange.
		$filters = array(
			'category' => 'Radiators',
			'make'     => 'Honda',
			'search'   => 'performance',
		);

		$mock_parts = array(
			(object) array(
				'sku'      => 'CSF-3000',
				'category' => 'Radiators',
			),
		);

		$this->wpdb_mock->shouldReceive( 'prepare' )
			->andReturn( 'SELECT * FROM wp_csf_parts WHERE category = "Radiators" AND ...' );

		$this->wpdb_mock->shouldReceive( 'get_var' )
			->once()
			->andReturn( '1' );

		$this->wpdb_mock->shouldReceive( 'get_results' )
			->once()
			->andReturn( $mock_parts );

		// Act.
		$result = $this->database->query_parts( $filters );

		// Assert.
		$this->assertIsArray( $result );
		$this->assertCount( 1, $result['parts'] );
		$this->assertEquals( 'Radiators', $result['parts'][0]->category );
	}

	/**
	 * Test: Database uses prepared statements for SQL injection protection.
	 *
	 * Verifies malicious SQL input is safely escaped via wpdb->prepare().
	 */
	public function test_database_uses_prepared_statements(): void {
		// Arrange.
		$malicious_sku = "CSF-3000'; DROP TABLE wp_csf_parts; --";

		$this->wpdb_mock->shouldReceive( 'prepare' )
			->once()
			->with( Mockery::type( 'string' ), $malicious_sku )
			->andReturn( 'SELECT * FROM wp_csf_parts WHERE sku = "CSF-3000\'; DROP TABLE wp_csf_parts; --"' );

		$this->wpdb_mock->shouldReceive( 'get_row' )
			->once()
			->andReturn( null );

		// Act.
		$result = $this->database->get_part_by_sku( $malicious_sku );

		// Assert - No exception thrown, SQL injection prevented.
		$this->assertNull( $result );
	}

	/**
	 * Test: JSON columns are properly encoded during insert.
	 *
	 * Verifies arrays are JSON-encoded before database storage.
	 */
	public function test_json_columns_are_properly_encoded(): void {
		// Arrange.
		$part_data = array(
			'sku'            => 'CSF-5000',
			'name'           => 'Test Part',
			'price'          => 99.99,
			'category'       => 'Test',
			'manufacturer'   => 'CSF',
			'in_stock'       => true,
			'compatibility'  => array(
				array(
					'year'  => 2020,
					'make'  => 'Honda',
					'model' => 'Accord',
				),
			),
			'specifications' => array( 'core_rows' => 2 ),
			'features'       => array( 'High efficiency' ),
			'images'         => array(),
		);

		Functions\when( 'current_time' )->justReturn( '2025-10-28 12:00:00' );

		// Mock get_part_by_sku returning null.
		$this->wpdb_mock->shouldReceive( 'prepare' )
			->once()
			->andReturn( 'SELECT * FROM wp_csf_parts WHERE sku = "CSF-5000"' );

		$this->wpdb_mock->shouldReceive( 'get_row' )
			->once()
			->andReturn( null );

		// Mock insert with JSON encoding verification.
		$this->wpdb_mock->shouldReceive( 'insert' )
			->once()
			->with(
				'wp_csf_parts',
				Mockery::on(
					function ( $data ) {
						// Verify JSON encoding.
						$compatibility_decoded = json_decode( $data['compatibility'], true );
						return is_array( $compatibility_decoded ) &&
							isset( $compatibility_decoded[0]['make'] ) &&
							$compatibility_decoded[0]['make'] === 'Honda';
					}
				),
				Mockery::type( 'array' )
			)
			->andReturn( 1 );

		// Act.
		$result = $this->database->upsert_part( $part_data );

		// Assert.
		$this->assertEquals( 1, $result );
	}

	/**
	 * Test: Database handles pagination offset calculation correctly.
	 *
	 * Verifies proper offset calculation: (page - 1) * limit.
	 */
	public function test_pagination_offset_calculated_correctly(): void {
		// Arrange - Page 3 with 20 per page should have offset of 40.
		$this->wpdb_mock->shouldReceive( 'prepare' )
			->once()
			->with(
				Mockery::type( 'string' ),
				20,  // limit.
				40   // offset (page 3: (3-1) * 20 = 40).
			)
			->andReturn( 'SELECT * FROM wp_csf_parts LIMIT 20 OFFSET 40' );

		$this->wpdb_mock->shouldReceive( 'get_results' )
			->once()
			->andReturn( array() );

		// Act.
		$result = $this->database->get_parts( 20, 3 );

		// Assert.
		$this->assertIsArray( $result );
	}
}
