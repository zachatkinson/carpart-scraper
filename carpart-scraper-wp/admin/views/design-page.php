<?php
/**
 * Design Page View.
 *
 * Preset selection and per-token overrides for the plugin's design tokens.
 *
 * @package CSF_Parts_Catalog
 * @since   1.9.0
 */

// Prevent direct access.
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

$design = new CSF_Parts_Design();

// Handle reset (drops overrides, keeps preset).
if ( isset( $_POST['csf_design_reset'] ) && check_admin_referer( 'csf_design_nonce' ) ) {
	$current = $design->get_settings();
	update_option( CSF_Parts_Constants::OPTION_DESIGN, array( 'preset' => $current['preset'], 'overrides' => array() ) );
	echo '<div class="notice notice-success is-dismissible"><p>' . esc_html( 'Overrides cleared. The preset values are in effect.' ) . '</p></div>';
}

// Handle save.
if ( isset( $_POST['csf_design_save'] ) && check_admin_referer( 'csf_design_nonce' ) ) {
	$raw = array(
		'preset'    => isset( $_POST['csf_design_preset'] ) ? sanitize_key( wp_unslash( $_POST['csf_design_preset'] ) ) : '',
		'overrides' => isset( $_POST['csf_design'] ) && is_array( $_POST['csf_design'] ) ? array_map( 'sanitize_text_field', wp_unslash( $_POST['csf_design'] ) ) : array(),
	);
	update_option( CSF_Parts_Constants::OPTION_DESIGN, CSF_Parts_Design::sanitize_settings( $raw ) );
	echo '<div class="notice notice-success is-dismissible"><p>' . esc_html( 'Design saved.' ) . '</p></div>';
}

$settings  = $design->get_settings();
$presets   = CSF_Parts_Design::presets();
$tokens    = CSF_Parts_Design::tokens();
$resolved  = CSF_Parts_Design::resolve( $settings );
$preset_js = wp_json_encode( array_map( static fn( $p ) => $p['light'], $presets ) );

$groups = array();
foreach ( $tokens as $token => $meta ) {
	$groups[ $meta['group'] ][ $token ] = $meta;
}
?>

<div class="wrap csf-design-page">
	<h1><?php echo esc_html( 'CSF Parts Design' ); ?></h1>
	<p>
		<?php echo esc_html( 'Pick a preset, then override individual tokens if needed. Empty fields inherit the preset; the preset inherits the theme. Brand colours and radii apply in both light and dark mode; other overrides apply to light mode only.' ); ?>
	</p>

	<form method="post" action="">
		<?php wp_nonce_field( 'csf_design_nonce' ); ?>

		<table class="form-table" role="presentation">
			<tbody>
				<tr>
					<th scope="row"><label for="csf_design_preset"><?php echo esc_html( 'Preset' ); ?></label></th>
					<td>
						<select id="csf_design_preset" name="csf_design_preset">
							<?php foreach ( $presets as $id => $preset ) : ?>
								<option value="<?php echo esc_attr( $id ); ?>" <?php selected( $settings['preset'], $id ); ?>><?php echo esc_html( $preset['label'] ); ?></option>
							<?php endforeach; ?>
						</select>
						<?php foreach ( $presets as $id => $preset ) : ?>
							<p class="description csf-preset-description" data-preset="<?php echo esc_attr( $id ); ?>" <?php echo $settings['preset'] === $id ? '' : 'hidden'; ?>>
								<?php echo esc_html( $preset['description'] ); ?>
							</p>
						<?php endforeach; ?>
					</td>
				</tr>
			</tbody>
		</table>

		<?php foreach ( $groups as $group => $group_tokens ) : ?>
			<h2><?php echo esc_html( $group ); ?></h2>
			<table class="form-table" role="presentation">
				<tbody>
					<?php foreach ( $group_tokens as $token => $meta ) : ?>
						<?php
						$field_id     = 'csf_design_' . $token;
						$override     = $settings['overrides'][ $token ] ?? '';
						$preset_value = $resolved['light'][ $token ] ?? '';
						?>
						<tr>
							<th scope="row"><label for="<?php echo esc_attr( $field_id ); ?>"><?php echo esc_html( $meta['label'] ); ?></label></th>
							<td>
								<?php if ( CSF_Parts_Design::TYPE_COLOR === $meta['type'] ) : ?>
									<input
										type="text"
										id="<?php echo esc_attr( $field_id ); ?>"
										name="csf_design[<?php echo esc_attr( $token ); ?>]"
										class="csf-color-field"
										value="<?php echo esc_attr( $override ); ?>"
										data-default-color="<?php echo esc_attr( $preset_value ); ?>"
										data-token="<?php echo esc_attr( $token ); ?>"
									/>
								<?php else : ?>
									<input
										type="number"
										id="<?php echo esc_attr( $field_id ); ?>"
										name="csf_design[<?php echo esc_attr( $token ); ?>]"
										class="small-text csf-length-field"
										min="0"
										max="64"
										value="<?php echo esc_attr( '' === $override ? '' : (string) (int) $override ); ?>"
										placeholder="<?php echo esc_attr( (int) $preset_value ); ?>"
										data-token="<?php echo esc_attr( $token ); ?>"
									/> px
								<?php endif; ?>
								<p class="description">
									<?php echo esc_html( $meta['help'] ); ?>
									<?php if ( '' !== $preset_value ) : ?>
										<span class="csf-preset-value"><?php echo esc_html( 'Preset: ' . $preset_value ); ?></span>
									<?php else : ?>
										<span class="csf-preset-value"><?php echo esc_html( 'Preset: inherits theme / plugin default' ); ?></span>
									<?php endif; ?>
								</p>
							</td>
						</tr>
					<?php endforeach; ?>
				</tbody>
			</table>
		<?php endforeach; ?>

		<p class="submit">
			<button type="submit" name="csf_design_save" class="button button-primary"><?php echo esc_html( 'Save Design' ); ?></button>
			<button type="submit" name="csf_design_reset" class="button" onclick="return confirm('<?php echo esc_attr( 'Clear all overrides and use the preset values?' ); ?>');"><?php echo esc_html( 'Clear Overrides' ); ?></button>
		</p>
	</form>

	<script>
	jQuery(function($) {
		var presets = <?php echo $preset_js; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- JSON from wp_json_encode. ?>;
		$('.csf-color-field').wpColorPicker();
		$('#csf_design_preset').on('change', function() {
			var id = $(this).val();
			$('.csf-preset-description').prop('hidden', true).filter('[data-preset="' + id + '"]').prop('hidden', false);
			var values = presets[id] || {};
			$('.csf-color-field').each(function() {
				var token = $(this).data('token');
				$(this).closest('td').find('.csf-preset-value').text('Preset: ' + (values[token] || 'inherits theme / plugin default'));
			});
			$('.csf-length-field').each(function() {
				var token = $(this).data('token');
				$(this).attr('placeholder', parseInt(values[token] || '0', 10));
				$(this).closest('td').find('.csf-preset-value').text('Preset: ' + (values[token] || 'plugin default'));
			});
		});
	});
	</script>
</div>
