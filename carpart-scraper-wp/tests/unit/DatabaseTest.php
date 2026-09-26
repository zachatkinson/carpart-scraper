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
		$wpdb_property->setValue( $this->database, $this->wpdb_mock );

		// Fix table_parts property to use mock prefix.
		$table_property = $reflection->getProperty( 'table_parts' );
		$table_property->setValue( $this->database, 'wp_csf_parts' );

		$changes_property = $reflection->getProperty( 'table_changes' );
		$changes_property->setValue( $this->database, 'wp_csf_part_changes' );
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
				Mockery::on(
					function ( array $row ) {
						return '2025-10-28 12:00:00' === $row['created_at']
							&& '2025-10-28 12:00:00' === $row['updated_at']
							&& 32 === strlen( $row['content_hash'] );
					}
				),
				Mockery::type( 'array' )
			)
			->andReturn( 1 );

		// The change log records the addition.
		$this->wpdb_mock->shouldReceive( 'insert' )
			->once()
			->with(
				'wp_csf_part_changes',
				Mockery::on(
					function ( array $row ) {
						return 'CSF-4000' === $row['sku'] && 'created' === $row['change_type'];
					}
				),
				Mockery::type( 'array' )
			)
			->andReturn( 1 );

		// Act.
		$result = $this->database->upsert_part( $part_data );

		// Assert.
		$this->assertEquals( 1, $result['id'] );
		$this->assertEquals( 'created', $result['status'] );
	}

	/**
	 * Test: upsert_part returns unchanged when data is identical.
	 *
	 * Verifies that no full update is issued when the incoming data
	 * matches the existing row, preserving the updated_at timestamp.
	 */
	public function test_upsert_part_returns_unchanged_when_data_identical(): void {
		// Arrange.
		$part_data = array(
			'sku'            => 'CSF-5000',
			'name'           => 'Test Radiator',
			'price'          => 199.99,
			'category'       => 'Radiators',
			'manufacturer'   => 'CSF',
			'in_stock'       => true,
			'description'    => 'Test description',
			'short_description' => '',
			'position'       => '',
			'tech_notes'     => '',
			'compatibility'  => array(),
			'specifications' => array(),
			'features'       => array(),
			'images'         => array(),
			'interchange_numbers' => array(),
			'scraped_at'     => '2025-01-01',
		);

		$existing = (object) array(
			'id'                  => 42,
			'sku'                 => 'CSF-5000',
			'name'                => 'Test Radiator',
			'price'               => '199.99',
			'category'            => 'Radiators',
			'manufacturer'        => 'CSF',
			'in_stock'            => 1,
			'description'         => 'Test description',
			'short_description'   => '',
			'position'            => '',
			'tech_notes'          => '',
			'compatibility'       => '[]',
			'specifications'      => '[]',
			'features'            => '[]',
			'images'              => '[]',
			'interchange_numbers' => '[]',
			'scraped_at'          => '2025-01-01',
		);

		Functions\when( 'current_time' )->justReturn( '2025-10-28 12:00:00' );

		// Mock get_part_by_sku returning existing part.
		$this->wpdb_mock->shouldReceive( 'prepare' )
			->once()
			->andReturn( 'SELECT * FROM wp_csf_parts WHERE sku = "CSF-5000"' );

		$this->wpdb_mock->shouldReceive( 'get_row' )
			->once()
			->andReturn( $existing );

		// Expect only the last_synced update query, NOT a full update.
		$this->wpdb_mock->shouldReceive( 'prepare' )
			->once()
			->withArgs( function ( $sql, ...$args ) {
				return strpos( $sql, 'last_synced' ) !== false
					&& strpos( $sql, 'updated_at = updated_at' ) !== false;
			} )
			->andReturn( 'UPDATE wp_csf_parts SET last_synced = ...' );

		$this->wpdb_mock->shouldReceive( 'query' )
			->once()
			->andReturn( 1 );

		// Should NOT receive a full update call.
		$this->wpdb_mock->shouldNotReceive( 'update' );

		// Act.
		$result = $this->database->upsert_part( $part_data );

		// Assert.
		$this->assertEquals( 42, $result['id'] );
		$this->assertEquals( 'unchanged', $result['status'] );
		$this->assertSame( array(), $result['changed_fields'] );
	}

	/**
	 * Test: upsert_part returns updated when data differs.
	 *
	 * Verifies that a full update is issued when part content has changed.
	 */
	public function test_upsert_part_returns_updated_when_data_differs(): void {
		// Arrange.
		$part_data = array(
			'sku'            => 'CSF-6000',
			'name'           => 'Updated Radiator Name',
			'price'          => 299.99,
			'category'       => 'Radiators',
			'manufacturer'   => 'CSF',
			'in_stock'       => true,
			'description'    => 'New description',
			'short_description' => '',
			'position'       => '',
			'tech_notes'     => '',
			'compatibility'  => array(),
			'specifications' => array(),
			'features'       => array(),
			'images'         => array(),
			'interchange_numbers' => array(),
			'scraped_at'     => '2025-01-01',
		);

		$existing = (object) array(
			'id'                  => 99,
			'sku'                 => 'CSF-6000',
			'name'                => 'Old Radiator Name',
			'price'               => '199.99',
			'category'            => 'Radiators',
			'manufacturer'        => 'CSF',
			'in_stock'            => 1,
			'description'         => 'Old description',
			'short_description'   => '',
			'position'            => '',
			'tech_notes'          => '',
			'compatibility'       => '[]',
			'specifications'      => '[]',
			'features'            => '[]',
			'images'              => '[]',
			'interchange_numbers' => '[]',
			'scraped_at'          => '2025-01-01',
		);

		Functions\when( 'current_time' )->justReturn( '2025-10-28 12:00:00' );

		// Mock get_part_by_sku returning existing part.
		$this->wpdb_mock->shouldReceive( 'prepare' )
			->once()
			->andReturn( 'SELECT * FROM wp_csf_parts WHERE sku = "CSF-6000"' );

		$this->wpdb_mock->shouldReceive( 'get_row' )
			->once()
			->andReturn( $existing );

		// Expect a full update call (data changed) that moves updated_at itself.
		$this->wpdb_mock->shouldReceive( 'update' )
			->once()
			->with(
				'wp_csf_parts',
				Mockery::on(
					function ( array $row ) {
						return '2025-10-28 12:00:00' === $row['updated_at']
							&& ! array_key_exists( 'created_at', $row )
							&& 32 === strlen( $row['content_hash'] );
					}
				),
				array( 'id' => 99 ),
				Mockery::type( 'array' ),
				array( '%d' )
			)
			->andReturn( 1 );

		// The change log records which fields moved.
		$this->wpdb_mock->shouldReceive( 'insert' )
			->once()
			->with(
				'wp_csf_part_changes',
				Mockery::on(
					function ( array $row ) {
						return 'updated' === $row['change_type']
							&& json_decode( $row['changed_fields'], true ) === array( 'name', 'description', 'price' );
					}
				),
				Mockery::type( 'array' )
			)
			->andReturn( 1 );

		// Act.
		$result = $this->database->upsert_part( $part_data );

		// Assert.
		$this->assertEquals( 99, $result['id'] );
		$this->assertEquals( 'updated', $result['status'] );
		$this->assertEqualsCanonicalizing(
			array( 'name', 'price', 'description' ),
			$result['changed_fields'],
			'Every differing content field is reported, not just the first'
		);
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

		$this->wpdb_mock->shouldReceive( 'insert' )
			->once()
			->with( 'wp_csf_part_changes', Mockery::type( 'array' ), Mockery::type( 'array' ) )
			->andReturn( 1 );

		// Act.
		$result = $this->database->upsert_part( $part_data );

		// Assert.
		$this->assertEquals( 1, $result['id'] );
		$this->assertEquals( 'created', $result['status'] );
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

	/**
	 * Compatibility rows are stored in make, model, year order whatever the scraper emitted.
	 */
	public function test_sort_compatibility_orders_by_make_model_year(): void {
		// Arrange
		$rows = array(
			array( 'make' => 'Gmc', 'model' => 'Canyon', 'year' => 2006 ),
			array( 'make' => 'Chevrolet', 'model' => 'Colorado', 'year' => 2005 ),
			array( 'make' => 'chevrolet', 'model' => 'Colorado', 'year' => 2004 ),
			array( 'make' => 'Chevrolet', 'model' => 'Silverado 1500', 'year' => 2004 ),
			array( 'make' => 'Chevrolet', 'model' => 'Silverado 2500', 'year' => 2004 ),
		);

		// Act
		$sorted = CSF_Parts_Database::sort_compatibility( $rows );

		// Assert
		$this->assertSame(
			array( 'chevrolet|Colorado|2004', 'Chevrolet|Colorado|2005', 'Chevrolet|Silverado 1500|2004', 'Chevrolet|Silverado 2500|2004', 'Gmc|Canyon|2006' ),
			array_map( static fn( array $r ): string => $r['make'] . '|' . $r['model'] . '|' . $r['year'], $sorted )
		);
	}

	/**
	 * A stored row for hash/diff tests: identical content to incoming_data(), in storage form.
	 *
	 * @param array $overrides Column overrides.
	 * @return object
	 */
	private function stored_row( array $overrides = array() ): object {
		return (object) array_merge(
			array(
				'id'                  => 7,
				'sku'                 => 'CSF-7000',
				'name'                => 'Radiator',
				'price'               => '199.990000',
				'category'            => 'Radiators',
				'manufacturer'        => 'CSF',
				'in_stock'            => 1,
				'description'         => 'Desc',
				'short_description'   => '',
				'position'            => '',
				'tech_notes'          => '',
				'compatibility'       => '[{"year":2020,"make":"Honda","model":"Civic"}]',
				'specifications'      => '{"Rows":"2"}',
				'features'            => '[]',
				'images'              => '[]',
				'interchange_numbers' => '[]',
				'scraped_at'          => '2025-01-01T00:00:00',
				'content_hash'        => null,
				'updated_at'          => '2025-01-01 00:00:00',
			),
			$overrides
		);
	}

	/**
	 * Incoming part data whose storage form equals stored_row().
	 *
	 * @param array $overrides Field overrides.
	 * @return array
	 */
	private function incoming_data( array $overrides = array() ): array {
		return array_merge(
			array(
				'sku'                 => 'CSF-7000',
				'name'                => 'Radiator',
				'price'               => 199.99,
				'category'            => 'Radiators',
				'manufacturer'        => 'CSF',
				'in_stock'            => true,
				'description'         => 'Desc',
				'compatibility'       => array( array( 'year' => 2020, 'make' => 'Honda', 'model' => 'Civic' ) ),
				'specifications'      => array( 'Rows' => '2' ),
				'features'            => array(),
				'images'              => array(),
				'interchange_numbers' => array(),
				'scraped_at'          => '2025-09-25T03:30:00',
			),
			$overrides
		);
	}

	/**
	 * Test: a newer scraped_at alone never counts as a change.
	 */
	public function test_upsert_part_ignores_scraped_at_when_content_identical(): void {
		// Arrange.
		Functions\when( 'current_time' )->justReturn( '2025-10-28 12:00:00' );
		$this->wpdb_mock->shouldReceive( 'prepare' )->once()->andReturn( 'SELECT ...' );
		$this->wpdb_mock->shouldReceive( 'get_row' )->once()->andReturn( $this->stored_row() );
		$this->wpdb_mock->shouldReceive( 'prepare' )
			->once()
			->withArgs(
				function ( $sql, ...$args ) {
					return strpos( $sql, 'content_hash = %s' ) !== false
						&& strpos( $sql, 'updated_at = updated_at' ) !== false
						&& '2025-09-25T03:30:00' === $args[1];
				}
			)
			->andReturn( 'UPDATE ...' );
		$this->wpdb_mock->shouldReceive( 'query' )->once()->andReturn( 1 );
		$this->wpdb_mock->shouldNotReceive( 'update' );
		$this->wpdb_mock->shouldNotReceive( 'insert' );

		// Act.
		$result = $this->database->upsert_part( $this->incoming_data() );

		// Assert.
		$this->assertSame( 'unchanged', $result['status'] );
	}

	/**
	 * Test: a matching stored hash short-circuits the field comparison.
	 */
	public function test_upsert_part_trusts_matching_content_hash(): void {
		// Arrange: stored fields deliberately stale, hash current — the hash wins.
		$hash   = CSF_Parts_Database::content_hash( CSF_Parts_Database::content_data( $this->incoming_data() ) );
		$stored = $this->stored_row( array( 'name' => 'Stale name', 'content_hash' => $hash ) );

		Functions\when( 'current_time' )->justReturn( '2025-10-28 12:00:00' );
		$this->wpdb_mock->shouldReceive( 'prepare' )->once()->andReturn( 'SELECT ...' );
		$this->wpdb_mock->shouldReceive( 'get_row' )->once()->andReturn( $stored );
		$this->wpdb_mock->shouldReceive( 'prepare' )->once()->andReturn( 'UPDATE ...' );
		$this->wpdb_mock->shouldReceive( 'query' )->once()->andReturn( 1 );
		$this->wpdb_mock->shouldNotReceive( 'update' );

		// Act.
		$result = $this->database->upsert_part( $this->incoming_data() );

		// Assert.
		$this->assertSame( 'unchanged', $result['status'] );
	}

	/**
	 * Test: hash and field diff agree on what counts as a change.
	 */
	public function test_content_hash_matches_diff_content_semantics(): void {
		// Arrange.
		$base    = CSF_Parts_Database::content_data( $this->incoming_data() );
		$same    = CSF_Parts_Database::content_data( $this->incoming_data( array( 'price' => '199.990', 'scraped_at' => 'later' ) ) );
		$changed = CSF_Parts_Database::content_data( $this->incoming_data( array( 'price' => 209.99, 'images' => array( array( 'url' => 'images/a.avif' ) ) ) ) );

		// Act & Assert.
		$this->assertSame( CSF_Parts_Database::content_hash( $base ), CSF_Parts_Database::content_hash( $same ) );
		$this->assertNotSame( CSF_Parts_Database::content_hash( $base ), CSF_Parts_Database::content_hash( $changed ) );
		$this->assertSame( array(), CSF_Parts_Database::diff_content( $this->stored_row(), $same ) );
		$this->assertSame( array( 'price', 'images' ), CSF_Parts_Database::diff_content( $this->stored_row(), $changed ) );
	}

	/**
	 * Test: compatibility row order does not affect the hash or the diff.
	 */
	public function test_content_hash_is_order_independent_for_compatibility(): void {
		// Arrange.
		$rows     = array(
			array( 'year' => 2021, 'make' => 'Toyota', 'model' => 'Camry' ),
			array( 'year' => 2020, 'make' => 'Honda', 'model' => 'Civic' ),
		);
		$forward  = CSF_Parts_Database::content_data( $this->incoming_data( array( 'compatibility' => $rows ) ) );
		$backward = CSF_Parts_Database::content_data( $this->incoming_data( array( 'compatibility' => array_reverse( $rows ) ) ) );

		// Act & Assert.
		$this->assertSame( $forward['compatibility'], $backward['compatibility'] );
		$this->assertSame( CSF_Parts_Database::content_hash( $forward ), CSF_Parts_Database::content_hash( $backward ) );
	}

	/**
	 * Test: recent changes come back newest first with decoded field lists.
	 */
	public function test_get_recent_changes_decodes_fields(): void {
		// Arrange.
		$this->wpdb_mock->shouldReceive( 'prepare' )
			->once()
			->withArgs(
				function ( $sql, $limit ) {
					return strpos( $sql, 'wp_csf_part_changes' ) !== false
						&& strpos( $sql, 'ORDER BY observed_at DESC' ) !== false
						&& 20 === $limit;
				}
			)
			->andReturn( 'SELECT ...' );
		$this->wpdb_mock->shouldReceive( 'get_results' )
			->once()
			->andReturn(
				array(
					(object) array( 'sku' => 'CSF-1', 'change_type' => 'updated', 'changed_fields' => '["compatibility"]', 'observed_at' => '2025-10-28 03:38:00' ),
					(object) array( 'sku' => 'CSF-2', 'change_type' => 'created', 'changed_fields' => 'not json', 'observed_at' => '2025-10-27 03:38:00' ),
				)
			);

		// Act.
		$changes = $this->database->get_recent_changes();

		// Assert.
		$this->assertCount( 2, $changes );
		$this->assertSame( array( 'compatibility' ), $changes[0]->changed_fields );
		$this->assertSame( array(), $changes[1]->changed_fields );
	}

	/**
	 * Test: discontinued parts leave the catalog unless explicitly included.
	 */
	public function test_query_parts_excludes_discontinued_unless_asked(): void {
		// Arrange.
		$seen = array();
		$this->wpdb_mock->shouldReceive( 'prepare' )
			->andReturnUsing(
				function ( $sql ) use ( &$seen ) {
					$seen[] = $sql;
					return $sql;
				}
			);
		$this->wpdb_mock->shouldReceive( 'get_var' )->andReturn( '0' );
		$this->wpdb_mock->shouldReceive( 'get_results' )->andReturn( array() );

		// Act.
		$this->database->query_parts( array() );
		$default_sql = implode( "\n", $seen );
		$seen        = array();
		$this->database->query_parts( array( 'include_discontinued' => true ) );
		$inclusive_sql = implode( "\n", $seen );

		// Assert.
		$this->assertStringContainsString( 'p.discontinued = 0', $default_sql );
		$this->assertStringNotContainsString( 'p.discontinued = 0', $inclusive_sql );
	}

	/**
	 * Test: a part CSF dropped is recorded as a discontinued change, and only that.
	 */
	public function test_upsert_part_records_discontinued_as_the_changed_field(): void {
		// Arrange: stored row predates the column entirely.
		Functions\when( 'current_time' )->justReturn( '2025-10-28 12:00:00' );
		$this->wpdb_mock->shouldReceive( 'prepare' )->once()->andReturn( 'SELECT ...' );
		$this->wpdb_mock->shouldReceive( 'get_row' )->once()->andReturn( $this->stored_row() );
		$this->wpdb_mock->shouldReceive( 'update' )
			->once()
			->with(
				'wp_csf_parts',
				Mockery::on(
					function ( array $row ) {
						return 1 === $row['discontinued'];
					}
				),
				array( 'id' => 7 ),
				Mockery::type( 'array' ),
				array( '%d' )
			)
			->andReturn( 1 );
		$this->wpdb_mock->shouldReceive( 'insert' )
			->once()
			->with( 'wp_csf_part_changes', Mockery::type( 'array' ), Mockery::type( 'array' ) )
			->andReturn( 1 );

		// Act.
		$result = $this->database->upsert_part( $this->incoming_data( array( 'discontinued' => true ) ) );

		// Assert.
		$this->assertSame( 'updated', $result['status'] );
		$this->assertSame( array( 'discontinued' ), $result['changed_fields'] );
	}
}
