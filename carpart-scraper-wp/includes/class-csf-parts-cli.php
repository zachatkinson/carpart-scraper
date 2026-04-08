<?php
/**
 * WP-CLI Commands for CSF Parts.
 *
 * Provides command-line interface for importing and managing parts data.
 * Can be used for automated cron jobs and deployment scripts.
 *
 * @package CSF_Parts_Catalog
 * @since   1.0.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

/**
 * Manage CSF Parts via WP-CLI.
 *
 * ## EXAMPLES
 *
 *     # Import parts from JSON file
 *     $ wp csf-parts import /path/to/parts.json
 *
 *     # Import with verbose output
 *     $ wp csf-parts import /path/to/parts.json --verbose
 *
 *     # Get import statistics
 *     $ wp csf-parts stats
 *
 *     # Clear all parts (dangerous!)
 *     $ wp csf-parts clear --yes
 */
class CSF_Parts_CLI {

	/**
	 * Import parts from a JSON file.
	 *
	 * Imports parts data from a JSON file exported by the Python scraper.
	 * Supports incremental updates - existing parts will be updated, new parts will be created.
	 *
	 * ## OPTIONS
	 *
	 * <file>
	 * : Path to the JSON file to import.
	 *
	 * [--batch-size=<size>]
	 * : Number of parts to process per batch. Default: 50.
	 *
	 * [--verbose]
	 * : Show detailed progress information.
	 *
	 * ## EXAMPLES
	 *
	 *     # Import parts from file
	 *     $ wp csf-parts import /var/www/exports/parts.json
	 *     Success: Imported 1523 parts (1234 created, 289 updated)
	 *
	 *     # Import with custom batch size
	 *     $ wp csf-parts import /path/to/parts.json --batch-size=100
	 *
	 *     # Import with verbose output
	 *     $ wp csf-parts import /path/to/parts.json --verbose
	 *
	 * @when after_wp_load
	 */
	public function import( $args, $assoc_args ) {
		$file_path  = $args[0];
		$batch_size = isset( $assoc_args['batch-size'] ) ? (int) $assoc_args['batch-size'] : 50;
		$verbose    = isset( $assoc_args['verbose'] );

		// Validate file exists.
		if ( ! file_exists( $file_path ) ) {
			WP_CLI::error( "File not found: {$file_path}" );
			return;
		}

		// Validate file is readable.
		if ( ! is_readable( $file_path ) ) {
			WP_CLI::error( "File is not readable: {$file_path}" );
			return;
		}

		WP_CLI::log( "Starting import from: {$file_path}" );

		// Load importer.
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-json-importer.php';
		$importer = new CSF_Parts_JSON_Importer();
		$importer->set_batch_size( $batch_size );

		// Show progress bar if not verbose.
		if ( ! $verbose ) {
			WP_CLI::log( 'Processing parts...' );
		}

		// Run import.
		$start_time = microtime( true );
		$results    = $importer->import_from_file( $file_path );
		$end_time   = microtime( true );
		$duration   = round( $end_time - $start_time, 2 );

		// Display results.
		if ( ! empty( $results['errors'] ) ) {
			WP_CLI::warning( 'Import completed with errors:' );
			foreach ( $results['errors'] as $error ) {
				WP_CLI::log( WP_CLI::colorize( "%R  - {$error}%n" ) );
			}
		}

		if ( ! empty( $results['warnings'] ) && $verbose ) {
			WP_CLI::warning( 'Warnings:' );
			foreach ( $results['warnings'] as $warning ) {
				WP_CLI::log( WP_CLI::colorize( "%Y  - {$warning}%n" ) );
			}
		}

		// Success summary.
		$created   = $results['created'] ?? 0;
		$updated   = $results['updated'] ?? 0;
		$unchanged = $results['unchanged'] ?? 0;
		$skipped   = $results['skipped'] ?? 0;
		$total     = $created + $updated;

		WP_CLI::success(
			sprintf(
				'Imported %d parts in %s seconds (%d created, %d updated, %d unchanged, %d skipped)',
				$total,
				$duration,
				$created,
				$updated,
				$unchanged,
				$skipped
			)
		);

	}

