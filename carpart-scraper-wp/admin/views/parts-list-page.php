<?php
/**
 * Admin Parts List Page.
 *
 * Displays all parts from custom database table.
 *
 * @package CSF_Parts_Catalog
 * @since   1.0.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

global $wpdb;

// Handle bulk actions.
if ( isset( $_POST['action'] ) && isset( $_POST['parts'] ) && isset( $_POST['_wpnonce'] ) ) {
	if ( ! wp_verify_nonce( sanitize_text_field( wp_unslash( $_POST['_wpnonce'] ) ), 'bulk-parts' ) ) {
		wp_die( esc_html__( 'Security check failed', 'csf-parts' ) );
	}

	$action = sanitize_text_field( wp_unslash( $_POST['action'] ) );
	$parts  = array_map( 'intval', wp_unslash( $_POST['parts'] ) );

	if ( 'delete' === $action && ! empty( $parts ) ) {
		$placeholders = implode( ',', array_fill( 0, count( $parts ), '%d' ) );
		$wpdb->query(
			$wpdb->prepare(
				"DELETE FROM {$wpdb->prefix}csf_parts WHERE id IN ($placeholders)", // phpcs:ignore WordPress.DB.PreparedSQL.InterpolatedNotPrepared
				...$parts
			)
		);
		echo '<div class="notice notice-success"><p>' . esc_html__( 'Parts deleted successfully.', 'csf-parts' ) . '</p></div>';
	}
}

// Get parts from database.
$page     = isset( $_GET['paged'] ) ? max( 1, intval( $_GET['paged'] ) ) : 1;
$per_page = 20;
$offset   = ( $page - 1 ) * $per_page;

// Sorting parameters.
$allowed_orderby = array( 'sku', 'name', 'category', 'last_synced', 'updated_at', 'created_at' );
$orderby         = isset( $_GET['orderby'] ) && in_array( $_GET['orderby'], $allowed_orderby, true )
	? sanitize_text_field( wp_unslash( $_GET['orderby'] ) )
	: 'created_at';
$order           = isset( $_GET['order'] ) && in_array( strtolower( $_GET['order'] ), array( 'asc', 'desc' ), true )
	? strtoupper( sanitize_text_field( wp_unslash( $_GET['order'] ) ) )
	: 'DESC';

// Filter parameters.
$filter_category = isset( $_GET['category'] ) ? sanitize_text_field( wp_unslash( $_GET['category'] ) ) : '';
$search_term     = isset( $_GET['s'] ) ? sanitize_text_field( wp_unslash( $_GET['s'] ) ) : '';

// Build WHERE clause.
$where_clauses = array();
$where_values  = array();

if ( '' !== $filter_category ) {
	$where_clauses[] = 'category = %s';
	$where_values[]  = $filter_category;
}

if ( '' !== $search_term ) {
	$where_clauses[] = '(sku LIKE %s OR name LIKE %s)';
	$like_term       = '%' . $wpdb->esc_like( $search_term ) . '%';
	$where_values[]  = $like_term;
	$where_values[]  = $like_term;
}

$where_sql = '';
if ( ! empty( $where_clauses ) ) {
	$where_sql = 'WHERE ' . implode( ' AND ', $where_clauses );
}

// Fetch distinct categories for the filter dropdown.
$categories = $wpdb->get_col( "SELECT DISTINCT category FROM {$wpdb->prefix}csf_parts ORDER BY category ASC" );

// Count query.
if ( ! empty( $where_values ) ) {
	$total_parts = $wpdb->get_var(
		$wpdb->prepare(
			"SELECT COUNT(*) FROM {$wpdb->prefix}csf_parts {$where_sql}", // phpcs:ignore WordPress.DB.PreparedSQL.InterpolatedNotPrepared
			...$where_values
		)
	);
} else {
	$total_parts = $wpdb->get_var( "SELECT COUNT(*) FROM {$wpdb->prefix}csf_parts {$where_sql}" ); // phpcs:ignore WordPress.DB.PreparedSQL.InterpolatedNotPrepared
}
$total_pages = ceil( $total_parts / $per_page );

// Data query — $orderby is whitelisted above so safe to interpolate.
$query_values = array_merge( $where_values, array( $per_page, $offset ) );
$parts        = $wpdb->get_results(
	$wpdb->prepare(
		"SELECT * FROM {$wpdb->prefix}csf_parts {$where_sql} ORDER BY {$orderby} {$order} LIMIT %d OFFSET %d", // phpcs:ignore WordPress.DB.PreparedSQL.InterpolatedNotPrepared
		...$query_values
	)
);

// Build base URL preserving sort/filter params for pagination links.
$pagination_base_args = array( 'page' => 'csf-parts' );
if ( 'created_at' !== $orderby ) {
	$pagination_base_args['orderby'] = $orderby;
}
if ( 'DESC' !== $order ) {
	$pagination_base_args['order'] = strtolower( $order );
}
if ( '' !== $filter_category ) {
	$pagination_base_args['category'] = $filter_category;
}
if ( '' !== $search_term ) {
	$pagination_base_args['s'] = $search_term;
}
$pagination_base_url = add_query_arg( $pagination_base_args, admin_url( 'admin.php' ) );
?>

<div class="wrap">
	<h1 class="wp-heading-inline">
		<?php esc_html_e( 'All Parts', 'csf-parts' ); ?>
	</h1>

	<a href="<?php echo esc_url( admin_url( 'admin.php?page=csf-parts-import' ) ); ?>" class="page-title-action">
		<?php esc_html_e( 'Import Parts', 'csf-parts' ); ?>
	</a>

	<hr class="wp-header-end">

	<form method="get" action="<?php echo esc_url( admin_url( 'admin.php' ) ); ?>">
		<input type="hidden" name="page" value="csf-parts">
		<?php if ( 'created_at' !== $orderby ) : ?>
			<input type="hidden" name="orderby" value="<?php echo esc_attr( $orderby ); ?>">
		<?php endif; ?>
		<?php if ( 'DESC' !== $order ) : ?>
			<input type="hidden" name="order" value="<?php echo esc_attr( strtolower( $order ) ); ?>">
		<?php endif; ?>

		<div class="tablenav top">
			<div class="alignleft actions">
				<label for="filter-by-category" class="screen-reader-text">
					<?php esc_html_e( 'Filter by category', 'csf-parts' ); ?>
				</label>
				<select name="category" id="filter-by-category">
					<option value=""><?php esc_html_e( 'All categories', 'csf-parts' ); ?></option>
					<?php foreach ( $categories as $cat ) : ?>
						<option value="<?php echo esc_attr( $cat ); ?>" <?php selected( $filter_category, $cat ); ?>>
							<?php echo esc_html( $cat ); ?>
						</option>
					<?php endforeach; ?>
				</select>

				<label for="parts-search-input" class="screen-reader-text">
					<?php esc_html_e( 'Search parts', 'csf-parts' ); ?>
				</label>
				<input type="search" id="parts-search-input" name="s" value="<?php echo esc_attr( $search_term ); ?>" placeholder="<?php esc_attr_e( 'Search SKU or name...', 'csf-parts' ); ?>">

				<input type="submit" class="button" value="<?php esc_attr_e( 'Filter', 'csf-parts' ); ?>">
			</div>

			<div class="tablenav-pages">
				<span class="displaying-num">
					<?php
					/* translators: %d: number of parts */
					printf( esc_html( _n( '%d item', '%d items', $total_parts, 'csf-parts' ) ), (int) $total_parts );
					?>
				</span>
				<?php if ( $total_pages > 1 ) : ?>
					<span class="pagination-links">
						<?php
						echo wp_kses_post(
							paginate_links(
								array(
									'base'      => add_query_arg( 'paged', '%#%', $pagination_base_url ),
									'format'    => '',
									'prev_text' => __( '&laquo;', 'csf-parts' ),
									'next_text' => __( '&raquo;', 'csf-parts' ),
									'total'     => $total_pages,
									'current'   => $page,
								)
							)
						);
						?>
					</span>
				<?php endif; ?>
			</div>
		</div>
	</form>

	<?php if ( empty( $parts ) && ( '' !== $filter_category || '' !== $search_term ) ) : ?>
		<div class="notice notice-info">
			<p>
				<?php esc_html_e( 'No parts match your filters.', 'csf-parts' ); ?>
				<a href="<?php echo esc_url( admin_url( 'admin.php?page=csf-parts' ) ); ?>">
					<?php esc_html_e( 'Clear filters', 'csf-parts' ); ?>
				</a>
			</p>
		</div>
	<?php elseif ( empty( $parts ) ) : ?>
		<div class="notice notice-info">
			<p>
				<?php esc_html_e( 'No parts found.', 'csf-parts' ); ?>
				<a href="<?php echo esc_url( admin_url( 'admin.php?page=csf-parts-import' ) ); ?>">
					<?php esc_html_e( 'Import parts now', 'csf-parts' ); ?>
				</a>
			</p>
		</div>
	<?php else : ?>

		<form method="post">
			<?php wp_nonce_field( 'bulk-parts' ); ?>

			<table class="wp-list-table widefat fixed striped">
				<thead>
					<tr>
						<td class="manage-column column-cb check-column">
							<input type="checkbox" id="cb-select-all-1">
						</td>
						<?php
						$sortable_columns = array(
							'sku'         => array( 'label' => __( 'SKU', 'csf-parts' ), 'width' => '15%', 'extra_class' => ' column-primary' ),
							'name'        => array( 'label' => __( 'Name', 'csf-parts' ), 'width' => '30%', 'extra_class' => '' ),
							'category'    => array( 'label' => __( 'Category', 'csf-parts' ), 'width' => '15%', 'extra_class' => '' ),
							'last_synced' => array( 'label' => __( 'Last Synced', 'csf-parts' ), 'width' => '15%', 'extra_class' => '' ),
						);

						foreach ( $sortable_columns as $col_key => $col ) :
							$is_current  = ( $orderby === $col_key );
							$next_order  = $is_current && 'ASC' === $order ? 'desc' : 'asc';
							$sort_class  = $is_current
								? 'sorted ' . strtolower( $order )
								: 'sortable asc';
							$sort_url    = add_query_arg(
								array(
									'orderby'  => $col_key,
									'order'    => $next_order,
									'category' => $filter_category,
									's'        => $search_term,
								),
								admin_url( 'admin.php?page=csf-parts' )
							);
							?>
							<th class="manage-column <?php echo esc_attr( $sort_class . $col['extra_class'] ); ?>" style="width: <?php echo esc_attr( $col['width'] ); ?>;">
								<a href="<?php echo esc_url( $sort_url ); ?>">
									<span><?php echo esc_html( $col['label'] ); ?></span>
									<span class="sorting-indicators">
										<span class="sorting-indicator asc" aria-hidden="true"></span>
										<span class="sorting-indicator desc" aria-hidden="true"></span>
									</span>
								</a>
							</th>
						<?php endforeach; ?>
						<th class="manage-column" style="width: 10%;">
							<?php esc_html_e( 'Images', 'csf-parts' ); ?>
						</th>
						<?php
						$is_updated_current = ( 'updated_at' === $orderby );
						$updated_next_order = $is_updated_current && 'ASC' === $order ? 'desc' : 'asc';
						$updated_sort_class = $is_updated_current
							? 'sorted ' . strtolower( $order )
							: 'sortable desc';
						$updated_sort_url   = add_query_arg(
							array(
								'orderby'  => 'updated_at',
								'order'    => $updated_next_order,
								'category' => $filter_category,
								's'        => $search_term,
							),
							admin_url( 'admin.php?page=csf-parts' )
						);
						?>
						<th class="manage-column <?php echo esc_attr( $updated_sort_class ); ?>" style="width: 10%;">
							<a href="<?php echo esc_url( $updated_sort_url ); ?>">
								<span><?php esc_html_e( 'Updated', 'csf-parts' ); ?></span>
								<span class="sorting-indicators">
									<span class="sorting-indicator asc" aria-hidden="true"></span>
									<span class="sorting-indicator desc" aria-hidden="true"></span>
								</span>
							</a>
						</th>
					</tr>
				</thead>
				<tbody>
					<?php foreach ( $parts as $part ) : ?>
						<?php
						$images = json_decode( $part->images, true );
						$image_count = is_array( $images ) ? count( $images ) : 0;
						// Remove CSF- prefix and hyphens from SKU for clean URL (CSF-3680 -> csf3680).
					$clean_sku = strtolower( str_replace( array( 'CSF-', '-' ), '', $part->sku ) );
					$part_url = home_url( '/parts/csf' . $clean_sku );
						?>
						<tr id="part-row-<?php echo esc_attr( $part->id ); ?>">
							<th scope="row" class="check-column">
								<input type="checkbox" name="parts[]" value="<?php echo esc_attr( $part->id ); ?>">
							</th>
							<td class="column-primary" data-colname="<?php esc_attr_e( 'SKU', 'csf-parts' ); ?>">
								<strong>
									<a href="<?php echo esc_url( $part_url ); ?>" target="_blank">
										<?php echo esc_html( $part->sku ); ?>
									</a>
								</strong>
								<div class="row-actions">
									<span class="view">
										<a href="<?php echo esc_url( $part_url ); ?>" target="_blank">
											<?php esc_html_e( 'View', 'csf-parts' ); ?>
										</a>
										|
									</span>
									<span class="refresh">
										<a href="#" class="csf-refresh-part" data-part-id="<?php echo esc_attr( $part->id ); ?>" data-sku="<?php echo esc_attr( $part->sku ); ?>">
											<?php esc_html_e( 'Refresh', 'csf-parts' ); ?>
										</a>
									</span>
								</div>
							</td>
							<td data-colname="<?php esc_attr_e( 'Name', 'csf-parts' ); ?>">
								<?php echo esc_html( csf_format_sku_display( $part->sku ) ); ?>
							</td>
						<td data-colname="<?php esc_attr_e( 'Category', 'csf-parts' ); ?>">
							<?php echo esc_html( $part->category ); ?>
						</td>
						<td data-colname="<?php esc_attr_e( 'Last Synced', 'csf-parts' ); ?>">
							<?php
							if ( ! empty( $part->last_synced ) && '0000-00-00 00:00:00' !== $part->last_synced ) {
								echo esc_html(
									human_time_diff(
										strtotime( $part->last_synced ),
										current_time( 'timestamp' )
									)
								);
								echo ' ' . esc_html__( 'ago', 'csf-parts' );
							} else {
								echo '<span style="color: #999;">' . esc_html__( 'Never', 'csf-parts' ) . '</span>';
							}
							?>
						</td>
							<td data-colname="<?php esc_attr_e( 'Images', 'csf-parts' ); ?>">
								<?php echo esc_html( $image_count ); ?>
							</td>
							<td data-colname="<?php esc_attr_e( 'Updated', 'csf-parts' ); ?>">
								<?php
								echo esc_html(
									human_time_diff(
										strtotime( $part->updated_at ),
										current_time( 'timestamp' )
									)
								);
								?> <?php esc_html_e( 'ago', 'csf-parts' ); ?>
							</td>
						</tr>
					<?php endforeach; ?>
				</tbody>
			</table>
		</form>

		<div class="tablenav bottom">
			<div class="tablenav-pages">
				<?php if ( $total_pages > 1 ) : ?>
					<span class="pagination-links">
						<?php
						echo wp_kses_post(
							paginate_links(
								array(
									'base'      => add_query_arg( 'paged', '%#%', $pagination_base_url ),
									'format'    => '',
									'prev_text' => __( '&laquo;', 'csf-parts' ),
									'next_text' => __( '&raquo;', 'csf-parts' ),
									'total'     => $total_pages,
									'current'   => $page,
								)
							)
						);
						?>
					</span>
				<?php endif; ?>
			</div>
		</div>

	<?php endif; ?>
</div>

<script>
jQuery(document).ready(function($) {
	// Select/deselect all checkboxes
	$('#cb-select-all-1').on('click', function() {
		$('input[name="parts[]"]').prop('checked', this.checked);
	});
});
</script>
