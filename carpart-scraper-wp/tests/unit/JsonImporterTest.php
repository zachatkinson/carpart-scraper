<?php
/**
 * Unit tests for CSF_Parts_JSON_Importer change reporting.
 *
 * @package CSF_Parts
 */

use PHPUnit\Framework\TestCase;
use Brain\Monkey;
use Brain\Monkey\Functions;

/**
 * Tests that an import reports which fields changed, not only how many parts.
 */
final class JsonImporterTest extends TestCase {

	private CSF_Parts_JSON_Importer $importer;

	private $database_mock;

	protected function setUp(): void {
		parent::setUp();
		Monkey\setUp();

		Functions\when( 'wp_json_encode' )->alias( 'json_encode' );

		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-json-importer.php';

		$this->importer      = new CSF_Parts_JSON_Importer();
		$this->database_mock = Mockery::mock( 'CSF_Parts_Database' );
		$this->database_mock->shouldReceive( 'prune_changes' )->andReturn( 0 );

		$reflection = new ReflectionClass( $this->importer );
		$property   = $reflection->getProperty( 'database' );
		$property->setValue( $this->importer, $this->database_mock );
	}

	protected function tearDown(): void {
		Monkey\tearDown();
		Mockery::close();
		parent::tearDown();
	}

	/**
	 * Write a parts payload to a temp file and return its path.
	 *
	 * @param array $parts Part rows.
	 * @return string File path.
	 */
	private function write_parts_file( array $parts ): string {
		$path = tempnam( sys_get_temp_dir(), 'csf-import-' );
		file_put_contents( $path, json_encode( array( 'parts' => $parts ) ) );
		return $path;
	}

	/**
	 * Test: import results carry a per-field histogram and per-SKU sample for updated parts.
	 */
	public function test_import_reports_changed_fields_per_part_and_in_aggregate(): void {
		// Arrange.
		$parts = array(
			array( 'sku' => 'CSF-1' ),
			array( 'sku' => 'CSF-2' ),
			array( 'sku' => 'CSF-3' ),
			array( 'sku' => 'CSF-4' ),
		);
		$file  = $this->write_parts_file( $parts );

		$this->database_mock->shouldReceive( 'get_part_by_sku' )->andReturn( null );
		$this->database_mock->shouldReceive( 'upsert_part' )
			->times( 4 )
			->andReturnUsing(
				static function ( array $data ): array {
					$by_sku = array(
						'CSF-1' => array( 'updated', array( 'compatibility', 'images' ) ),
						'CSF-2' => array( 'updated', array( 'compatibility' ) ),
						'CSF-3' => array( 'unchanged', array() ),
						'CSF-4' => array( 'created', array() ),
					);
					list( $status, $fields ) = $by_sku[ $data['sku'] ];
					return array(
						'id'             => 1,
						'status'         => $status,
						'changed_fields' => $fields,
					);
				}
			);

		// Act.
		$results = $this->importer->import_from_file( $file );
		unlink( $file );

		// Assert.
		$this->assertSame( 2, $results['updated'] );
		$this->assertSame( 1, $results['unchanged'] );
		$this->assertSame( 1, $results['created'] );
		$this->assertSame(
			array(
				'compatibility' => 2,
				'images'        => 1,
			),
			$results['changed_fields']
		);
		$this->assertSame(
			array(
				'CSF-1' => array( 'compatibility', 'images' ),
				'CSF-2' => array( 'compatibility' ),
			),
			$results['changes'],
			'Only updated parts are listed individually'
		);
	}

	/**
	 * Test: the per-SKU sample is capped while the histogram stays complete.
	 */
	public function test_import_caps_per_sku_sample_but_not_histogram(): void {
		// Arrange.
		$count = CSF_Parts_JSON_Importer::MAX_LOGGED_CHANGES + 5;
		$parts = array();
		for ( $i = 0; $i < $count; $i++ ) {
			$parts[] = array( 'sku' => sprintf( 'CSF-%03d', $i ) );
		}
		$file = $this->write_parts_file( $parts );

		$this->database_mock->shouldReceive( 'get_part_by_sku' )->andReturn( null );
		$this->database_mock->shouldReceive( 'upsert_part' )
			->times( $count )
			->andReturn(
				array(
					'id'             => 1,
					'status'         => 'updated',
					'changed_fields' => array( 'compatibility' ),
				)
			);

		// Act.
		$results = $this->importer->import_from_file( $file );
		unlink( $file );

		// Assert.
		$this->assertSame( $count, $results['updated'] );
		$this->assertSame( $count, $results['changed_fields']['compatibility'] );
		$this->assertCount( CSF_Parts_JSON_Importer::MAX_LOGGED_CHANGES, $results['changes'] );
	}
}