	/**
	 * Show statistics about imported parts.
	 *
	 * Displays counts by category, manufacturer, and vehicle compatibility.
	 *
	 * ## OPTIONS
	 *
	 * [--format=<format>]
	 * : Output format (table, json, csv, yaml). Default: table.
	 *
	 * ## EXAMPLES
	 *
	 *     # Show statistics
	 *     $ wp csf-parts stats
	 *
	 *     # Output as JSON
	 *     $ wp csf-parts stats --format=json
	 *
	 * @when after_wp_load
	 */
	public function stats( $args, $assoc_args ) {
		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-database.php';
		$database = new CSF_Parts_Database();

		$total_parts  = $database->get_total_parts();
		$categories   = $database->get_categories();
		$makes        = $database->get_vehicle_makes();
		$years        = $database->get_vehicle_years();

		$format = isset( $assoc_args['format'] ) ? $assoc_args['format'] : 'table';

		if ( 'table' === $format ) {
			WP_CLI::log( WP_CLI::colorize( '%G=== CSF Parts Statistics ===%n' ) );
			WP_CLI::log( '' );
			WP_CLI::log( sprintf( 'Total Parts: %d', $total_parts ) );
			WP_CLI::log( sprintf( 'Categories: %d', count( $categories ) ) );
			WP_CLI::log( sprintf( 'Vehicle Makes: %d', count( $makes ) ) );
			WP_CLI::log( sprintf( 'Vehicle Years: %d', count( $years ) ) );
			WP_CLI::log( '' );

			if ( ! empty( $categories ) ) {
				WP_CLI::log( WP_CLI::colorize( '%BCategories:%n' ) );
				foreach ( $categories as $category ) {
					$count = count( $database->get_parts_by_category( $category ) );
					WP_CLI::log( sprintf( '  - %s: %d parts', $category, $count ) );
				}
			}

			if ( ! empty( $makes ) ) {
				WP_CLI::log( '' );
				WP_CLI::log( WP_CLI::colorize( '%BTop Vehicle Makes:%n' ) );
				$top_makes = array_slice( $makes, 0, 10 );
				foreach ( $top_makes as $make ) {
					WP_CLI::log( sprintf( '  - %s: %d parts', $make->make, $make->count ) );
				}
			}
		} else {
			$data = array(
				'total_parts' => $total_parts,
				'categories'  => $categories,
				'makes'       => $makes,
				'years'       => array_map(
					function ( $year ) {
						return array(
							'year'  => $year->year,
							'count' => $year->count,
						);
					},
					$years
				),
			);

			WP_CLI\Utils\format_items( $format, array( $data ), array_keys( $data ) );
		}
	}

	/**
	 * Clear all parts from the database.
	 *
	 * WARNING: This will permanently delete all parts data. Use with caution!
	 *
	 * ## OPTIONS
	 *
	 * [--yes]
	 * : Skip confirmation prompt.
	 *
	 * ## EXAMPLES
	 *
	 *     # Clear all parts (with confirmation)
	 *     $ wp csf-parts clear
	 *
	 *     # Clear without confirmation (dangerous!)
	 *     $ wp csf-parts clear --yes
	 *
	 * @when after_wp_load
	 */
	public function clear( $args, $assoc_args ) {
		global $wpdb;

		$skip_confirm = isset( $assoc_args['yes'] );

		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-database.php';
		$database   = new CSF_Parts_Database();
		$part_count = $database->get_total_parts();

		if ( 0 === $part_count ) {
			WP_CLI::log( 'No parts to clear.' );
			return;
		}

		// Confirm before deletion.
		if ( ! $skip_confirm ) {
			WP_CLI::confirm(
				WP_CLI::colorize(
					sprintf(
						"%%RWarning: This will permanently delete %d parts. Are you sure?%%n",
						$part_count
					)
				)
			);
		}

		// Truncate table.
		$table = $wpdb->prefix . 'csf_parts';
		// phpcs:ignore WordPress.DB.PreparedSQL.InterpolatedNotPrepared
		$result = $wpdb->query( "TRUNCATE TABLE {$table}" );

		if ( false === $result ) {
			WP_CLI::error( 'Failed to clear parts table.' );
			return;
		}

		WP_CLI::success( sprintf( 'Cleared %d parts from database.', $part_count ) );
	}

