<?php
/**
 * Settings Page View.
 *
 * Plugin settings and configuration.
 *
 * @package CSF_Parts_Catalog
 * @since   1.0.0
 */

// Prevent direct access.
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

// Handle API key generation (separate from settings save).
if ( isset( $_POST['csf_generate_api_key'] ) && check_admin_referer( 'csf_settings_nonce' ) ) {
	require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-auto-import.php';
	$api_key = CSF_Parts_Auto_Import::generate_api_key();
	update_option( 'csf_parts_api_key', $api_key );
	echo '<div class="notice notice-success is-dismissible"><p>' . esc_html( 'New API key generated successfully.' ) . '</p></div>';
}

// Handle settings save.
if ( isset( $_POST['csf_save_settings'] ) && check_admin_referer( 'csf_settings_nonce' ) ) {
	// Save settings.
	$cache_duration = isset( $_POST['csf_cache_duration'] ) ? intval( $_POST['csf_cache_duration'] ) : 3600;
	update_option( 'csf_parts_cache_duration', $cache_duration );

	$parts_per_page = isset( $_POST['csf_parts_per_page'] ) ? intval( $_POST['csf_parts_per_page'] ) : 20;
	update_option( 'csf_parts_per_page', $parts_per_page );

	$enable_cache = isset( $_POST['csf_enable_cache'] ) ? 1 : 0;
	update_option( 'csf_parts_enable_cache', $enable_cache );

	// Appearance settings.
	$color_scheme = isset( $_POST['csf_color_scheme'] ) ? sanitize_key( $_POST['csf_color_scheme'] ) : CSF_Parts_Constants::COLOR_SCHEME_DEFAULT;
	update_option( CSF_Parts_Constants::OPTION_COLOR_SCHEME, CSF_Parts_Assets::sanitize_color_scheme( $color_scheme ) );

	// Part page settings.
	// URL templates keep their {sku} placeholders; the filled URL is escaped at output.
	update_option( CSF_Parts_Constants::OPTION_DISTRIBUTOR_URL, isset( $_POST['csf_distributor_url'] ) ? sanitize_text_field( wp_unslash( $_POST['csf_distributor_url'] ) ) : '' );
	update_option( CSF_Parts_Constants::OPTION_TECH_SERVICE_URL, isset( $_POST['csf_tech_service_url'] ) ? sanitize_text_field( wp_unslash( $_POST['csf_tech_service_url'] ) ) : '' );
	update_option( CSF_Parts_Constants::OPTION_PART_PAGE_NOTE, isset( $_POST['csf_part_page_note'] ) ? sanitize_textarea_field( wp_unslash( $_POST['csf_part_page_note'] ) ) : '' );
	$fitment_layout = isset( $_POST['csf_fitment_layout'] ) ? sanitize_key( wp_unslash( $_POST['csf_fitment_layout'] ) ) : CSF_Parts_Constants::FITMENT_LAYOUT_TABLE;
	update_option( CSF_Parts_Constants::OPTION_FITMENT_LAYOUT, in_array( $fitment_layout, CSF_Parts_Constants::FITMENT_LAYOUTS, true ) ? $fitment_layout : CSF_Parts_Constants::FITMENT_LAYOUT_TABLE );
	update_option( CSF_Parts_Constants::OPTION_RELATED_COUNT, min( CSF_Parts_Constants::RELATED_COUNT_MAX, max( 0, isset( $_POST['csf_related_count'] ) ? (int) $_POST['csf_related_count'] : CSF_Parts_Constants::RELATED_COUNT_DEFAULT ) ) );

	// Auto-import settings.
	$auto_import_enabled = isset( $_POST['csf_auto_import_enabled'] ) ? 1 : 0;
	update_option( 'csf_parts_auto_import_enabled', $auto_import_enabled );

	$import_source = isset( $_POST['csf_import_source'] ) ? sanitize_text_field( $_POST['csf_import_source'] ) : 'url';
	update_option( 'csf_parts_import_source', $import_source );

	$remote_url = isset( $_POST['csf_remote_url'] ) ? esc_url_raw( $_POST['csf_remote_url'] ) : '';
	update_option( 'csf_parts_remote_url', $remote_url );

	$import_directory = isset( $_POST['csf_import_directory'] ) ? sanitize_text_field( $_POST['csf_import_directory'] ) : '';
	update_option( 'csf_parts_import_directory', $import_directory );

	$import_frequency = isset( $_POST['csf_import_frequency'] ) ? sanitize_text_field( $_POST['csf_import_frequency'] ) : 'hourly';
	update_option( 'csf_parts_import_frequency', $import_frequency );

	// Update cron schedule.
	require_once CSF_PARTS_PLUGIN_DIR . 'includes/class-csf-parts-auto-import.php';
	CSF_Parts_Auto_Import::schedule_import( $import_frequency );

	echo '<div class="notice notice-success is-dismissible"><p>' . esc_html( 'Settings saved successfully.' ) . '</p></div>';
}

