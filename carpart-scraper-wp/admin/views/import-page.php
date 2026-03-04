<?php
/**
 * Import Page View.
 *
 * Admin page for importing parts from JSON files.
 *
 * @package CSF_Parts_Catalog
 * @since   1.0.0
 */

// Prevent direct access.
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

// Get current import status.
$file_info = get_option( 'csf_parts_import_file' );
?>

<div class="wrap">
	<h1><?php echo esc_html( 'Import Parts' ); ?></h1>

	<div class="csf-import-wrapper">
		<!-- Upload Section -->
		<div class="csf-import-section csf-upload-section">
			<h2><?php echo esc_html( 'Step 1: Upload JSON File' ); ?></h2>
			<p>
				<?php echo esc_html( 'Upload a JSON file exported from the carpart-scraper. The file should contain parts data in the expected format.' ); ?>
			</p>

			<div id="csf-upload-form">
				<input type="file" id="csf-json-file" accept=".json" />
				<button type="button" id="csf-upload-btn" class="button button-primary">
					<?php echo esc_html( 'Upload File' ); ?>
				</button>
			</div>

			<div id="csf-upload-status" style="display: none; margin-top: 15px;">
				<div class="notice notice-info inline">
					<p id="csf-upload-message"></p>
				</div>
			</div>
		</div>

		<!-- Import Section -->
		<div class="csf-import-section csf-import-controls" style="<?php echo $file_info && 'pending' === $file_info['status'] ? '' : 'display: none;'; ?>">
			<h2><?php echo esc_html( 'Step 2: Start Import' ); ?></h2>

			<?php if ( $file_info && 'pending' === $file_info['status'] ) : ?>
				<div class="notice notice-success inline">
					<p>
						<?php
						printf(
							/* translators: 1: filename, 2: parts count */
							esc_html( 'File "%1$s" ready to import (%2$d parts found).' ),
							esc_html( $file_info['filename'] ),
							intval( $file_info['parts_count'] )
						);
						?>
					</p>
				</div>
			<?php endif; ?>

			<p>
				<?php echo esc_html( 'Click the button below to start importing parts. This process may take several minutes depending on the file size.' ); ?>
			</p>

			<div class="csf-import-options">
				<label for="csf-batch-size">
					<?php echo esc_html( 'Batch Size:' ); ?>
				</label>
				<select id="csf-batch-size">
					<option value="25">25</option>
					<option value="50" selected>50</option>
					<option value="100">100</option>
				</select>
				<p class="description">
					<?php echo esc_html( 'Number of parts to process per batch. Lower values use less memory but take longer.' ); ?>
				</p>
			</div>

			<button type="button" id="csf-start-import-btn" class="button button-primary button-large">
				<?php echo esc_html( 'Start Import' ); ?>
			</button>
			<button type="button" id="csf-cancel-import-btn" class="button button-secondary">
				<?php echo esc_html( 'Cancel' ); ?>
			</button>
		</div>

		<!-- Progress Section -->
		<div id="csf-import-progress" style="display: none; margin-top: 20px;">
			<h3><?php echo esc_html( 'Import in Progress' ); ?></h3>
			<div class="csf-progress-bar-wrapper">
				<div class="csf-progress-bar">
					<div class="csf-progress-bar-fill" style="width: 0%;"></div>
				</div>
			</div>
			<p id="csf-progress-message"><?php echo esc_html( 'Processing...' ); ?></p>
		</div>

		<!-- Results Section -->
		<div id="csf-import-results" style="display: none; margin-top: 20px;">
			<h3><?php echo esc_html( 'Import Results' ); ?></h3>
			<div id="csf-results-content"></div>
			<p>
				<a href="<?php echo esc_url( admin_url( 'admin.php?page=csf-parts-import-log' ) ); ?>" class="button button-primary">
					<?php echo esc_html( 'View Import Log' ); ?>
				</a>
			</p>
			<p class="description">
				<?php echo esc_html( 'Parts are stored in the custom database table. Use the REST API or Gutenberg blocks to display them.' ); ?>
			</p>
		</div>

		<!-- Help Section -->
		<div class="csf-import-section csf-help-section" style="margin-top: 30px;">
			<h2><?php echo esc_html( 'JSON File Format' ); ?></h2>
			<p><?php echo esc_html( 'The JSON file should have the following structure. Only "sku" is required; all other fields are optional.' ); ?></p>
			<pre style="background: #f5f5f5; padding: 15px; overflow-x: auto; font-size: 12px; line-height: 1.5;"><code>{
  "parts": [
    {
      "sku": "CSF-3542",
      "name": "3542- Radiator",
      "category": "Radiator",
      "description": "&lt;h5&gt;1 Row Plastic Tank Aluminum Core&lt;/h5&gt;\n&lt;p&gt;&lt;strong&gt;Radiator&lt;/strong&gt;&lt;/p&gt;\n&lt;p&gt;Marketing copy here.&lt;/p&gt;\n&lt;ul&gt;&lt;li&gt;Feature 1&lt;/li&gt;&lt;li&gt;Feature 2&lt;/li&gt;&lt;/ul&gt;",
      "tech_notes": "Direct-Fit OE Replacement",
      "specifications": {
        "Core Length (in)": "19 9/16",
        "Core Width (in)": "29 11/16",
        "Core Thickness (in)": "1 1/4",
        "Inlet Length (in)": "30 1/4",
        "Inlet Width (in)": "1 5/8",
        "No. Of Rows": "1",
        "Core Material": "Aluminum"
      },
      "interchange": [
        {
          "reference_number": "2952",
          "reference_type": "Denso First Time Fit"
        }
      ],
      "images": [
        "/wp-content/uploads/csf-parts/CSF-3542_0.avif"
      ],
      "compatibility": [
        {
          "make": "Honda",
          "model": "Accord",
          "year_start": 2018,
          "year_end": 2022,
          "engine": "1.5L 4 Cyl"
        }
      ]
    }
  ]
}</code></pre>
			<p class="description">
				<?php echo wp_kses_post( 'The <code>description</code> field supports HTML (headings, paragraphs, lists). Generated by <code>merge_for_import.py</code> from the scraper pipeline.' ); ?>
			</p>
		</div>
	</div>
