<?php
/**
 * Detail Page Fetcher.
 *
 * Fetches and parses part detail pages from csf.autocaredata.com,
 * extracts specifications, interchange data, descriptions, tech notes,
 * and gallery images. Downloads images and converts to AVIF/WebP.
 *
 * @package CSF_Parts_Catalog
 * @since   1.1.5
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

/**
 * Class CSF_Parts_Detail_Fetcher
 */
class CSF_Parts_Detail_Fetcher {

	/**
	 * Base URL for detail pages.
	 *
	 * @var string
	 */
	const DETAIL_BASE_URL = 'https://csf.autocaredata.com/items/';

	/**
	 * S3 bucket domain for image filtering.
	 *
	 * @var string
	 */
	const S3_IMAGE_DOMAIN = 'illumaware-digital-assets.s3';

	/**
	 * Upload subdirectory for part images.
	 *
	 * @var string
	 */
	const IMAGE_UPLOAD_DIR = 'csf-parts';

	/**
	 * Fetch and parse detail page for a given SKU.
	 *
	 * @since 1.1.5
	 * @param string $sku Part SKU (e.g. "CSF-3542").
	 * @return array|WP_Error Parsed detail data or WP_Error on failure.
	 */
	public function fetch( string $sku ) {
		// Extract numeric portion from SKU for URL (CSF-3542 -> 3542).
		$sku_number = preg_replace( '/^CSF-?/i', '', $sku );
		if ( empty( $sku_number ) ) {
			return new WP_Error( 'invalid_sku', 'Could not extract SKU number from: ' . $sku );
		}

		$url      = self::DETAIL_BASE_URL . rawurlencode( $sku_number );
		$response = wp_remote_get(
			$url,
			array(
				'timeout'    => 30,
				'user-agent' => 'CSF-Parts-Catalog/' . CSF_PARTS_VERSION . ' (WordPress Plugin)',
			)
		);

		if ( is_wp_error( $response ) ) {
			return $response;
		}

		$status_code = wp_remote_retrieve_response_code( $response );
		if ( 200 !== $status_code ) {
			return new WP_Error(
				'fetch_failed',
				sprintf( 'Detail page returned HTTP %d for SKU %s', $status_code, $sku )
			);
		}

		$html = wp_remote_retrieve_body( $response );
		if ( empty( $html ) ) {
			return new WP_Error( 'empty_response', 'Empty response body for SKU ' . $sku );
		}

		return $this->parse_html( $html, $sku );
	}

	/**
	 * Parse detail page HTML and extract all data.
	 *
	 * @since 1.1.5
	 * @param string $html Raw HTML content.
	 * @param string $sku  Part SKU for context.
	 * @return array Parsed detail data.
	 */
	private function parse_html( string $html, string $sku ): array {
		$doc = new DOMDocument();

		// Suppress warnings for malformed HTML.
		$prev = libxml_use_internal_errors( true );
		$doc->loadHTML( $html, LIBXML_HTML_NOIMPLIED | LIBXML_HTML_NODEFDTD );
		libxml_clear_errors();
		libxml_use_internal_errors( $prev );

		$xpath = new DOMXPath( $doc );

		$specifications   = $this->extract_specifications( $xpath );
		$tech_notes       = $this->extract_tech_notes( $specifications );
		$interchange_data = $this->extract_interchange_data( $xpath );
		$description      = $this->extract_description( $xpath );
		$image_urls       = $this->extract_image_urls( $xpath );

		// Download and convert images.
		$local_images = $this->download_images( $image_urls, $sku );

		return array(
			'description'         => $description,
			'specifications'      => $specifications,
			'tech_notes'          => $tech_notes,
			'interchange_numbers' => $interchange_data,
			'images'              => $local_images,
			'fields_updated'      => $this->count_updated_fields( $description, $specifications, $tech_notes, $interchange_data, $local_images ),
		);
	}

