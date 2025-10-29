/**
 * Product Catalog Smart Filters
 *
 * Handles cascading filter behavior:
 * 1. Year must be selected first
 * 2. Make is enabled and populated based on selected year
 * 3. Model is enabled and populated based on selected year + make
 *
 * @package CSF_Parts_Catalog
 * @since   2.0.0
 */

(function() {
	'use strict';

	// Initialize filters for all catalog blocks on the page.
	function initFilters() {
		console.log('CSF Filters: Initializing...');
		const blocks = document.querySelectorAll('.csf-product-catalog');
		console.log('CSF Filters: Found', blocks.length, 'blocks');

		blocks.forEach((block) => {
			const filterForm = block.querySelector('.csf-filter-form');
			if (!filterForm) {
				console.log('CSF Filters: No filter form found in block');
				return;
			}
			console.log('CSF Filters: Filter form found');

			const yearSelect = filterForm.querySelector('select[name="csf_year"]');
			const makeSelect = filterForm.querySelector('select[name="csf_make"]');
			const modelSelect = filterForm.querySelector('select[name="csf_model"]');

			console.log('CSF Filters: Year select:', yearSelect);
			console.log('CSF Filters: Make select:', makeSelect);
			console.log('CSF Filters: Model select:', modelSelect);

			if (!yearSelect || !makeSelect || !modelSelect) {
				console.log('CSF Filters: Missing select elements');
				return;
			}

			console.log('CSF Filters: All selects found, setting up...');

			// Initialize - make and model should start disabled.
			makeSelect.disabled = true;
			modelSelect.disabled = true;
			console.log('CSF Filters: Make and model disabled');

			// Year change handler.
			yearSelect.addEventListener('change', function() {
				const year = this.value;
				console.log('CSF Filters: Year changed to:', year);

				// Reset dependent fields.
				makeSelect.innerHTML = '<option value="">' + csfPartsFilters.selectMake + '</option>';
				modelSelect.innerHTML = '<option value="">' + csfPartsFilters.selectModel + '</option>';
				makeSelect.disabled = true;
				modelSelect.disabled = true;

				if (!year) {
					console.log('CSF Filters: No year selected, stopping');
					return;
				}

				console.log('CSF Filters: Fetching makes for year:', year);
				// Fetch makes for selected year.
				fetchMakesByYear(year, makeSelect);
			});

			// Make change handler.
			makeSelect.addEventListener('change', function() {
				const year = yearSelect.value;
				const make = this.value;

				// Reset model field.
				modelSelect.innerHTML = '<option value="">' + csfPartsFilters.selectModel + '</option>';
				modelSelect.disabled = true;

				if (!make || !year) {
					return;
				}

				// Fetch models for selected year + make.
				fetchModelsByYearMake(year, make, modelSelect);
			});
		});
	}

	/**
	 * Fetch makes for a specific year via AJAX.
	 */
	function fetchMakesByYear(year, makeSelect) {
		console.log('CSF Filters: fetchMakesByYear called with year:', year);
		console.log('CSF Filters: AJAX URL:', csfPartsFilters.ajaxUrl);
		console.log('CSF Filters: Nonce:', csfPartsFilters.nonce);

		// Show loading state.
		makeSelect.disabled = true;
		makeSelect.innerHTML = '<option value="">' + csfPartsFilters.loading + '</option>';

		const data = new FormData();
		data.append('action', 'csf_get_makes_by_year');
		data.append('nonce', csfPartsFilters.nonce);
		data.append('year', year);

		console.log('CSF Filters: Sending AJAX request...');

		fetch(csfPartsFilters.ajaxUrl, {
			method: 'POST',
			body: data,
			credentials: 'same-origin'
		})
		.then(response => {
			console.log('CSF Filters: Got response, status:', response.status);
			return response.json();
		})
		.then(response => {
			console.log('CSF Filters: Response data:', response);
			if (response.success && response.data.makes) {
				console.log('CSF Filters: Success! Makes:', response.data.makes);
				populateSelect(makeSelect, response.data.makes, csfPartsFilters.selectMake);
				makeSelect.disabled = false;
			} else {
				console.log('CSF Filters: No makes found or error:', response);
				makeSelect.innerHTML = '<option value="">' + csfPartsFilters.noMakes + '</option>';
				makeSelect.disabled = true;
			}
		})
		.catch(error => {
			console.error('CSF Filters: Error fetching makes:', error);
			makeSelect.innerHTML = '<option value="">' + csfPartsFilters.error + '</option>';
			makeSelect.disabled = true;
		});
	}

	/**
	 * Fetch models for a specific year and make via AJAX.
	 */
	function fetchModelsByYearMake(year, make, modelSelect) {
		// Show loading state.
		modelSelect.disabled = true;
		modelSelect.innerHTML = '<option value="">' + csfPartsFilters.loading + '</option>';

		const data = new FormData();
		data.append('action', 'csf_get_models_by_year_make');
		data.append('nonce', csfPartsFilters.nonce);
		data.append('year', year);
		data.append('make', make);

		fetch(csfPartsFilters.ajaxUrl, {
			method: 'POST',
			body: data,
			credentials: 'same-origin'
		})
		.then(response => response.json())
		.then(response => {
			if (response.success && response.data.models) {
				populateSelect(modelSelect, response.data.models, csfPartsFilters.selectModel);
				modelSelect.disabled = false;
			} else {
				modelSelect.innerHTML = '<option value="">' + csfPartsFilters.noModels + '</option>';
				modelSelect.disabled = true;
			}
		})
		.catch(error => {
			console.error('Error fetching models:', error);
			modelSelect.innerHTML = '<option value="">' + csfPartsFilters.error + '</option>';
			modelSelect.disabled = true;
		});
	}

	/**
	 * Populate a select element with options.
	 */
	function populateSelect(selectElement, options, placeholderText) {
		selectElement.innerHTML = '<option value="">' + placeholderText + '</option>';

		options.forEach(function(option) {
			const optionElement = document.createElement('option');
			optionElement.value = option;
			optionElement.textContent = option;
			selectElement.appendChild(optionElement);
		});
	}

	// Initialize on DOM ready.
	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', initFilters);
	} else {
		initFilters();
	}
})();