</div>

<style>
.csf-import-wrapper {
	max-width: 900px;
}

.csf-import-section {
	background: #fff;
	border: 1px solid #ccd0d4;
	padding: 20px;
	margin-bottom: 20px;
	box-shadow: 0 1px 1px rgba(0,0,0,.04);
}

.csf-upload-section input[type="file"] {
	margin-right: 10px;
}

.csf-import-options {
	margin: 15px 0;
}

.csf-import-options label {
	display: inline-block;
	margin-right: 10px;
	font-weight: 600;
}

.csf-import-options select {
	width: 100px;
}

.csf-progress-bar-wrapper {
	margin: 15px 0;
}

.csf-progress-bar {
	background: #f0f0f1;
	border: 1px solid #c3c4c7;
	height: 30px;
	border-radius: 3px;
	overflow: hidden;
}

.csf-progress-bar-fill {
	background: #2271b1;
	height: 100%;
	transition: width 0.3s ease;
}

#csf-progress-message {
	margin-top: 10px;
	font-weight: 600;
}

.csf-results-table {
	width: 100%;
	margin-top: 15px;
	border-collapse: collapse;
}

.csf-results-table th,
.csf-results-table td {
	padding: 10px;
	text-align: left;
	border: 1px solid #c3c4c7;
}

.csf-results-table th {
	background: #f6f7f7;
	font-weight: 600;
}

.csf-error-list,
.csf-warning-list {
	margin: 10px 0;
	padding-left: 20px;
}

.csf-error-list li {
	color: #d63638;
}

.csf-warning-list li {
	color: #dba617;
}
</style>