	/**
	 * Verify database integrity and report issues.
	 *
	 * Checks for common data quality issues like missing required fields,
	 * invalid JSON structures, or duplicate SKUs.
	 *
	 * ## OPTIONS
	 *
	 * [--fix]
	 * : Attempt to fix issues automatically.
	 *
	 * ## EXAMPLES
	 *
	 *     # Check for issues
	 *     $ wp csf-parts verify
	 *
	 *     # Check and fix issues
	 *     $ wp csf-parts verify --fix
	 *
	 * @when after_wp_load
	 */
	public function verify( $args, $assoc_args ) {
		global $wpdb;

		$fix = isset( $assoc_args['fix'] );

		require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-database.php';
		$database = new CSF_Parts_Database();
		$table    = $wpdb->prefix . 'csf_parts';

		WP_CLI::log( 'Verifying database integrity...' );
		WP_CLI::log( '' );

		$issues = array();

		// Check for missing SKUs.
		// phpcs:ignore WordPress.DB.PreparedSQL.InterpolatedNotPrepared
		$missing_sku = $wpdb->get_var( "SELECT COUNT(*) FROM {$table} WHERE sku = '' OR sku IS NULL" );
		if ( $missing_sku > 0 ) {
			$issues[] = sprintf( '%d parts with missing SKU', $missing_sku );
		}

		// Check for invalid JSON in specifications.
		// phpcs:ignore WordPress.DB.PreparedSQL.InterpolatedNotPrepared
		$parts = $wpdb->get_results( "SELECT id, specifications, features, compatibility, images FROM {$table}" );
		$invalid_json = 0;

		foreach ( $parts as $part ) {
			$json_fields = array( 'specifications', 'features', 'compatibility', 'images' );
			foreach ( $json_fields as $field ) {
				if ( ! empty( $part->$field ) ) {
					json_decode( $part->$field );
					if ( json_last_error() !== JSON_ERROR_NONE ) {
						$invalid_json++;
						break;
					}
				}
			}
		}

		if ( $invalid_json > 0 ) {
			$issues[] = sprintf( '%d parts with invalid JSON data', $invalid_json );
		}

		// Check for duplicate SKUs.
		// phpcs:ignore WordPress.DB.PreparedSQL.InterpolatedNotPrepared
		$duplicate_skus = $wpdb->get_var( "SELECT COUNT(*) FROM (SELECT sku FROM {$table} GROUP BY sku HAVING COUNT(*) > 1) as dupes" );
		if ( $duplicate_skus > 0 ) {
			$issues[] = sprintf( '%d duplicate SKUs found', $duplicate_skus );
		}

		// Report results.
		if ( empty( $issues ) ) {
			WP_CLI::success( 'Database integrity verified. No issues found.' );
		} else {
			WP_CLI::warning( 'Found issues:' );
			foreach ( $issues as $issue ) {
				WP_CLI::log( WP_CLI::colorize( "%R  - {$issue}%n" ) );
			}

			if ( $fix ) {
				WP_CLI::log( '' );
				WP_CLI::log( 'Attempting to fix issues...' );

				// Fix: Delete parts with missing SKU.
				if ( $missing_sku > 0 ) {
					// phpcs:ignore WordPress.DB.PreparedSQL.InterpolatedNotPrepared
					$wpdb->query( "DELETE FROM {$table} WHERE sku = '' OR sku IS NULL" );
					WP_CLI::log( WP_CLI::colorize( "%G  ✓ Deleted {$missing_sku} parts with missing SKU%n" ) );
				}

				WP_CLI::success( 'Fixed issues. Run verify again to confirm.' );
			} else {
				WP_CLI::log( '' );
				WP_CLI::log( 'Run with --fix flag to attempt automatic repairs.' );
			}
		}
	}

