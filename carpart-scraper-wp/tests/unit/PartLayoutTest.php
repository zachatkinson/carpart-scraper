<?php
/**
 * Unit tests for CSF_Parts_Part_Layout and CSF_Parts_Part_Context.
 *
 * @package CSF_Parts_Catalog
 */

use PHPUnit\Framework\TestCase;

require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-part-context.php';
require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-part-layout.php';

/**
 * Test the part page layout and context.
 */
final class PartLayoutTest extends TestCase {

	protected function tearDown(): void {
		CSF_Parts_Part_Context::clear();
		parent::tearDown();
	}

	/**
	 * The built-in layout uses every part block exactly once and balances its columns.
	 */
	public function test_default_markup_uses_every_block_once(): void {
		// Act
		$markup = CSF_Parts_Part_Layout::default_markup();

		// Assert
		foreach ( CSF_Parts_Part_Layout::BLOCKS as $block ) {
			$this->assertSame( 1, substr_count( $markup, '<!-- wp:csf-parts/' . $block . ' /-->' ), $block );
			$this->assertFileExists( CSF_PARTS_PLUGIN_DIR . 'blocks/' . $block . '/block.json' );
		}
		$this->assertSame( substr_count( $markup, '<!-- wp:column ' ), substr_count( $markup, '<!-- /wp:column -->' ) );
		$this->assertSame( 1, substr_count( $markup, '<!-- wp:columns ' ) );
	}

	/**
	 * Every part block declares the shared editor script, the part stylesheet and core supports.
	 */
	public function test_part_blocks_share_editor_script_style_and_supports(): void {
		foreach ( CSF_Parts_Part_Layout::BLOCKS as $block ) {
			// Act
			$meta = json_decode( (string) file_get_contents( CSF_PARTS_PLUGIN_DIR . 'blocks/' . $block . '/block.json' ), true );

			// Assert
			$this->assertSame( 'csf-parts/' . $block, $meta['name'] );
			$this->assertSame( 'file:../build/part-blocks/index.js', $meta['editorScript'] );
			$this->assertSame( 'csf-part-modern', $meta['style'] );
			$this->assertTrue( $meta['supports']['color']['background'] );
			$this->assertTrue( $meta['supports']['spacing']['padding'] );
		}
	}

	/**
	 * Context is set, read and cleared; current() reads the set view first.
	 */
	public function test_context_set_get_clear(): void {
		// Arrange
		$view = array( 'heading' => 'Radiator for 2024 Toyota Tacoma' );

		// Act
		CSF_Parts_Part_Context::set( $view );
		$during = CSF_Parts_Part_Context::get();
		$current = CSF_Parts_Part_Context::current();
		CSF_Parts_Part_Context::clear();

		// Assert
		$this->assertSame( $view, $during );
		$this->assertSame( $view, $current );
		$this->assertNull( CSF_Parts_Part_Context::get() );
	}
}
