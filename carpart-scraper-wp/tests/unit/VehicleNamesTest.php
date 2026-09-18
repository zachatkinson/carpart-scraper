<?php
/**
 * Unit tests for CSF_Parts_Vehicle_Names.
 *
 * @package CSF_Parts_Catalog
 */

use PHPUnit\Framework\TestCase;

require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-vehicle-names.php';

/**
 * Test human casing of makes, models and engines.
 */
final class VehicleNamesTest extends TestCase {

	public function test_makes_and_models_get_human_casing(): void {
		$this->assertSame( 'GMC', CSF_Parts_Vehicle_Names::make( 'Gmc' ) );
		$this->assertSame( 'BMW', CSF_Parts_Vehicle_Names::make( 'bmw' ) );
		$this->assertSame( 'Toyota', CSF_Parts_Vehicle_Names::make( 'TOYOTA' ) );
		$this->assertSame( 'TT Quattro', CSF_Parts_Vehicle_Names::model( 'Tt Quattro' ) );
		$this->assertSame( 'CC', CSF_Parts_Vehicle_Names::model( 'Cc' ) );
		$this->assertSame( 'RAV4', CSF_Parts_Vehicle_Names::model( 'Rav4' ) );
		$this->assertSame( 'CR-V', CSF_Parts_Vehicle_Names::model( 'Cr-v' ) );
		$this->assertSame( 'F-150', CSF_Parts_Vehicle_Names::model( 'f-150' ) );
		$this->assertSame( 'I-280', CSF_Parts_Vehicle_Names::model( 'I-280' ) );
		$this->assertSame( 'Q5', CSF_Parts_Vehicle_Names::model( 'q5' ) );
		$this->assertSame( 'i3', CSF_Parts_Vehicle_Names::model( 'I3' ) );
		$this->assertSame( 'i3s', CSF_Parts_Vehicle_Names::model( 'I3s' ) );
		$this->assertSame( 'Silverado 1500', CSF_Parts_Vehicle_Names::model( 'Silverado 1500' ) );
		$this->assertSame( 'Escalade ESV', CSF_Parts_Vehicle_Names::model( 'Escalade Esv' ) );
	}

	public function test_engine_short_reads_like_a_sentence(): void {
		$this->assertSame( '2.4 L turbo', CSF_Parts_Vehicle_Names::engine_short( '2.4L L4 2393cc', 'Turbocharged' ) );
		$this->assertSame( '2.4 L turbo', CSF_Parts_Vehicle_Names::engine_short( '2.4L L4 turbo' ) );
		$this->assertSame( '3.5 L', CSF_Parts_Vehicle_Names::engine_short( '3.5L V6 3456cc' ) );
		$this->assertSame( '6.7 L diesel', CSF_Parts_Vehicle_Names::engine_short( '6.7L V8 Power Stroke' ) );
		$this->assertSame( 'Electric', CSF_Parts_Vehicle_Names::engine_short( 'Electric' ) );
	}

	public function test_engine_detailed_keeps_layout_and_displacement(): void {
		$this->assertSame( '2.4 L L4 turbo, 2393 cc', CSF_Parts_Vehicle_Names::engine_detailed( '2.4L L4 2393cc', 'Turbocharged' ) );
		$this->assertSame( '2.9 L L4', CSF_Parts_Vehicle_Names::engine_detailed( '2.9L L4' ) );
	}
}