	/**
	 * Extract specifications from detail page tables.
	 *
	 * Handles 3 table formats:
	 * - 3-cell triplets: [display, label, value]
	 * - 2-cell rows: [label, value]
	 * - Single-cell: "Label: Value"
	 *
	 * @since 1.1.5
	 * @param DOMXPath $xpath XPath instance.
	 * @return array Associative array of specifications.
	 */
	private function extract_specifications( DOMXPath $xpath ): array {
		$specs  = array();
		$tables = $xpath->query( '//table' );

		foreach ( $tables as $table ) {
			// Skip interchange table (has "Reference Number" header).
			$headers = $this->get_table_headers( $table, $xpath );
			if ( in_array( 'Reference Number', $headers, true ) || in_array( 'Reference Name', $headers, true ) ) {
				continue;
			}

			// Skip vehicle compatibility tables.
			if ( in_array( 'Make', $headers, true ) && in_array( 'Model', $headers, true ) ) {
				continue;
			}

			// Extract data from rows.
			$rows = $xpath->query( './/tr', $table );
			foreach ( $rows as $row ) {
				$cells = $xpath->query( './/td|.//th', $row );
				$this->extract_spec_from_row( $cells, $specs );
			}
		}

		return $specs;
	}

	/**
	 * Get header text from a table element.
	 *
	 * @since 1.1.5
	 * @param DOMElement $table Table element.
	 * @param DOMXPath   $xpath XPath instance.
	 * @return array Array of header strings.
	 */
	private function get_table_headers( DOMElement $table, DOMXPath $xpath ): array {
		$headers  = array();
		$th_nodes = $xpath->query( './/th', $table );
		foreach ( $th_nodes as $th ) {
			$headers[] = trim( $th->textContent );
		}
		return $headers;
	}

	/**
	 * Extract specification key-value pair from a table row.
	 *
	 * @since 1.1.5
	 * @param DOMNodeList $cells Row cells.
	 * @param array       $specs Specs array to populate (by reference).
	 */
	private function extract_spec_from_row( DOMNodeList $cells, array &$specs ): void {
		$count = $cells->length;

		// 3-cell triplets: [display, label, value] repeated.
		if ( $count >= 3 && 0 === $count % 3 ) {
			for ( $i = 0; $i < $count; $i += 3 ) {
				if ( $i + 2 < $count ) {
					$key   = rtrim( trim( $cells->item( $i + 1 )->textContent ), ':' );
					$value = trim( $cells->item( $i + 2 )->textContent );
					if ( ! empty( $key ) && ! empty( $value ) && ! isset( $specs[ $key ] ) ) {
						$specs[ $key ] = $value;
					}
				}
			}
			return;
		}

		// 2-cell rows: [label, value].
		if ( 2 === $count ) {
			$key   = rtrim( trim( $cells->item( 0 )->textContent ), ':' );
			$value = trim( $cells->item( 1 )->textContent );
			if ( ! empty( $key ) && ! empty( $value ) && ! isset( $specs[ $key ] ) ) {
				$specs[ $key ] = $value;
			}
			return;
		}

		// Single-cell: "Label: Value".
		if ( 1 === $count ) {
			$text = trim( $cells->item( 0 )->textContent );
			if ( false !== strpos( $text, ':' ) && strlen( $text ) > 3 ) {
				$parts = explode( ':', $text, 2 );
				$key   = trim( $parts[0] );
				$value = trim( $parts[1] );
				if ( ! empty( $key ) && ! empty( $value ) && ! isset( $specs[ $key ] ) ) {
					$specs[ $key ] = $value;
				}
			}
		}
	}

	/**
	 * Extract tech notes from specifications.
	 *
	 * @since 1.1.5
	 * @param array $specifications Parsed specs array.
	 * @return string|null Tech notes string or null.
	 */
	private function extract_tech_notes( array $specifications ): ?string {
		if ( isset( $specifications['Tech Note'] ) && is_string( $specifications['Tech Note'] ) ) {
			return $specifications['Tech Note'];
		}
		return null;
	}

	/**
	 * Extract interchange/reference numbers from table.
	 *
	 * @since 1.1.5
	 * @param DOMXPath $xpath XPath instance.
	 * @return array List of interchange references.
	 */
	private function extract_interchange_data( DOMXPath $xpath ): array {
		$interchange = array();
		$tables      = $xpath->query( '//table' );

		foreach ( $tables as $table ) {
			$headers = $this->get_table_headers( $table, $xpath );
			if ( ! in_array( 'Reference Number', $headers, true ) || ! in_array( 'Reference Name', $headers, true ) ) {
				continue;
			}

			// Found the interchange table — extract rows (skip header).
			$rows      = $xpath->query( './/tr', $table );
			$first_row = true;
			foreach ( $rows as $row ) {
				if ( $first_row ) {
					$first_row = false;
					continue;
				}

				$cells = $xpath->query( './/td', $row );
				if ( $cells->length >= 2 ) {
					$ref_num  = trim( $cells->item( 0 )->textContent );
					$ref_name = trim( $cells->item( 1 )->textContent );
					if ( ! empty( $ref_num ) && ! empty( $ref_name ) ) {
						$interchange[] = array(
							'reference_number' => $ref_num,
							'reference_type'   => $ref_name,
						);
					}
				}
			}

			break; // Only one interchange table per page.
		}

		return $interchange;
	}

