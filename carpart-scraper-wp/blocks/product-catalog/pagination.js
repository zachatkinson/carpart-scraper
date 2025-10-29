/**
 * Product Catalog Pagination
 *
 * Handles AJAX pagination for product catalog block:
 * - Endless scroll
 * - Load more button
 *
 * @package CSF_Parts_Catalog
 * @since   2.0.0
 */

(function() {
	'use strict';

	// Initialize pagination for all catalog blocks on the page.
	function initPagination() {
		const blocks = document.querySelectorAll('.csf-product-catalog[data-ajax="1"]');

		blocks.forEach((block) => {
			const paginationType = block.dataset.paginationType || 'numbered';
			const blockId = block.id;

			if (paginationType === 'endless') {
				initEndlessScroll(block);
			} else if (paginationType === 'loadmore') {
				initLoadMore(block);
			}
		});
	}

	/**
	 * Initialize endless scroll pagination.
	 */
	function initEndlessScroll(block) {
		const trigger = block.querySelector('.csf-endless-trigger');
		if (!trigger) return;

		const loadingIndicator = trigger.querySelector('.csf-loading-indicator');
		let isLoading = false;

		// Create intersection observer.
		const observer = new IntersectionObserver((entries) => {
			entries.forEach((entry) => {
				if (entry.isIntersecting && !isLoading) {
					loadMoreParts(block, trigger, loadingIndicator, () => {
						// After loading, check if we should continue observing.
						const nextPage = parseInt(trigger.dataset.nextPage);
						const totalPages = parseInt(trigger.dataset.totalPages);

						if (nextPage > totalPages) {
							observer.unobserve(trigger);
							trigger.remove();
						}
					});
				}
			});
		}, {
			rootMargin: '100px' // Start loading 100px before trigger is visible.
		});

		observer.observe(trigger);
	}

	/**
	 * Initialize load more button pagination.
	 */
	function initLoadMore(block) {
		const button = block.querySelector('.csf-load-more-btn');
		if (!button) return;

		button.addEventListener('click', function() {
			const trigger = this.closest('.csf-load-more');

			loadMoreParts(block, trigger, null, () => {
				// Update button text or remove if no more pages.
				const nextPage = parseInt(trigger.dataset.nextPage);
				const totalPages = parseInt(trigger.dataset.totalPages);

				if (nextPage > totalPages) {
					trigger.remove();
				} else {
					// Update button text with remaining pages.
					const remaining = totalPages - (nextPage - 1);
					const text = remaining === 1
						? csfPartsPagination.loadMoreSingle.replace('%d', remaining)
						: csfPartsPagination.loadMorePlural.replace('%d', remaining);
					button.textContent = text;
				}
			});
		});
	}

	/**
	 * Load more parts via AJAX.
	 */
	function loadMoreParts(block, trigger, loadingIndicator, callback) {
		const nextPage = parseInt(trigger.dataset.nextPage);
		const gridContainer = block.querySelector('.csf-grid-items');

		// Show loading indicator.
		if (loadingIndicator) {
			loadingIndicator.style.display = 'block';
		}

		// Disable button if it exists.
		const button = trigger.querySelector('.csf-load-more-btn');
		if (button) {
			button.disabled = true;
			button.style.opacity = '0.5';
			button.style.cursor = 'not-allowed';
		}

		// Get current filters from URL parameters.
		const urlParams = new URLSearchParams(window.location.search);
		const year = urlParams.get('csf_year') || '';
		const make = urlParams.get('csf_make') || '';
		const model = urlParams.get('csf_model') || '';
		const category = urlParams.get('csf_category') || '';

		// Get block settings.
		const perPage = parseInt(block.dataset.perPage) || 12;

		// Make AJAX request.
		const data = new FormData();
		data.append('action', 'csf_load_more_parts');
		data.append('nonce', csfPartsPagination.nonce);
		data.append('page', nextPage);
		data.append('per_page', perPage);
		if (year) data.append('year', year);
		if (make) data.append('make', make);
		if (model) data.append('model', model);
		if (category) data.append('category', category);

		fetch(csfPartsPagination.ajaxUrl, {
			method: 'POST',
			body: data,
			credentials: 'same-origin'
		})
		.then(response => response.json())
		.then(response => {
			if (response.success && response.data.html) {
				// Append new parts to grid.
				const tempDiv = document.createElement('div');
				tempDiv.innerHTML = response.data.html;

				while (tempDiv.firstChild) {
					gridContainer.appendChild(tempDiv.firstChild);
				}

				// Update trigger's next page.
				trigger.dataset.nextPage = response.data.current_page + 1;

				// Execute callback.
				if (callback) callback();
			}
		})
		.catch(error => {
			console.error('Error loading more parts:', error);
		})
		.finally(() => {
			// Hide loading indicator.
			if (loadingIndicator) {
				loadingIndicator.style.display = 'none';
			}

			// Re-enable button.
			if (button) {
				button.disabled = false;
				button.style.opacity = '1';
				button.style.cursor = 'pointer';
			}
		});
	}

	// Initialize on DOM ready.
	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', initPagination);
	} else {
		initPagination();
	}
})();