<script>
jQuery(document).ready(function($) {
	const nonce = '<?php echo esc_js( wp_create_nonce( 'csf_parts_import_nonce' ) ); ?>';
	let uploadedFile = <?php echo $file_info ? 'true' : 'false'; ?>;

	// Upload file
	$('#csf-upload-btn').on('click', function() {
		const fileInput = $('#csf-json-file')[0];
		const file = fileInput.files[0];

		if (!file) {
			alert('<?php echo esc_html( 'Please select a file first.' ); ?>');
			return;
		}

		const formData = new FormData();
		formData.append('action', 'csf_parts_upload_json');
		formData.append('nonce', nonce);
		formData.append('file', file);

		$('#csf-upload-btn').prop('disabled', true).text('<?php echo esc_html( 'Uploading...' ); ?>');
		$('#csf-upload-status').hide();

		$.ajax({
			url: ajaxurl,
			type: 'POST',
			data: formData,
			processData: false,
			contentType: false,
			success: function(response) {
				if (response.success) {
					$('#csf-upload-message').text(response.data.message + ' (' + response.data.parts_count + ' parts found)');
					$('#csf-upload-status .notice').removeClass('notice-error').addClass('notice-success');
					$('#csf-upload-status').show();
					$('.csf-import-controls').show();
					uploadedFile = true;
				} else {
					$('#csf-upload-message').text(response.data.message);
					$('#csf-upload-status .notice').removeClass('notice-success').addClass('notice-error');
					$('#csf-upload-status').show();
				}
			},
			error: function() {
				$('#csf-upload-message').text('<?php echo esc_html( 'An error occurred during upload.' ); ?>');
				$('#csf-upload-status .notice').removeClass('notice-success').addClass('notice-error');
				$('#csf-upload-status').show();
			},
			complete: function() {
				$('#csf-upload-btn').prop('disabled', false).text('<?php echo esc_html( 'Upload File' ); ?>');
			}
		});
	});

	// Start import
	$('#csf-start-import-btn').on('click', function() {
		if (!uploadedFile) {
			alert('<?php echo esc_html( 'Please upload a file first.' ); ?>');
			return;
		}

		if (!confirm('<?php echo esc_html( 'Are you sure you want to start the import? This will create/update parts in your database.' ); ?>')) {
			return;
		}

		const batchSize = $('#csf-batch-size').val();

		$('.csf-import-controls').hide();
		$('#csf-import-progress').show();
		$('.csf-progress-bar-fill').css('width', '50%');

		$.ajax({
			url: ajaxurl,
			type: 'POST',
			data: {
				action: 'csf_parts_import_json',
				nonce: nonce,
				batch_size: batchSize
			},
			success: function(response) {
				$('.csf-progress-bar-fill').css('width', '100%');

				if (response.success) {
					$('#csf-progress-message').text('<?php echo esc_html( 'Import completed!' ); ?>');
					displayResults(response.data.results);
				} else {
					$('#csf-progress-message').html('<span style="color: #d63638;">' + response.data.message + '</span>');
				}

				setTimeout(function() {
					$('#csf-import-progress').hide();
					$('#csf-import-results').show();
				}, 1000);
			},
			error: function() {
				$('#csf-progress-message').html('<span style="color: #d63638;"><?php echo esc_html( 'An error occurred during import.' ); ?></span>');
			}
		});
	});

	// Cancel import
	$('#csf-cancel-import-btn').on('click', function() {
		if (confirm('<?php echo esc_html( 'Are you sure you want to cancel? The uploaded file will be removed.' ); ?>')) {
			location.reload();
		}
	});

	// Display results
	function displayResults(results) {
		let html = '<div class="notice notice-success"><p><strong><?php echo esc_html( 'Import completed successfully!' ); ?></strong></p></div>';

		html += '<table class="csf-results-table">';
		html += '<tr><th><?php echo esc_html( 'Metric' ); ?></th><th><?php echo esc_html( 'Count' ); ?></th></tr>';
		html += '<tr><td><?php echo esc_html( 'Parts Created' ); ?></td><td>' + results.created + '</td></tr>';
		html += '<tr><td><?php echo esc_html( 'Parts Updated' ); ?></td><td>' + results.updated + '</td></tr>';
		html += '<tr><td><?php echo esc_html( 'Parts Skipped' ); ?></td><td>' + results.skipped + '</td></tr>';
		html += '</table>';

		if (results.errors && results.errors.length > 0) {
			html += '<h4><?php echo esc_html( 'Errors:' ); ?></h4>';
			html += '<ul class="csf-error-list">';
			results.errors.forEach(function(error) {
				html += '<li>' + error + '</li>';
			});
			html += '</ul>';
		}

		if (results.warnings && results.warnings.length > 0) {
			html += '<h4><?php echo esc_html( 'Warnings:' ); ?></h4>';
			html += '<ul class="csf-warning-list">';
			results.warnings.forEach(function(warning) {
				html += '<li>' + warning + '</li>';
			});
			html += '</ul>';
		}

		$('#csf-results-content').html(html);
	}
});
</script>