	/**
	 * Extract full description from div.col-6 container.
	 *
	 * The detail page has a div.col-6 containing:
	 * - <h5> title text (e.g. "1 Row Plastic Tank Aluminum Core")
	 * - <p> category/subtitle (e.g. "Radiator")
	 * - Bare text node with marketing copy (semicolon-separated)
	 * - <ul> feature bullet list (not always present)
	 *
	 * @since 1.6.0
	 * @param DOMXPath $xpath XPath instance.
	 * @return string|null HTML-formatted description or null.
	 */
	private function extract_description( DOMXPath $xpath ): ?string {
		$col6_nodes = $xpath->query( "//div[contains(@class, 'col-6')]" );
		if ( 0 === $col6_nodes->length ) {
			return null;
		}

		$col6 = $col6_nodes->item( 0 );
		$parts = array();

		// Extract h5 title.
		$h5_nodes = $xpath->query( './/h5', $col6 );
		if ( $h5_nodes->length > 0 ) {
			$title = trim( $h5_nodes->item( 0 )->textContent );
			if ( ! empty( $title ) ) {
				$parts[] = '<h5>' . esc_html( $title ) . '</h5>';
			}
		}

		// Extract p (category/subtitle).
		$p_nodes = $xpath->query( './/p', $col6 );
		if ( $p_nodes->length > 0 ) {
			$subtitle = trim( $p_nodes->item( 0 )->textContent );
			if ( ! empty( $subtitle ) ) {
				$parts[] = '<p><strong>' . esc_html( $subtitle ) . '</strong></p>';
			}
		}

		// Extract marketing text (bare text nodes directly inside div.col-6).
		$marketing = array();
		foreach ( $col6->childNodes as $child ) {
			if ( XML_TEXT_NODE === $child->nodeType ) {
				$text = trim( $child->textContent );
				if ( strlen( $text ) > 10 ) {
					$marketing[] = $text;
				}
			}
		}

		if ( ! empty( $marketing ) ) {
			$full      = implode( ' ', $marketing );
			$sentences = array_filter( array_map( 'trim', explode( ';', $full ) ) );
			$formatted = array();
			foreach ( $sentences as $sentence ) {
				if ( ! empty( $sentence ) && ! in_array( substr( $sentence, -1 ), array( '.', '!', '?' ), true ) ) {
					$sentence .= '.';
				}
				$formatted[] = esc_html( $sentence );
			}
			if ( ! empty( $formatted ) ) {
				$parts[] = '<p>' . implode( ' ', $formatted ) . '</p>';
			}
		}

		// Extract ul feature list.
		$ul_nodes = $xpath->query( './/ul', $col6 );
		if ( $ul_nodes->length > 0 ) {
			$li_nodes = $xpath->query( './/li', $ul_nodes->item( 0 ) );
			if ( $li_nodes->length > 0 ) {
				$items = array();
				foreach ( $li_nodes as $li ) {
					$text = trim( $li->textContent );
					if ( ! empty( $text ) ) {
						$items[] = '<li>' . esc_html( $text ) . '</li>';
					}
				}
				if ( ! empty( $items ) ) {
					$parts[] = '<ul>' . implode( '', $items ) . '</ul>';
				}
			}
		}

		if ( empty( $parts ) ) {
			return null;
		}

		return implode( "\n", $parts );
	}

	/**
	 * Extract gallery image URLs from S3.
	 *
	 * Filters for large catalog images from the S3 bucket.
	 *
	 * @since 1.1.5
	 * @param DOMXPath $xpath XPath instance.
	 * @return array List of S3 image URLs.
	 */
	private function extract_image_urls( DOMXPath $xpath ): array {
		$urls     = array();
		$img_tags = $xpath->query( '//img[@src]' );

		foreach ( $img_tags as $img ) {
			$src = $img->getAttribute( 'src' );
			// Filter for CSF catalog images: S3 bucket + large images only.
			if ( false !== strpos( $src, self::S3_IMAGE_DOMAIN ) && false !== strpos( $src, '/large/' ) ) {
				$urls[] = $src;
			}
		}

		return $urls;
	}

