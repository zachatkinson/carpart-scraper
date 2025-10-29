<?php
/**
 * Import Log Page View.
 *
 * Displays history of past imports with results.
 *
 * @package CSF_Parts_Catalog
 * @since   1.0.0
 */

// Prevent direct access.
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

// Get import logs.
$logs = CSF_Parts_Import_Manager::get_import_logs();

// Handle clear logs action.
if ( isset( $_POST['csf_clear_logs'] ) && check_admin_referer( 'csf_clear_logs_nonce' ) ) {
	CSF_Parts_Import_Manager::clear_import_logs();
	wp_safe_redirect( admin_url( 'admin.php?page=csf-parts-import-log&cleared=1' ) );
	exit;
}

$cleared = isset( $_GET['cleared'] ) && '1' === $_GET['cleared'];
?>

<div class="wrap">
	<h1><?php esc_html_e( 'Import Log', CSF_Parts_Constants::TEXT_DOMAIN ); ?></h1>

	<?php if ( $cleared ) : ?>
		<div class="notice notice-success is-dismissible">
			<p><?php esc_html_e( 'Import logs cleared successfully.', CSF_Parts_Constants::TEXT_DOMAIN ); ?></p>
		</div>
	<?php endif; ?>

	<p>
		<a href="<?php echo esc_url( admin_url( 'admin.php?page=csf-parts-import' ) ); ?>" class="button">
			<?php esc_html_e( 'Back to Import', CSF_Parts_Constants::TEXT_DOMAIN ); ?>
		</a>
	</p>

	<?php if ( empty( $logs ) ) : ?>
		<div class="notice notice-info">
			<p><?php esc_html_e( 'No import history found.', CSF_Parts_Constants::TEXT_DOMAIN ); ?></p>
		</div>
	<?php else : ?>
		<form method="post" style="margin-bottom: 20px;">
			<?php wp_nonce_field( 'csf_clear_logs_nonce' ); ?>
			<button type="submit" name="csf_clear_logs" class="button" onclick="return confirm('<?php esc_attr_e( 'Are you sure you want to clear all import logs?', CSF_Parts_Constants::TEXT_DOMAIN ); ?>');">
				<?php esc_html_e( 'Clear Logs', CSF_Parts_Constants::TEXT_DOMAIN ); ?>
			</button>
		</form>

		<table class="wp-list-table widefat fixed striped">
			<thead>
				<tr>
					<th><?php esc_html_e( 'Date', CSF_Parts_Constants::TEXT_DOMAIN ); ?></th>
					<th><?php esc_html_e( 'File', CSF_Parts_Constants::TEXT_DOMAIN ); ?></th>
					<th><?php esc_html_e( 'Parts', CSF_Parts_Constants::TEXT_DOMAIN ); ?></th>
					<th><?php esc_html_e( 'Created', CSF_Parts_Constants::TEXT_DOMAIN ); ?></th>
					<th><?php esc_html_e( 'Updated', CSF_Parts_Constants::TEXT_DOMAIN ); ?></th>
					<th><?php esc_html_e( 'Skipped', CSF_Parts_Constants::TEXT_DOMAIN ); ?></th>
					<th><?php esc_html_e( 'Errors', CSF_Parts_Constants::TEXT_DOMAIN ); ?></th>
					<th><?php esc_html_e( 'Warnings', CSF_Parts_Constants::TEXT_DOMAIN ); ?></th>
					<th><?php esc_html_e( 'Duration', CSF_Parts_Constants::TEXT_DOMAIN ); ?></th>
				</tr>
			</thead>
			<tbody>
				<?php foreach ( array_reverse( $logs ) as $log ) : ?>
					<?php
					$results       = $log['results'] ?? array();
					$error_count   = count( $results['errors'] ?? array() );
					$warning_count = count( $results['warnings'] ?? array() );

					// Calculate duration.
					$duration = '';
					if ( ! empty( $log['started_at'] ) && ! empty( $log['completed_at'] ) ) {
						$start    = strtotime( $log['started_at'] );
						$end      = strtotime( $log['completed_at'] );
						$seconds  = $end - $start;
						$duration = gmdate( 'H:i:s', $seconds );
					}
					?>
					<tr>
						<td>
							<?php echo esc_html( get_date_from_gmt( $log['completed_at'] ?? $log['uploaded_at'], 'Y-m-d H:i:s' ) ); ?>
						</td>
						<td>
							<strong><?php echo esc_html( $log['filename'] ); ?></strong>
						</td>
						<td><?php echo esc_html( number_format_i18n( $log['parts_count'] ) ); ?></td>
						<td><?php echo esc_html( number_format_i18n( $results['created'] ?? 0 ) ); ?></td>
						<td><?php echo esc_html( number_format_i18n( $results['updated'] ?? 0 ) ); ?></td>
						<td><?php echo esc_html( number_format_i18n( $results['skipped'] ?? 0 ) ); ?></td>
						<td>
							<?php if ( $error_count > 0 ) : ?>
								<span style="color: #d63638; font-weight: 600;">
									<?php echo esc_html( number_format_i18n( $error_count ) ); ?>
								</span>
								<button type="button" class="button button-small csf-toggle-details" data-target="errors-<?php echo esc_attr( sanitize_key( $log['completed_at'] ?? $log['uploaded_at'] ) ); ?>">
									<?php esc_html_e( 'View', CSF_Parts_Constants::TEXT_DOMAIN ); ?>
								</button>
							<?php else : ?>
								0
							<?php endif; ?>
						</td>
						<td>
							<?php if ( $warning_count > 0 ) : ?>
								<span style="color: #dba617; font-weight: 600;">
									<?php echo esc_html( number_format_i18n( $warning_count ) ); ?>
								</span>
								<button type="button" class="button button-small csf-toggle-details" data-target="warnings-<?php echo esc_attr( sanitize_key( $log['completed_at'] ?? $log['uploaded_at'] ) ); ?>">
									<?php esc_html_e( 'View', CSF_Parts_Constants::TEXT_DOMAIN ); ?>
								</button>
							<?php else : ?>
								0
							<?php endif; ?>
						</td>
						<td><?php echo esc_html( $duration ); ?></td>
					</tr>

					<!-- Error Details Row -->
					<?php if ( $error_count > 0 ) : ?>
						<tr id="errors-<?php echo esc_attr( sanitize_key( $log['completed_at'] ?? $log['uploaded_at'] ) ); ?>" class="csf-details-row" style="display: none;">
							<td colspan="9">
								<strong><?php esc_html_e( 'Errors:', CSF_Parts_Constants::TEXT_DOMAIN ); ?></strong>
								<ul style="margin: 10px 0; padding-left: 20px;">
									<?php foreach ( $results['errors'] as $error ) : ?>
										<li style="color: #d63638;"><?php echo esc_html( $error ); ?></li>
									<?php endforeach; ?>
								</ul>
							</td>
						</tr>
					<?php endif; ?>

					<!-- Warning Details Row -->
					<?php if ( $warning_count > 0 ) : ?>
						<tr id="warnings-<?php echo esc_attr( sanitize_key( $log['completed_at'] ?? $log['uploaded_at'] ) ); ?>" class="csf-details-row" style="display: none;">
							<td colspan="9">
								<strong><?php esc_html_e( 'Warnings:', CSF_Parts_Constants::TEXT_DOMAIN ); ?></strong>
								<ul style="margin: 10px 0; padding-left: 20px;">
									<?php foreach ( $results['warnings'] as $warning ) : ?>
										<li style="color: #dba617;"><?php echo esc_html( $warning ); ?></li>
									<?php endforeach; ?>
								</ul>
							</td>
						</tr>
					<?php endif; ?>
				<?php endforeach; ?>
			</tbody>
		</table>

		<p class="description">
			<?php
			printf(
				/* translators: %d: number of logs */
				esc_html__( 'Showing %d most recent import(s). Older logs are automatically removed.', CSF_Parts_Constants::TEXT_DOMAIN ),
				count( $logs )
			);
			?>
		</p>
	<?php endif; ?>
</div>

<script>
jQuery(document).ready(function($) {
	$('.csf-toggle-details').on('click', function() {
		const target = $(this).data('target');
		$('#' + target).toggle();
	});
});
</script>
