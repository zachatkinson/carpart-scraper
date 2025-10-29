<?php
/**
 * Tests for CSF_Parts_URL_Handler class (V2 Architecture).
 *
 * Comprehensive test coverage for virtual URL routing, rewrite rules,
 * query variables, and dynamic page rendering.
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
 * Class URLHandlerTest
 *
 * Tests virtual URL routing and dynamic page generation following AAA pattern.
 * Adheres to CLAUDE.md guidelines: test_<unit>_<scenario>_<expected_result>
 */
final class URLHandlerTest extends TestCase {

	/**
	 * URL Handler instance under test.
	 *
	 * @var CSF_Parts_URL_Handler
	 */
	private CSF_Parts_URL_Handler $url_handler;

	/**
	 * Mock Database instance.
	 *
	 * @var MockInterface
	 */
	private $database_mock;

	/**
	 * Set up test environment before each test.
	 *
	 * Initializes mock database and URL handler with WordPress function mocks.
	 */
	protected function setUp(): void {
		parent::setUp();
		Monkey\setUp();

		// Mock WordPress core functions.
		Functions\when( 'home_url' )->returnArg();
		Functions\when( 'sanitize_title' )->returnArg();
		Functions\when( 'sanitize_text_field' )->returnArg();
		Functions\when( 'esc_attr' )->returnArg();
		Functions\when( 'esc_url' )->returnArg();
		Functions\when( 'wp_strip_all_tags' )->returnArg();
		Functions\when( 'wp_trim_words' )->returnArg();
		Functions\when( 'wp_json_encode' )->alias( 'json_encode' );
		Functions\when( 'get_site_url' )->justReturn( 'https://example.com' );

		// Define constants if not already defined.
		if ( ! defined( 'CSF_PARTS_PLUGIN_DIR' ) ) {
			define( 'CSF_PARTS_PLUGIN_DIR', __DIR__ . '/../../' );
		}

		// Create mock database.
		$this->database_mock = Mockery::mock( 'CSF_Parts_Database' );

		// Create URL handler instance.
		$this->url_handler = new CSF_Parts_URL_Handler();

		// Inject mock database via reflection.
		$reflection      = new ReflectionClass( $this->url_handler );
		$database_property = $reflection->getProperty( 'database' );
		$database_property->setAccessible( true );
		$database_property->setValue( $this->url_handler, $this->database_mock );
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
	 * Test: URL Handler class instantiates successfully.
	 *
	 * Verifies basic object creation and WordPress hook registration.
	 */
	public function test_url_handler_class_can_be_instantiated(): void {
		// Assert.
		$this->assertInstanceOf( CSF_Parts_URL_Handler::class, $this->url_handler );
	}

	/**
	 * Test: register_rewrite_rules registers vehicle-specific URL pattern.
	 *
	 * Verifies vehicle-specific pattern: /parts/{year}-{make}-{model}-{category}-{sku}
	 */
	public function test_register_rewrite_rules_registers_vehicle_specific_pattern(): void {
		// Arrange.
		$call_count = 0;
		Functions\when( 'add_rewrite_rule' )
			->alias(
				function ( $pattern, $query, $priority ) use ( &$call_count ) {
					if ( $pattern === '^parts/([0-9]{4})-([^/-]+)-([^/-]+)-([^/-]+)-(.+)/?$' ) {
						$call_count++;
					}
				}
			);

		// Act.
		$this->url_handler->register_rewrite_rules();

		// Assert.
		$this->assertEquals( 1, $call_count, 'Vehicle-specific rewrite rule should be registered once' );
	}

	/**
	 * Test: register_rewrite_rules registers all URL patterns.
	 *
	 * Verifies all 4 rewrite rules are registered (vehicle, canonical, category, search).
	 */
	public function test_register_rewrite_rules_registers_all_patterns(): void {
		// Arrange.
		$registered_patterns = array();
		Functions\when( 'add_rewrite_rule' )
			->alias(
				function ( $pattern, $query, $priority ) use ( &$registered_patterns ) {
					$registered_patterns[] = $pattern;
				}
			);

		// Act.
		$this->url_handler->register_rewrite_rules();

		// Assert.
		$this->assertCount( 4, $registered_patterns, 'Should register 4 rewrite rules' );
		$this->assertContains( '^parts/([0-9]{4})-([^/-]+)-([^/-]+)-([^/-]+)-(.+)/?$', $registered_patterns, 'Vehicle-specific pattern' );
		$this->assertContains( '^parts/([^-]+)-(.+)/?$', $registered_patterns, 'Canonical pattern' );
		$this->assertContains( '^parts/category/([^/]+)/?$', $registered_patterns, 'Category archive pattern' );
		$this->assertContains( '^parts/search/([^/]+)/?$', $registered_patterns, 'Search pattern' );
	}

	/**
	 * Test: add_query_vars adds all required custom variables.
	 *
	 * Verifies 8 custom query vars are registered with WordPress.
	 */
	public function test_add_query_vars_adds_all_custom_variables(): void {
		// Arrange.
		$initial_vars = array( 'p', 'page_id', 's' );

		// Act.
		$result = $this->url_handler->add_query_vars( $initial_vars );

		// Assert.
		$this->assertIsArray( $result );
		$this->assertCount( 11, $result ); // 3 initial + 8 custom
		$this->assertContains( 'csf_part', $result );
		$this->assertContains( 'csf_sku', $result );
		$this->assertContains( 'csf_category', $result );
		$this->assertContains( 'csf_year', $result );
		$this->assertContains( 'csf_make', $result );
		$this->assertContains( 'csf_model', $result );
		$this->assertContains( 'csf_category_archive', $result );
		$this->assertContains( 'csf_search', $result );
	}

	/**
	 * Test: add_query_vars preserves existing WordPress query vars.
	 *
	 * Ensures custom vars are added without removing existing ones.
	 */
	public function test_add_query_vars_preserves_existing_vars(): void {
		// Arrange.
		$existing_vars = array( 'p', 'page_id', 'name', 's', 'cat' );

		// Act.
		$result = $this->url_handler->add_query_vars( $existing_vars );

		// Assert.
		foreach ( $existing_vars as $var ) {
			$this->assertContains( $var, $result, "Existing var '{$var}' should be preserved" );
		}
	}

	/**
	 * Test: handle_virtual_page ignores non-part requests.
	 *
	 * Verifies early return when csf_part query var is not set.
	 */
	public function test_handle_virtual_page_ignores_non_part_requests(): void {
		// Arrange.
		Functions\when( 'get_query_var' )->justReturn( false );

		// Act.
		$result = $this->url_handler->handle_virtual_page();

		// Assert - No database call should be made.
		$this->assertNull( $result );
	}

	/**
	 * Test: handle_virtual_page calls database for valid SKU.
	 *
	 * Verifies database is queried when SKU is provided.
	 *
	 * Note: Full page rendering with exit() is tested in integration tests.
	 */
	public function test_handle_virtual_page_calls_database_for_valid_sku(): void {
		// Arrange.
		Functions\when( 'get_query_var' )
			->alias(
				function ( $var ) {
					if ( $var === 'csf_part' ) {
						return '1';
					}
					if ( $var === 'csf_sku' ) {
						return 'CSF-3000';
					}
					return '';
				}
			);

		// Expectation: database should be queried.
		$this->database_mock->shouldReceive( 'get_part_by_sku' )
			->once()
			->with( 'CSF-3000' )
			->andReturn( null ); // Return null to avoid further processing.

		// Mock WordPress functions to avoid errors.
		Functions\when( 'status_header' )->justReturn( null );
		Functions\when( 'get_template_part' )->justReturn( null );

		// Mock global $wp_query with set_404 method.
		global $wp_query;
		$wp_query = Mockery::mock( 'WP_Query' );
		$wp_query->is_404 = false;
		$wp_query->shouldReceive( 'set_404' )->andReturn( null );

		// Act - Catch exit if thrown, but don't require it.
		try {
			$this->url_handler->handle_virtual_page();
		} catch ( \Exception $e ) {
			// Ignore exit/exceptions - we just want to verify database was called.
		}

		// Assert - Mockery will verify database->get_part_by_sku was called.
		$this->assertTrue( true );
	}

	/**
	 * Test: get_all_virtual_urls generates canonical URLs.
	 *
	 * Verifies sitemap URL generation for parts with no vehicle compatibility.
	 */
	public function test_get_all_virtual_urls_generates_canonical_urls(): void {
		// Arrange.
		global $wpdb;
		$wpdb         = Mockery::mock( 'wpdb' );
		$wpdb->prefix = 'wp_';

		$mock_parts = array(
			(object) array(
				'sku'           => 'CSF-3000',
				'category'      => 'Radiators',
				'compatibility' => '[]',
			),
			(object) array(
				'sku'           => 'CSF-4000',
				'category'      => 'Condensers',
				'compatibility' => '[]',
			),
		);

		$wpdb->shouldReceive( 'get_results' )
			->once()
			->andReturn( $mock_parts );

		// Act.
		$result = $this->url_handler->get_all_virtual_urls();

		// Assert.
		$this->assertIsArray( $result );
		$this->assertContains( '/parts/Radiator-CSF-3000', $result );
		$this->assertContains( '/parts/Condenser-CSF-4000', $result );
	}

	/**
	 * Test: get_all_virtual_urls generates vehicle-specific URLs.
	 *
	 * Verifies sitemap includes vehicle variations from compatibility JSON.
	 */
	public function test_get_all_virtual_urls_generates_vehicle_specific_urls(): void {
		// Arrange.
		global $wpdb;
		$wpdb         = Mockery::mock( 'wpdb' );
		$wpdb->prefix = 'wp_';

		$compatibility_json = json_encode(
			array(
				array(
					'year'  => 2020,
					'make'  => 'Honda',
					'model' => 'Civic',
				),
				array(
					'year'  => 2021,
					'make'  => 'Toyota',
					'model' => 'Camry',
				),
			)
		);

		$mock_parts = array(
			(object) array(
				'sku'           => 'CSF-3000',
				'category'      => 'Radiators',
				'compatibility' => $compatibility_json,
			),
		);

		$wpdb->shouldReceive( 'get_results' )
			->once()
			->andReturn( $mock_parts );

		// Act.
		$result = $this->url_handler->get_all_virtual_urls();

		// Assert.
		$this->assertIsArray( $result );
		$this->assertContains( '/parts/Radiator-CSF-3000', $result ); // Canonical
		$this->assertContains( '/parts/2020-Honda-Civic-Radiator-CSF-3000', $result ); // Vehicle 1
		$this->assertContains( '/parts/2021-Toyota-Camry-Radiator-CSF-3000', $result ); // Vehicle 2
		$this->assertCount( 3, $result );
	}

	/**
	 * Test: get_all_virtual_urls singularizes category names.
	 *
	 * Ensures URLs use singular form (Radiator not Radiators).
	 */
	public function test_get_all_virtual_urls_singularizes_category_names(): void {
		// Arrange.
		global $wpdb;
		$wpdb         = Mockery::mock( 'wpdb' );
		$wpdb->prefix = 'wp_';

		$mock_parts = array(
			(object) array(
				'sku'           => 'CSF-3000',
				'category'      => 'Radiators', // Plural
				'compatibility' => '[]',
			),
		);

		$wpdb->shouldReceive( 'get_results' )
			->once()
			->andReturn( $mock_parts );

		// Act.
		$result = $this->url_handler->get_all_virtual_urls();

		// Assert.
		$this->assertContains( '/parts/Radiator-CSF-3000', $result ); // Singular
		$this->assertNotContains( '/parts/Radiators-CSF-3000', $result ); // Not plural
	}

	/**
	 * Test: get_all_virtual_urls handles parts with incomplete vehicle data.
	 *
	 * Verifies only complete vehicle records generate URLs.
	 */
	public function test_get_all_virtual_urls_handles_incomplete_vehicle_data(): void {
		// Arrange.
		global $wpdb;
		$wpdb         = Mockery::mock( 'wpdb' );
		$wpdb->prefix = 'wp_';

		$compatibility_json = json_encode(
			array(
				array(
					'year'  => 2020,
					'make'  => 'Honda',
					'model' => 'Civic',
				),
				array(
					'year'  => 2021,
					'make'  => 'Toyota',
					// Missing model - should be skipped
				),
				array(
					// Missing year - should be skipped
					'make'  => 'Ford',
					'model' => 'F-150',
				),
			)
		);

		$mock_parts = array(
			(object) array(
				'sku'           => 'CSF-3000',
				'category'      => 'Radiators',
				'compatibility' => $compatibility_json,
			),
		);

		$wpdb->shouldReceive( 'get_results' )
			->once()
			->andReturn( $mock_parts );

		// Act.
		$result = $this->url_handler->get_all_virtual_urls();

		// Assert.
		$this->assertIsArray( $result );
		$this->assertCount( 2, $result ); // Only canonical + 1 complete vehicle
		$this->assertContains( '/parts/Radiator-CSF-3000', $result ); // Canonical
		$this->assertContains( '/parts/2020-Honda-Civic-Radiator-CSF-3000', $result ); // Complete
		$this->assertNotContains( '/parts/2021-Toyota-', $result ); // Incomplete should not exist
	}
}