// Get current settings.
$cache_duration       = get_option( 'csf_parts_cache_duration', 3600 );
$parts_per_page       = get_option( 'csf_parts_per_page', 20 );
$enable_cache         = get_option( 'csf_parts_enable_cache', 1 );
$distributor_url      = (string) get_option( CSF_Parts_Constants::OPTION_DISTRIBUTOR_URL, '' );
$tech_service_url     = (string) get_option( CSF_Parts_Constants::OPTION_TECH_SERVICE_URL, '' );
$part_page_note       = (string) get_option( CSF_Parts_Constants::OPTION_PART_PAGE_NOTE, CSF_Parts_Constants::PART_PAGE_NOTE_DEFAULT );
$fitment_layout       = (string) get_option( CSF_Parts_Constants::OPTION_FITMENT_LAYOUT, CSF_Parts_Constants::FITMENT_LAYOUT_TABLE );
$related_count        = (int) get_option( CSF_Parts_Constants::OPTION_RELATED_COUNT, CSF_Parts_Constants::RELATED_COUNT_DEFAULT );
$color_scheme         = CSF_Parts_Assets::sanitize_color_scheme(
	(string) get_option( CSF_Parts_Constants::OPTION_COLOR_SCHEME, CSF_Parts_Constants::COLOR_SCHEME_DEFAULT )
);
$auto_import_enabled  = get_option( 'csf_parts_auto_import_enabled', 0 );
$import_source        = get_option( 'csf_parts_import_source', 'url' );
$remote_url           = get_option( 'csf_parts_remote_url', '' );
$import_directory     = get_option( 'csf_parts_import_directory', '' );
$import_frequency     = get_option( 'csf_parts_import_frequency', 'hourly' );
$api_key              = get_option( 'csf_parts_api_key', '' );
?>

