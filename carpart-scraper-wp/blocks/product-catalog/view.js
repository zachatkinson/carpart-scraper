/**
 * Product Catalog Block - Frontend Interactions
 * Handles auto-search functionality
 */

document.addEventListener('DOMContentLoaded', function() {
	// Find all product catalog blocks
	const catalogBlocks = document.querySelectorAll('.wp-block-csf-parts-product-catalog');

	catalogBlocks.forEach(function(block) {
		const searchInput = block.querySelector('.csf-search-input');
		const form = block.querySelector('.csf-filter-form');

		if (!searchInput || !form) {
			return;
		}

		let debounceTimer = null;
		const DEBOUNCE_DELAY = 500; // Wait 500ms after user stops typing
		const MIN_CHARS = 3; // Minimum characters to trigger search

		/**
		 * Handle search input changes
		 */
		searchInput.addEventListener('input', function(e) {
			const searchValue = e.target.value.trim();

			// Clear existing timer
			if (debounceTimer) {
				clearTimeout(debounceTimer);
			}

			// If empty, submit immediately to show all results
			if (searchValue === '') {
				form.submit();
				return;
			}

			// If less than minimum characters, don't search yet
			if (searchValue.length < MIN_CHARS) {
				return;
			}

			// Set new timer to submit after delay
			debounceTimer = setTimeout(function() {
				form.submit();
			}, DEBOUNCE_DELAY);
		});

		/**
		 * Clear search on Escape key
		 */
		searchInput.addEventListener('keydown', function(e) {
			if (e.key === 'Escape') {
				searchInput.value = '';
				form.submit();
			}
		});
	});
});