	/**
	 * Migrate images from plugin directory to WordPress uploads.
	 *
	 * Copies product images from the plugin's public/images/ directory to
	 * wp-content/uploads/csf-parts/images/ so they persist across plugin updates.
	 *
	 * ## OPTIONS
	 *
	 * [--source=<path>]
	 * : Source directory for images. Default: plugin's public/images/ directory.
	 *
	 * [--dry-run]
	 * : Show what would be copied without making changes.
	 *
	 * ## EXAMPLES
	 *
	 *     # Migrate images from plugin to uploads
	 *     $ wp csf-parts migrate-images
	 *     Success: Copied 2998 images to wp-content/uploads/csf-parts/
	 *
	 *     # Preview migration
	 *     $ wp csf-parts migrate-images --dry-run
	 *
	 *     # Migrate from custom source
	 *     $ wp csf-parts migrate-images --source=/tmp/images
	 *
	 * @when after_wp_load
	 */
	public function migrate_images( $args, $assoc_args ) {
		$dry_run = isset( $assoc_args['dry-run'] );

		// Determine source directory.
		if ( isset( $assoc_args['source'] ) ) {
			$source_dir = rtrim( $assoc_args['source'], '/' );
		} else {
			$source_dir = CSF_PARTS_PLUGIN_DIR . 'public/images';
		}

		if ( ! is_dir( $source_dir ) ) {
			WP_CLI::error( "Source directory not found: {$source_dir}" );
			return;
		}

		// Determine target directory.
		$upload_dir = wp_upload_dir();
		$target_dir = $upload_dir['basedir'] . '/csf-parts/images';

		WP_CLI::log( sprintf( 'Source: %s', $source_dir ) );
		WP_CLI::log( sprintf( 'Target: %s', $target_dir ) );
		WP_CLI::log( '' );

		if ( $dry_run ) {
			WP_CLI::log( WP_CLI::colorize( '%Y(Dry run mode - no files will be copied)%n' ) );
			WP_CLI::log( '' );
		}

		// Recursively find all image files.
		$iterator = new RecursiveIteratorIterator(
			new RecursiveDirectoryIterator( $source_dir, RecursiveDirectoryIterator::SKIP_DOTS ),
			RecursiveIteratorIterator::SELF_FIRST
		);

		$files_to_copy = array();
		$dirs_to_create = array();

		foreach ( $iterator as $item ) {
			$relative_path = substr( $item->getPathname(), strlen( $source_dir ) );

			if ( $item->isDir() ) {
				$dirs_to_create[] = $target_dir . $relative_path;
			} elseif ( $item->isFile() ) {
				$files_to_copy[] = array(
					'source' => $item->getPathname(),
					'target' => $target_dir . $relative_path,
					'size'   => $item->getSize(),
				);
			}
		}

		if ( empty( $files_to_copy ) ) {
			WP_CLI::warning( 'No image files found in source directory.' );
			return;
		}

		$total_size = array_sum( array_column( $files_to_copy, 'size' ) );
		WP_CLI::log( sprintf(
			'Found %d files (%s) to migrate',
			count( $files_to_copy ),
			size_format( $total_size )
		) );
		WP_CLI::log( '' );

		if ( $dry_run ) {
			// Show first 10 files as sample.
			$sample = array_slice( $files_to_copy, 0, 10 );
			foreach ( $sample as $file ) {
				WP_CLI::log( sprintf( '  %s', basename( $file['source'] ) ) );
			}
			if ( count( $files_to_copy ) > 10 ) {
				WP_CLI::log( sprintf( '  ... and %d more', count( $files_to_copy ) - 10 ) );
			}
			WP_CLI::log( '' );
			WP_CLI::success( sprintf( 'Would copy %d files (%s)', count( $files_to_copy ), size_format( $total_size ) ) );
			return;
		}

		// Create directories.
		foreach ( $dirs_to_create as $dir ) {
			if ( ! file_exists( $dir ) ) {
				wp_mkdir_p( $dir );
			}
		}

		// Copy files with progress bar.
		$progress = \WP_CLI\Utils\make_progress_bar( 'Copying images', count( $files_to_copy ) );
		$copied   = 0;
		$skipped  = 0;
		$errors   = 0;

		foreach ( $files_to_copy as $file ) {
			// Ensure target directory exists.
			$target_subdir = dirname( $file['target'] );
			if ( ! file_exists( $target_subdir ) ) {
				wp_mkdir_p( $target_subdir );
			}

			// Skip if target already exists and is same size.
			if ( file_exists( $file['target'] ) && filesize( $file['target'] ) === $file['size'] ) {
				$skipped++;
				$progress->tick();
				continue;
			}

			// Copy the file.
			if ( copy( $file['source'], $file['target'] ) ) {
				$copied++;
			} else {
				$errors++;
				WP_CLI::warning( sprintf( 'Failed to copy: %s', basename( $file['source'] ) ) );
			}

			$progress->tick();
		}

		$progress->finish();
		WP_CLI::log( '' );

		if ( $errors > 0 ) {
			WP_CLI::warning( sprintf( '%d files failed to copy', $errors ) );
		}

		WP_CLI::success( sprintf(
			'Migration complete: %d copied, %d skipped (already exist), %d errors',
			$copied,
			$skipped,
			$errors
		) );
		WP_CLI::log( sprintf( 'Images are now in: %s', $target_dir ) );
	}