<div class="wrap">
	<h1><?php echo esc_html( 'CSF Parts Settings' ); ?></h1>

	<form method="post" action="">
		<?php wp_nonce_field( 'csf_settings_nonce' ); ?>

		<table class="form-table" role="presentation">
			<tbody>
				<tr>
					<th scope="row">
						<label for="csf_enable_cache">
							<?php echo esc_html( 'Enable Caching' ); ?>
						</label>
					</th>
					<td>
						<input type="checkbox" id="csf_enable_cache" name="csf_enable_cache" value="1" <?php checked( $enable_cache, 1 ); ?> />
						<p class="description">
							<?php echo esc_html( 'Enable caching for REST API responses to improve performance.' ); ?>
						</p>
					</td>
				</tr>

				<tr>
					<th scope="row">
						<label for="csf_cache_duration">
							<?php echo esc_html( 'Cache Duration' ); ?>
						</label>
					</th>
					<td>
						<input type="number" id="csf_cache_duration" name="csf_cache_duration" value="<?php echo esc_attr( $cache_duration ); ?>" min="60" max="86400" class="regular-text" />
						<p class="description">
							<?php echo esc_html( 'Cache duration in seconds (60-86400). Default: 3600 (1 hour).' ); ?>
						</p>
					</td>
				</tr>

				<tr>
					<th scope="row">
						<label for="csf_parts_per_page">
							<?php echo esc_html( 'Parts Per Page' ); ?>
						</label>
					</th>
					<td>
						<input type="number" id="csf_parts_per_page" name="csf_parts_per_page" value="<?php echo esc_attr( $parts_per_page ); ?>" min="10" max="100" class="regular-text" />
						<p class="description">
							<?php echo esc_html( 'Default number of parts to display per page in REST API and blocks (10-100). Default: 20.' ); ?>
						</p>
					</td>
				</tr>
			</tbody>
		</table>

		<h2><?php echo esc_html( 'Part Page' ); ?></h2>

		<table class="form-table" role="presentation">
			<tbody>
				<tr>
					<th scope="row"><label for="csf_distributor_url"><?php echo esc_html( '"Find a distributor" URL' ); ?></label></th>
					<td>
						<input type="text" id="csf_distributor_url" name="csf_distributor_url" value="<?php echo esc_attr( $distributor_url ); ?>" class="large-text" placeholder="https://example.com/find-a-dealer/" />
						<p class="description"><?php echo esc_html( 'Primary button on part pages. Leave empty to hide it. {sku} and {sku_display} are replaced with the part number.' ); ?></p>
					</td>
				</tr>
				<tr>
					<th scope="row"><label for="csf_tech_service_url"><?php echo esc_html( '"Ask technical service" URL' ); ?></label></th>
					<td>
						<input type="text" id="csf_tech_service_url" name="csf_tech_service_url" value="<?php echo esc_attr( $tech_service_url ); ?>" class="large-text" placeholder="https://example.com/contact/?part={sku}" />
						<p class="description"><?php echo esc_html( 'Secondary button. Use {sku} to prefill the contact form. Leave empty to hide it.' ); ?></p>
					</td>
				</tr>
				<tr>
					<th scope="row"><label for="csf_part_page_note"><?php echo esc_html( 'Note under the buttons' ); ?></label></th>
					<td>
						<textarea id="csf_part_page_note" name="csf_part_page_note" rows="2" class="large-text"><?php echo esc_textarea( $part_page_note ); ?></textarea>
						<p class="description"><?php echo esc_html( 'Small print shown beneath the buttons. Leave empty to hide it.' ); ?></p>
					</td>
				</tr>
				<tr>
					<th scope="row"><label for="csf_fitment_layout"><?php echo esc_html( 'Fitment layout' ); ?></label></th>
					<td>
						<select id="csf_fitment_layout" name="csf_fitment_layout">
							<option value="<?php echo esc_attr( CSF_Parts_Constants::FITMENT_LAYOUT_TABLE ); ?>" <?php selected( $fitment_layout, CSF_Parts_Constants::FITMENT_LAYOUT_TABLE ); ?>><?php echo esc_html( 'Table (make, model, years, engine, notes)' ); ?></option>
							<option value="<?php echo esc_attr( CSF_Parts_Constants::FITMENT_LAYOUT_CARDS ); ?>" <?php selected( $fitment_layout, CSF_Parts_Constants::FITMENT_LAYOUT_CARDS ); ?>><?php echo esc_html( 'Expandable cards (previous layout)' ); ?></option>
						</select>
					</td>
				</tr>
				<tr>
					<th scope="row"><label for="csf_related_count"><?php echo esc_html( 'Related parts' ); ?></label></th>
					<td>
						<input type="number" id="csf_related_count" name="csf_related_count" value="<?php echo esc_attr( (string) $related_count ); ?>" min="0" max="<?php echo esc_attr( (string) CSF_Parts_Constants::RELATED_COUNT_MAX ); ?>" class="small-text" />
						<p class="description"><?php echo esc_html( 'How many "Other parts for this vehicle" cards to show. 0 hides the section.' ); ?></p>
					</td>
				</tr>
			</tbody>
		</table>

		<h2><?php echo esc_html( 'Appearance' ); ?></h2>

		<table class="form-table" role="presentation">
			<tbody>
				<tr>
					<th scope="row">
						<label for="csf_color_scheme">
							<?php echo esc_html( 'Color Scheme' ); ?>
						</label>
					</th>
					<td>
						<select id="csf_color_scheme" name="csf_color_scheme">
							<option value="<?php echo esc_attr( CSF_Parts_Constants::COLOR_SCHEME_AUTO ); ?>" <?php selected( $color_scheme, CSF_Parts_Constants::COLOR_SCHEME_AUTO ); ?>><?php echo esc_html( 'Automatic (follow visitor\'s device setting)' ); ?></option>
							<option value="<?php echo esc_attr( CSF_Parts_Constants::COLOR_SCHEME_LIGHT ); ?>" <?php selected( $color_scheme, CSF_Parts_Constants::COLOR_SCHEME_LIGHT ); ?>><?php echo esc_html( 'Light only' ); ?></option>
							<option value="<?php echo esc_attr( CSF_Parts_Constants::COLOR_SCHEME_DARK ); ?>" <?php selected( $color_scheme, CSF_Parts_Constants::COLOR_SCHEME_DARK ); ?>><?php echo esc_html( 'Dark only' ); ?></option>
						</select>
						<p class="description">
							<?php echo esc_html( 'Controls the plugin\'s built-in dark palette for catalog, search, and part pages. "Automatic" switches to dark colors when the visitor\'s browser or OS prefers dark mode. Choose "Light only" to disable that switching so the plugin always uses your theme\'s light colors.' ); ?>
						</p>
					</td>
				</tr>
			</tbody>
		</table>

		<h2><?php echo esc_html( 'Automatic Import' ); ?></h2>

		<table class="form-table" role="presentation">
			<tbody>
				<tr>
					<th scope="row">
						<label for="csf_auto_import_enabled">
							<?php echo esc_html( 'Enable Auto-Import' ); ?>
						</label>
					</th>
					<td>
						<input type="checkbox" id="csf_auto_import_enabled" name="csf_auto_import_enabled" value="1" <?php checked( $auto_import_enabled, 1 ); ?> />
						<p class="description">
							<?php echo esc_html( 'Automatically import parts from remote sources on a schedule.' ); ?>
						</p>
					</td>
				</tr>

				<tr>
					<th scope="row">
						<label for="csf_import_source">
							<?php echo esc_html( 'Import Source' ); ?>
						</label>
					</th>
					<td>
						<select id="csf_import_source" name="csf_import_source">
							<option value="url" <?php selected( $import_source, 'url' ); ?>><?php echo esc_html( 'Remote URL' ); ?></option>
							<option value="directory" <?php selected( $import_source, 'directory' ); ?>><?php echo esc_html( 'Local Directory' ); ?></option>
						</select>
						<p class="description">
							<?php echo esc_html( 'Where to fetch JSON files from.' ); ?>
						</p>
					</td>
				</tr>

				<tr class="csf-source-url" style="<?php echo 'url' === $import_source ? '' : 'display: none;'; ?>">
					<th scope="row">
						<label for="csf_remote_url">
							<?php echo esc_html( 'Remote URL' ); ?>
						</label>
					</th>
					<td>
						<input type="url" id="csf_remote_url" name="csf_remote_url" value="<?php echo esc_attr( $remote_url ); ?>" class="large-text" placeholder="https://example.com/exports/latest.json" />
						<p class="description">
							<?php echo esc_html( 'Full URL to JSON export file. Can be on S3, DigitalOcean Spaces, or any HTTPS server.' ); ?>
						</p>
					</td>
				</tr>

				<tr class="csf-source-directory" style="<?php echo 'directory' === $import_source ? '' : 'display: none;'; ?>">
					<th scope="row">
						<label for="csf_import_directory">
							<?php echo esc_html( 'Import Directory' ); ?>
						</label>
					</th>
					<td>
						<input type="text" id="csf_import_directory" name="csf_import_directory" value="<?php echo esc_attr( $import_directory ); ?>" class="large-text" placeholder="/path/to/exports/" />
						<p class="description">
							<?php echo esc_html( 'Absolute path to directory containing JSON files. Latest file will be imported.' ); ?>
						</p>
					</td>
				</tr>

				<tr>
					<th scope="row">
						<label for="csf_import_frequency">
							<?php echo esc_html( 'Import Frequency' ); ?>
						</label>
					</th>
					<td>
						<select id="csf_import_frequency" name="csf_import_frequency">
							<option value="csf_every_15_minutes" <?php selected( $import_frequency, 'csf_every_15_minutes' ); ?>><?php echo esc_html( 'Every 15 Minutes' ); ?></option>
							<option value="csf_every_30_minutes" <?php selected( $import_frequency, 'csf_every_30_minutes' ); ?>><?php echo esc_html( 'Every 30 Minutes' ); ?></option>
							<option value="hourly" <?php selected( $import_frequency, 'hourly' ); ?>><?php echo esc_html( 'Hourly' ); ?></option>
							<option value="csf_every_6_hours" <?php selected( $import_frequency, 'csf_every_6_hours' ); ?>><?php echo esc_html( 'Every 6 Hours' ); ?></option>
							<option value="csf_every_12_hours" <?php selected( $import_frequency, 'csf_every_12_hours' ); ?>><?php echo esc_html( 'Every 12 Hours' ); ?></option>
							<option value="daily" <?php selected( $import_frequency, 'daily' ); ?>><?php echo esc_html( 'Daily' ); ?></option>
							<option value="disabled" <?php selected( $import_frequency, 'disabled' ); ?>><?php echo esc_html( 'Disabled' ); ?></option>
						</select>
						<p class="description">
							<?php echo esc_html( 'How often to check for and import new data.' ); ?>
						</p>
					</td>
				</tr>
			</tbody>
		</table>

		<h2><?php echo esc_html( 'Push API Configuration' ); ?></h2>
		<p><?php echo esc_html( 'Allow the Python scraper to push JSON data directly to WordPress via REST API.' ); ?></p>

		<table class="form-table" role="presentation">
			<tbody>
				<tr>
					<th scope="row">
						<label for="csf_api_key">
							<?php echo esc_html( 'API Key' ); ?>
						</label>
					</th>
					<td>
						<?php if ( ! empty( $api_key ) ) : ?>
							<code style="background: #f0f0f1; padding: 5px 10px; display: inline-block; margin-bottom: 10px;"><?php echo esc_html( $api_key ); ?></code>
							<br>
							<button type="submit" name="csf_generate_api_key" class="button" onclick="return confirm('<?php echo esc_attr( 'Are you sure? The old key will stop working.' ); ?>');">
								<?php echo esc_html( 'Regenerate API Key' ); ?>
							</button>
						<?php else : ?>
							<button type="submit" name="csf_generate_api_key" class="button button-secondary">
								<?php echo esc_html( 'Generate API Key' ); ?>
							</button>
						<?php endif; ?>
						<p class="description">
							<?php echo esc_html( 'Use this key to authenticate POST requests to the import API.' ); ?>
						</p>
					</td>
				</tr>

				<?php if ( ! empty( $api_key ) ) : ?>
				<tr>
					<th scope="row">
						<?php echo esc_html( 'Endpoint URL' ); ?>
					</th>
					<td>
						<code style="background: #f0f0f1; padding: 5px 10px; display: inline-block; word-break: break-all;"><?php echo esc_html( rest_url( 'csf/v1/import' ) ); ?></code>
						<p class="description">
							<?php echo esc_html( 'Send POST requests to this URL with JSON data and include the API key in the X-CSF-API-Key header.' ); ?>
						</p>
					</td>
				</tr>

				<tr>
					<th scope="row">
						<?php echo esc_html( 'Python Example' ); ?>
					</th>
					<td>
						<pre style="background: #f0f0f1; padding: 10px; overflow-x: auto;"><code>import requests

