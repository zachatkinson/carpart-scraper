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

// Handle settings save.
if ( isset( $_POST['csf_save_settings'] ) && check_admin_referer( 'csf_settings_nonce' ) ) {
	// Save settings.
	$cache_duration = isset( $_POST['csf_cache_duration'] ) ? intval( $_POST['csf_cache_duration'] ) : 3600;
	update_option( 'csf_parts_cache_duration', $cache_duration );

	$parts_per_page = isset( $_POST['csf_parts_per_page'] ) ? intval( $_POST['csf_parts_per_page'] ) : 20;
	update_option( 'csf_parts_per_page', $parts_per_page );

	$enable_cache = isset( $_POST['csf_enable_cache'] ) ? 1 : 0;
	update_option( 'csf_parts_enable_cache', $enable_cache );

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

	// Generate API key if requested.
	if ( isset( $_POST['csf_generate_api_key'] ) ) {
		$api_key = CSF_Parts_Auto_Import::generate_api_key();
		update_option( 'csf_parts_api_key', $api_key );
		echo '<div class="notice notice-success is-dismissible"><p>' . esc_html__( 'New API key generated successfully.', CSF_Parts_Constants::TEXT_DOMAIN ) . '</p></div>';
	}

	echo '<div class="notice notice-success is-dismissible"><p>' . esc_html__( 'Settings saved successfully.', CSF_Parts_Constants::TEXT_DOMAIN ) . '</p></div>';
}

// Get current settings.
$cache_duration       = get_option( 'csf_parts_cache_duration', 3600 );
$parts_per_page       = get_option( 'csf_parts_per_page', 20 );
$enable_cache         = get_option( 'csf_parts_enable_cache', 1 );
$auto_import_enabled  = get_option( 'csf_parts_auto_import_enabled', 0 );
$import_source        = get_option( 'csf_parts_import_source', 'url' );
$remote_url           = get_option( 'csf_parts_remote_url', '' );
$import_directory     = get_option( 'csf_parts_import_directory', '' );
$import_frequency     = get_option( 'csf_parts_import_frequency', 'hourly' );
$api_key              = get_option( 'csf_parts_api_key', '' );
?>

