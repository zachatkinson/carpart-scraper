/**
 * CSF Parts Admin Scripts.
 *
 * Handles admin AJAX actions including part refresh from detail pages.
 *
 * @package CSF_Parts_Catalog
 * @since   1.1.5
 */

/* global jQuery, csfPartsAdmin */
(function ($) {
	'use strict';

	/**
	 * Handle "Refresh" link clicks on the parts list table.
	 */
	$(document).on('click', '.csf-refresh-part', function (e) {
		e.preventDefault();

		var $link = $(this);
		var $row = $link.closest('tr');
		var partId = $link.data('part-id');
		var sku = $link.data('sku');

		// Prevent double-clicks.
		if ($row.hasClass('csf-row-refreshing')) {
			return;
		}

		// Set loading state.
		$row.addClass('csf-row-refreshing')
			.removeClass('csf-row-refreshed csf-row-refresh-error');
		$link.text('Refreshing\u2026');

		$.ajax({
			url: csfPartsAdmin.ajaxUrl,
			type: 'POST',
			data: {
				action: 'csf_refresh_part',
				nonce: csfPartsAdmin.nonce,
				part_id: partId
			},
			success: function (response) {
				$row.removeClass('csf-row-refreshing');

				if (response.success) {
					$row.addClass('csf-row-refreshed');
					$link.text('Refreshed');

					// Update the "Last Synced" column to "just now".
					$row.find('td[data-colname="Last Synced"]').text('just now');

					// Auto-reset after 4 seconds.
					setTimeout(function () {
						$row.removeClass('csf-row-refreshed');
						$link.text('Refresh');
					}, 4000);
				} else {
					$row.addClass('csf-row-refresh-error');
					$link.text('Error');

					// Show error message in a tooltip-style notice.
					var msg = (response.data && response.data.message) ? response.data.message : 'Unknown error';
					$link.attr('title', msg);

					setTimeout(function () {
						$row.removeClass('csf-row-refresh-error');
						$link.text('Refresh').removeAttr('title');
					}, 5000);
				}
			},
			error: function () {
				$row.removeClass('csf-row-refreshing').addClass('csf-row-refresh-error');
				$link.text('Error');

				setTimeout(function () {
					$row.removeClass('csf-row-refresh-error');
					$link.text('Refresh');
				}, 5000);
			}
		});
	});
})(jQuery);