url = "<?php echo esc_js( rest_url( 'csf/v1/import' ) ); ?>"
headers = {
    "X-CSF-API-Key": "<?php echo esc_js( $api_key ); ?>",
    "Content-Type": "application/json"
}

with open("parts.json", "r") as f:
    data = f.read()

response = requests.post(url, headers=headers, data=data)
print(response.json())</code></pre>
					</td>
				</tr>
				<?php endif; ?>
			</tbody>
		</table>

		<p class="submit">
			<button type="submit" name="csf_save_settings" class="button button-primary">
				<?php echo esc_html( 'Save Settings' ); ?>
			</button>
		</p>
	</form>

	<script>
	jQuery(document).ready(function($) {
		$('#csf_import_source').on('change', function() {
			if ($(this).val() === 'url') {
				$('.csf-source-url').show();
				$('.csf-source-directory').hide();
			} else {
				$('.csf-source-url').hide();
				$('.csf-source-directory').show();
			}
		});
	});
	</script>

	<hr />

	<h2><?php echo esc_html( 'System Information' ); ?></h2>

	<?php
	// Query the custom table for system info.
	global $wpdb;
	$parts_table = $wpdb->prefix . 'csf_parts';
	$total_parts = (int) $wpdb->get_var( "SELECT COUNT(*) FROM {$parts_table}" );
	$categories  = (int) $wpdb->get_var( "SELECT COUNT(DISTINCT category) FROM {$parts_table} WHERE category IS NOT NULL AND category != ''" );
	?>

	<table class="widefat" style="max-width: 600px;">
		<tbody>
			<tr>
				<td><strong><?php echo esc_html( 'Plugin Version' ); ?></strong></td>
				<td><?php echo esc_html( CSF_PARTS_VERSION ); ?></td>
			</tr>
			<tr>
				<td><strong><?php echo esc_html( 'WordPress Version' ); ?></strong></td>
				<td><?php echo esc_html( get_bloginfo( 'version' ) ); ?></td>
			</tr>
			<tr>
				<td><strong><?php echo esc_html( 'PHP Version' ); ?></strong></td>
				<td><?php echo esc_html( phpversion() ); ?></td>
			</tr>
			<tr>
				<td><strong><?php echo esc_html( 'Total Parts' ); ?></strong></td>
				<td><?php echo esc_html( number_format_i18n( $total_parts ) ); ?></td>
			</tr>
			<tr>
				<td><strong><?php echo esc_html( 'Categories' ); ?></strong></td>
				<td><?php echo esc_html( number_format_i18n( $categories ) ); ?></td>
			</tr>
			<?php
			$upload_dir = wp_upload_dir();
			$image_path = $upload_dir['basedir'] . '/csf-parts/images/avif';
			$image_url  = $upload_dir['baseurl'] . '/csf-parts/images/avif';
			$dir_exists = is_dir( $image_path );
			?>
			<tr>
				<td><strong><?php echo esc_html( 'Image Directory' ); ?></strong></td>
				<td>
					<code><?php echo esc_html( $image_path ); ?></code>
					<?php if ( $dir_exists ) : ?>
						<span style="color: green;">&#10003; <?php echo esc_html( 'exists' ); ?></span>
					<?php else : ?>
						<span style="color: red;">&#10007; <?php echo esc_html( 'not found' ); ?></span>
					<?php endif; ?>
				</td>
			</tr>
			<tr>
				<td><strong><?php echo esc_html( 'Image URL Base' ); ?></strong></td>
				<td><code><?php echo esc_html( $image_url ); ?></code></td>
			</tr>
		</tbody>
	</table>
</div>