<div class="wrap">
	<h1><?php esc_html_e( 'CSF Parts Settings', CSF_Parts_Constants::TEXT_DOMAIN ); ?></h1>

	<form method="post" action="">
		<?php wp_nonce_field( 'csf_settings_nonce' ); ?>

		<table class="form-table" role="presentation">
			<tbody>
				<tr>
					<th scope="row">
						<label for="csf_enable_cache">
							<?php esc_html_e( 'Enable Caching', CSF_Parts_Constants::TEXT_DOMAIN ); ?>
						</label>
					</th>
					<td>
						<input type="checkbox" id="csf_enable_cache" name="csf_enable_cache" value="1" <?php checked( $enable_cache, 1 ); ?> />
						<p class="description">
							<?php esc_html_e( 'Enable caching for REST API responses to improve performance.', CSF_Parts_Constants::TEXT_DOMAIN ); ?>
						</p>
					</td>
				</tr>

				<tr>
					<th scope="row">
						<label for="csf_cache_duration">
							<?php esc_html_e( 'Cache Duration', CSF_Parts_Constants::TEXT_DOMAIN ); ?>
						</label>
					</th>
					<td>
						<input type="number" id="csf_cache_duration" name="csf_cache_duration" value="<?php echo esc_attr( $cache_duration ); ?>" min="60" max="86400" class="regular-text" />
						<p class="description">
							<?php esc_html_e( 'Cache duration in seconds (60-86400). Default: 3600 (1 hour).', CSF_Parts_Constants::TEXT_DOMAIN ); ?>
						</p>
					</td>
				</tr>

				<tr>
					<th scope="row">
						<label for="csf_parts_per_page">
							<?php esc_html_e( 'Parts Per Page', CSF_Parts_Constants::TEXT_DOMAIN ); ?>
						</label>
					</th>
					<td>
						<input type="number" id="csf_parts_per_page" name="csf_parts_per_page" value="<?php echo esc_attr( $parts_per_page ); ?>" min="10" max="100" class="regular-text" />
						<p class="description">
							<?php esc_html_e( 'Default number of parts to display per page in REST API and blocks (10-100). Default: 20.', CSF_Parts_Constants::TEXT_DOMAIN ); ?>
						</p>
					</td>
				</tr>
			</tbody>
		</table>

		<h2><?php esc_html_e( 'Automatic Import', CSF_Parts_Constants::TEXT_DOMAIN ); ?></h2>

		<table class="form-table" role="presentation">
			<tbody>
				<tr>
					<th scope="row">
						<label for="csf_auto_import_enabled">
							<?php esc_html_e( 'Enable Auto-Import', CSF_Parts_Constants::TEXT_DOMAIN ); ?>
						</label>
					</th>
					<td>
						<input type="checkbox" id="csf_auto_import_enabled" name="csf_auto_import_enabled" value="1" <?php checked( $auto_import_enabled, 1 ); ?> />
						<p class="description">
							<?php esc_html_e( 'Automatically import parts from remote sources on a schedule.', CSF_Parts_Constants::TEXT_DOMAIN ); ?>
						</p>
					</td>
				</tr>

				<tr>
					<th scope="row">
						<label for="csf_import_source">
							<?php esc_html_e( 'Import Source', CSF_Parts_Constants::TEXT_DOMAIN ); ?>
						</label>
					</th>
					<td>
						<select id="csf_import_source" name="csf_import_source">
							<option value="url" <?php selected( $import_source, 'url' ); ?>><?php esc_html_e( 'Remote URL', CSF_Parts_Constants::TEXT_DOMAIN ); ?></option>
							<option value="directory" <?php selected( $import_source, 'directory' ); ?>><?php esc_html_e( 'Local Directory', CSF_Parts_Constants::TEXT_DOMAIN ); ?></option>
						</select>
						<p class="description">
							<?php esc_html_e( 'Where to fetch JSON files from.', CSF_Parts_Constants::TEXT_DOMAIN ); ?>
						</p>
					</td>
				</tr>

				<tr class="csf-source-url" style="<?php echo 'url' === $import_source ? '' : 'display: none;'; ?>">
					<th scope="row">
						<label for="csf_remote_url">
							<?php esc_html_e( 'Remote URL', CSF_Parts_Constants::TEXT_DOMAIN ); ?>
						</label>
					</th>
					<td>
						<input type="url" id="csf_remote_url" name="csf_remote_url" value="<?php echo esc_attr( $remote_url ); ?>" class="large-text" placeholder="https://example.com/exports/latest.json" />
						<p class="description">
							<?php esc_html_e( 'Full URL to JSON export file. Can be on S3, DigitalOcean Spaces, or any HTTPS server.', CSF_Parts_Constants::TEXT_DOMAIN ); ?>
						</p>
					</td>
				</tr>

				<tr class="csf-source-directory" style="<?php echo 'directory' === $import_source ? '' : 'display: none;'; ?>">
					<th scope="row">
						<label for="csf_import_directory">
							<?php esc_html_e( 'Import Directory', CSF_Parts_Constants::TEXT_DOMAIN ); ?>
						</label>
					</th>
					<td>
						<input type="text" id="csf_import_directory" name="csf_import_directory" value="<?php echo esc_attr( $import_directory ); ?>" class="large-text" placeholder="/path/to/exports/" />
						<p class="description">
							<?php esc_html_e( 'Absolute path to directory containing JSON files. Latest file will be imported.', CSF_Parts_Constants::TEXT_DOMAIN ); ?>
						</p>
					</td>
				</tr>

				<tr>
					<th scope="row">
						<label for="csf_import_frequency">
							<?php esc_html_e( 'Import Frequency', CSF_Parts_Constants::TEXT_DOMAIN ); ?>
						</label>
					</th>
					<td>
						<select id="csf_import_frequency" name="csf_import_frequency">
							<option value="csf_every_15_minutes" <?php selected( $import_frequency, 'csf_every_15_minutes' ); ?>><?php esc_html_e( 'Every 15 Minutes', CSF_Parts_Constants::TEXT_DOMAIN ); ?></option>
							<option value="csf_every_30_minutes" <?php selected( $import_frequency, 'csf_every_30_minutes' ); ?>><?php esc_html_e( 'Every 30 Minutes', CSF_Parts_Constants::TEXT_DOMAIN ); ?></option>
							<option value="hourly" <?php selected( $import_frequency, 'hourly' ); ?>><?php esc_html_e( 'Hourly', CSF_Parts_Constants::TEXT_DOMAIN ); ?></option>
							<option value="csf_every_6_hours" <?php selected( $import_frequency, 'csf_every_6_hours' ); ?>><?php esc_html_e( 'Every 6 Hours', CSF_Parts_Constants::TEXT_DOMAIN ); ?></option>
							<option value="csf_every_12_hours" <?php selected( $import_frequency, 'csf_every_12_hours' ); ?>><?php esc_html_e( 'Every 12 Hours', CSF_Parts_Constants::TEXT_DOMAIN ); ?></option>
							<option value="daily" <?php selected( $import_frequency, 'daily' ); ?>><?php esc_html_e( 'Daily', CSF_Parts_Constants::TEXT_DOMAIN ); ?></option>
							<option value="disabled" <?php selected( $import_frequency, 'disabled' ); ?>><?php esc_html_e( 'Disabled', CSF_Parts_Constants::TEXT_DOMAIN ); ?></option>
						</select>
						<p class="description">
							<?php esc_html_e( 'How often to check for and import new data.', CSF_Parts_Constants::TEXT_DOMAIN ); ?>
						</p>
					</td>
				</tr>
			</tbody>
		</table>

		<h2><?php esc_html_e( 'Push API Configuration', CSF_Parts_Constants::TEXT_DOMAIN ); ?></h2>
		<p><?php esc_html_e( 'Allow the Python scraper to push JSON data directly to WordPress via REST API.', CSF_Parts_Constants::TEXT_DOMAIN ); ?></p>

		<table class="form-table" role="presentation">
			<tbody>
				<tr>
					<th scope="row">
						<label for="csf_api_key">
							<?php esc_html_e( 'API Key', CSF_Parts_Constants::TEXT_DOMAIN ); ?>
						</label>
					</th>
					<td>
						<?php if ( ! empty( $api_key ) ) : ?>
							<code style="background: #f0f0f1; padding: 5px 10px; display: inline-block; margin-bottom: 10px;"><?php echo esc_html( $api_key ); ?></code>
							<br>
							<button type="submit" name="csf_generate_api_key" class="button" onclick="return confirm('<?php esc_attr_e( 'Are you sure? The old key will stop working.', CSF_Parts_Constants::TEXT_DOMAIN ); ?>');">
								<?php esc_html_e( 'Regenerate API Key', CSF_Parts_Constants::TEXT_DOMAIN ); ?>
							</button>
						<?php else : ?>
							<button type="submit" name="csf_generate_api_key" class="button button-secondary">
								<?php esc_html_e( 'Generate API Key', CSF_Parts_Constants::TEXT_DOMAIN ); ?>
							</button>
						<?php endif; ?>
						<p class="description">
							<?php esc_html_e( 'Use this key to authenticate POST requests to the import API.', CSF_Parts_Constants::TEXT_DOMAIN ); ?>
						</p>
					</td>
				</tr>

				<?php if ( ! empty( $api_key ) ) : ?>
				<tr>
					<th scope="row">
						<?php esc_html_e( 'Endpoint URL', CSF_Parts_Constants::TEXT_DOMAIN ); ?>
					</th>
					<td>
						<code style="background: #f0f0f1; padding: 5px 10px; display: inline-block; word-break: break-all;"><?php echo esc_html( rest_url( 'csf/v1/import' ) ); ?></code>
						<p class="description">
							<?php esc_html_e( 'Send POST requests to this URL with JSON data and include the API key in the X-CSF-API-Key header.', CSF_Parts_Constants::TEXT_DOMAIN ); ?>
						</p>
					</td>
				</tr>

				<tr>
					<th scope="row">
						<?php esc_html_e( 'Python Example', CSF_Parts_Constants::TEXT_DOMAIN ); ?>
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
				<?php esc_html_e( 'Save Settings', CSF_Parts_Constants::TEXT_DOMAIN ); ?>
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

	<h2><?php esc_html_e( 'System Information', CSF_Parts_Constants::TEXT_DOMAIN ); ?></h2>

	<table class="widefat" style="max-width: 600px;">
		<tbody>
			<tr>
				<td><strong><?php esc_html_e( 'Plugin Version', CSF_Parts_Constants::TEXT_DOMAIN ); ?></strong></td>
				<td><?php echo esc_html( CSF_PARTS_VERSION ); ?></td>
			</tr>
			<tr>
				<td><strong><?php esc_html_e( 'WordPress Version', CSF_Parts_Constants::TEXT_DOMAIN ); ?></strong></td>
				<td><?php echo esc_html( get_bloginfo( 'version' ) ); ?></td>
			</tr>
			<tr>
				<td><strong><?php esc_html_e( 'PHP Version', CSF_Parts_Constants::TEXT_DOMAIN ); ?></strong></td>
				<td><?php echo esc_html( phpversion() ); ?></td>
			</tr>
			<tr>
				<td><strong><?php esc_html_e( 'Total Parts', CSF_Parts_Constants::TEXT_DOMAIN ); ?></strong></td>
				<td><?php echo esc_html( number_format_i18n( wp_count_posts( CSF_Parts_Constants::POST_TYPE )->publish ) ); ?></td>
			</tr>
			<tr>
				<td><strong><?php esc_html_e( 'Categories', CSF_Parts_Constants::TEXT_DOMAIN ); ?></strong></td>
				<td><?php echo esc_html( number_format_i18n( wp_count_terms( array( 'taxonomy' => CSF_Parts_Constants::TAXONOMY_CATEGORY ) ) ) ); ?></td>
			</tr>
			<tr>
				<td><strong><?php esc_html_e( 'Vehicle Makes', CSF_Parts_Constants::TEXT_DOMAIN ); ?></strong></td>
				<td><?php echo esc_html( number_format_i18n( wp_count_terms( array( 'taxonomy' => CSF_Parts_Constants::TAXONOMY_MAKE ) ) ) ); ?></td>
			</tr>
			<tr>
				<td><strong><?php esc_html_e( 'Vehicle Models', CSF_Parts_Constants::TEXT_DOMAIN ); ?></strong></td>
				<td><?php echo esc_html( number_format_i18n( wp_count_terms( array( 'taxonomy' => CSF_Parts_Constants::TAXONOMY_MODEL ) ) ) ); ?></td>
			</tr>
			<tr>
				<td><strong><?php esc_html_e( 'Vehicle Years', CSF_Parts_Constants::TEXT_DOMAIN ); ?></strong></td>
				<td><?php echo esc_html( number_format_i18n( wp_count_terms( array( 'taxonomy' => CSF_Parts_Constants::TAXONOMY_YEAR ) ) ) ); ?></td>
			</tr>
		</tbody>
	</table>
</div>