	/**
	 * Download images from S3 and convert to AVIF (fallback: WebP).
	 *
	 * @since 1.1.5
	 * @param array  $urls S3 image URLs.
	 * @param string $sku  Part SKU for filename.
	 * @return array List of local image URL strings.
	 */
	private function download_images( array $urls, string $sku ): array {
		if ( empty( $urls ) ) {
			return array();
		}

		$upload_dir = wp_upload_dir();
		$target_dir = $upload_dir['basedir'] . '/' . self::IMAGE_UPLOAD_DIR;
		$target_url = $upload_dir['baseurl'] . '/' . self::IMAGE_UPLOAD_DIR;

		// Create directory if it doesn't exist.
		if ( ! file_exists( $target_dir ) ) {
			wp_mkdir_p( $target_dir );
		}

		// Clean SKU for filename (CSF-3542 -> CSF-3542).
		$clean_sku    = sanitize_file_name( $sku );
		$local_images = array();

		foreach ( $urls as $index => $url ) {
			$result = $this->download_and_convert_image( $url, $target_dir, $target_url, $clean_sku, $index );
			if ( null !== $result ) {
				$local_images[] = $result;
			}
		}

		return $local_images;
	}

	/**
	 * Download a single image and convert to AVIF or WebP.
	 *
	 * @since 1.1.5
	 * @param string $url        Remote image URL.
	 * @param string $target_dir Local directory path.
	 * @param string $target_url Local directory URL.
	 * @param string $clean_sku  Sanitized SKU string.
	 * @param int    $index      Image index for filename.
	 * @return string|null Local image URL or null on failure.
	 */
	private function download_and_convert_image( string $url, string $target_dir, string $target_url, string $clean_sku, int $index ): ?string {
		$response = wp_remote_get(
			$url,
			array(
				'timeout'    => 30,
				'user-agent' => 'CSF-Parts-Catalog/' . CSF_PARTS_VERSION . ' (WordPress Plugin)',
			)
		);

		if ( is_wp_error( $response ) || 200 !== wp_remote_retrieve_response_code( $response ) ) {
			return null;
		}

		$image_data = wp_remote_retrieve_body( $response );
		if ( empty( $image_data ) ) {
			return null;
		}

		// Create GD image from raw data.
		$gd_image = @imagecreatefromstring( $image_data );
		if ( false === $gd_image ) {
			return null;
		}

		$filename_base = $clean_sku . '_' . $index;

		// Try AVIF first, fall back to WebP.
		if ( function_exists( 'imageavif' ) ) {
			$filepath = $target_dir . '/' . $filename_base . '.avif';
			$fileurl  = $target_url . '/' . $filename_base . '.avif';
			if ( imageavif( $gd_image, $filepath, 80 ) ) {
				imagedestroy( $gd_image );
				return $fileurl;
			}
		}

		// WebP fallback.
		if ( function_exists( 'imagewebp' ) ) {
			$filepath = $target_dir . '/' . $filename_base . '.webp';
			$fileurl  = $target_url . '/' . $filename_base . '.webp';
			if ( imagewebp( $gd_image, $filepath, 80 ) ) {
				imagedestroy( $gd_image );
				return $fileurl;
			}
		}

		// Last resort: save as original JPEG.
		$filepath = $target_dir . '/' . $filename_base . '.jpg';
		$fileurl  = $target_url . '/' . $filename_base . '.jpg';
		imagejpeg( $gd_image, $filepath, 85 );
		imagedestroy( $gd_image );

		return $fileurl;
	}

	/**
	 * Count how many fields were updated.
	 *
	 * @since 1.1.5
	 * @param string|null $description      Description text.
	 * @param array       $specifications   Specs array.
	 * @param string|null $tech_notes       Tech notes.
	 * @param array       $interchange_data Interchange array.
	 * @param array       $images           Local image URLs.
	 * @return int Number of non-empty fields.
	 */
	private function count_updated_fields( ?string $description, array $specifications, ?string $tech_notes, array $interchange_data, array $images ): int {
		$count = 0;
		if ( ! empty( $description ) ) {
			++$count;
		}
		if ( ! empty( $specifications ) ) {
			++$count;
		}
		if ( ! empty( $tech_notes ) ) {
			++$count;
		}
		if ( ! empty( $interchange_data ) ) {
			++$count;
		}
		if ( ! empty( $images ) ) {
			++$count;
		}
		return $count;
	}
}