	/**
	 * Revert image URLs in DB from absolute to relative paths.
	 *
	 * If update-image-urls was previously used to bake full URLs into the database,
	 * this command reverts them back to relative paths so the dynamic resolver works.
	 *
	 * ## OPTIONS
	 *
	 * [--dry-run]
	 * : Show what would be updated without making changes.
	 *
	 * ## EXAMPLES
	 *
	 *     # Revert absolute URLs to relative paths
	 *     $ wp csf-parts fix-image-paths
	 *
	 * @when after_wp_load
	 */
	public function fix_image_paths( $args, $assoc_args ) {
		global $wpdb;

		$dry_run = isset( $assoc_args['dry-run'] );
		$table   = $wpdb->prefix . 'csf_parts';

		WP_CLI::log( 'Reverting absolute image URLs to relative paths...' );
		if ( $dry_run ) {
			WP_CLI::log( WP_CLI::colorize( '%Y(Dry run mode - no changes will be made)%n' ) );
		}
		WP_CLI::log( '' );

		// phpcs:ignore WordPress.DB.PreparedSQL.InterpolatedNotPrepared
		$parts = $wpdb->get_results( "SELECT id, sku, images FROM {$table} WHERE images IS NOT NULL AND images != '[]'" );

		if ( empty( $parts ) ) {
			WP_CLI::log( 'No parts with images found.' );
			return;
		}

		$updated = 0;
		$skipped = 0;

		foreach ( $parts as $part ) {
			$images = json_decode( $part->images, true );
			if ( ! is_array( $images ) ) {
				$skipped++;
				continue;
			}

			$modified       = false;
			$updated_images = array_map(
				function ( $img ) use ( &$modified ) {
					$url = is_string( $img ) ? $img : ( $img['url'] ?? '' );

					// Match absolute URLs containing the image path.
					if ( preg_match( '#https?://.*/(images/avif/.+)$#', $url, $matches ) ) {
						if ( is_array( $img ) ) {
							$img['url'] = $matches[1];
						} else {
							$img = $matches[1];
						}
						$modified = true;
					}

					return $img;
				},
				$images
			);

			if ( $modified && ! $dry_run ) {
				$wpdb->update(
					$table,
					array( 'images' => wp_json_encode( $updated_images ) ),
					array( 'id' => $part->id )
				);
				$updated++;
			} elseif ( $modified ) {
				WP_CLI::log( sprintf( 'Would fix: %s', $part->sku ) );
				$updated++;
			} else {
				$skipped++;
			}
		}

		WP_CLI::log( '' );
		if ( $dry_run ) {
			WP_CLI::success( sprintf( 'Would revert %d parts, skip %d', $updated, $skipped ) );
		} else {
			WP_CLI::success( sprintf( 'Reverted %d parts to relative paths, skipped %d', $updated, $skipped ) );
		}
	}
}
