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
			const searchInput = filterForm.querySelector('input[name="csf_search"]');
			const resultsGrid = block.querySelector('.csf-grid-items');

			console.log('CSF Filters: Year select:', yearSelect);
			console.log('CSF Filters: Make select:', makeSelect);
			console.log('CSF Filters: Model select:', modelSelect);
			console.log('CSF Filters: Search input:', searchInput);

			if (!yearSelect || !makeSelect || !modelSelect) {
				console.log('CSF Filters: Missing select elements');
				return;
			}

			console.log('CSF Filters: All selects found, setting up...');

			// Initialize - make and model should start disabled.
			makeSelect.disabled = true;
			modelSelect.disabled = true;
			console.log('CSF Filters: Make and model disabled');

			// Create loading overlay if it doesn't exist.
			let loadingOverlay = block.querySelector('.csf-loading-overlay');
			if (!loadingOverlay && resultsGrid) {
				loadingOverlay = document.createElement('div');
				loadingOverlay.className = 'csf-loading-overlay';
				loadingOverlay.innerHTML = '<div class="csf-spinner"></div><p>' + csfPartsFilters.loadingResults + '</p>';
				loadingOverlay.style.display = 'none';
				resultsGrid.parentNode.style.position = 'relative';
				resultsGrid.parentNode.insertBefore(loadingOverlay, resultsGrid);
			}

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
					// Trigger filter update to show all results.
					triggerFilterUpdate(filterForm, loadingOverlay);
					return;
				}

				console.log('CSF Filters: Fetching makes for year:', year);
				// Fetch makes for selected year.
				fetchMakesByYear(year, makeSelect);

				// Trigger filter update to show parts for this year.
				triggerFilterUpdate(filterForm, loadingOverlay);
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

				// Auto-submit to show filtered results.
				triggerFilterUpdate(filterForm, loadingOverlay);
			});

			// Model change handler - trigger filter immediately.
			modelSelect.addEventListener('change', function() {
				triggerFilterUpdate(filterForm, loadingOverlay);
			});

			// Search input handler with debounce.
			if (searchInput) {
				let searchTimeout;
				searchInput.addEventListener('input', function() {
					clearTimeout(searchTimeout);
					searchTimeout = setTimeout(() => {
						console.log('CSF Filters: Search input changed:', searchInput.value);
						triggerFilterUpdate(filterForm, loadingOverlay);
					}, 500); // Debounce 500ms
				});
			}

			// Reset button handler.
			const resetButton = filterForm.querySelector('.csf-btn-reset');
			if (resetButton) {
				resetButton.addEventListener('click', function(e) {
					e.preventDefault();
					console.log('CSF Filters: Reset button clicked');

					// Show loading overlay.
					if (loadingOverlay) {
						loadingOverlay.style.display = 'flex';
					}

					// Reset all filter values.
					yearSelect.value = '';
					makeSelect.innerHTML = '<option value="">' + csfPartsFilters.selectMake + '</option>';
					modelSelect.innerHTML = '<option value="">' + csfPartsFilters.selectModel + '</option>';
					makeSelect.disabled = true;
					modelSelect.disabled = true;

					// Reload page without filter parameters.
					window.location.href = window.location.pathname;
				});
			}

			// Initialize cascading filters based on current URL parameters.
			initializeCascadingFilters(yearSelect, makeSelect, modelSelect);
		});
	}

	/**
	 * Initialize cascading filters on page load based on URL parameters.
	 */
	function initializeCascadingFilters(yearSelect, makeSelect, modelSelect) {
		const yearValue = yearSelect.value;
		const makeValue = makeSelect.value;
		const modelValue = modelSelect.value;

		// If year is selected, fetch makes for it.
		if (yearValue) {
			console.log('CSF Filters: Initializing makes for year:', yearValue);
			fetchMakesByYear(yearValue, makeSelect, function() {
				// If make was also selected, restore it and fetch models.
				if (makeValue) {
					makeSelect.value = makeValue;
					console.log('CSF Filters: Initializing models for year/make:', yearValue, makeValue);
					fetchModelsByYearMake(yearValue, makeValue, modelSelect, function() {
						// Restore the model value after models are fetched.
						if (modelValue) {
							modelSelect.value = modelValue;
							console.log('CSF Filters: Restored model value:', modelValue);
						}
					});
				}
			});
		}
	}

	/**
	 * Trigger filter update via AJAX (no page reload, maintains scroll position).
	 *
	 * @param {HTMLFormElement} form     The filter form element.
	 * @param {HTMLElement}     loadingOverlay Loading overlay element.
	 * @param {number}         page     Page number to fetch (default 1).
	 */
	function triggerFilterUpdate(form, loadingOverlay, page) {
		var requestedPage = page || 1;
		console.log('CSF Filters: Triggering filter update via AJAX, page:', requestedPage);

		// Show loading overlay.
		if (loadingOverlay) {
			loadingOverlay.style.display = 'flex';
		}

		// Get current filter values.
		const formData = new FormData(form);
		const year = formData.get('csf_year') || '';
		const make = formData.get('csf_make') || '';
		const model = formData.get('csf_model') || '';
		const searchQuery = formData.get('csf_search') || '';

		// Get block attributes.
		const block = form.closest('.csf-product-catalog');
		const defaultCategories = block ? (block.dataset.defaultCategories || '') : '';
		const perPage = block ? (block.dataset.perPage || '12') : '12';

		// Build AJAX data.
		const data = new FormData();
		data.append('action', 'csf_filter_products');
		data.append('nonce', csfPartsFilters.nonce);
		data.append('csf_year', year);
		data.append('csf_make', make);
		data.append('csf_model', model);
		data.append('csf_search', searchQuery);
		data.append('per_page', perPage);
		data.append('page', requestedPage);
		if (defaultCategories) {
			data.append('default_categories', defaultCategories);
		}

		console.log('CSF Filters: Fetching filtered results...', {year, make, model, searchQuery, defaultCategories, perPage, page: requestedPage});

		// Fetch filtered results.
		fetch(csfPartsFilters.ajaxUrl, {
			method: 'POST',
			body: data,
			credentials: 'same-origin'
		})
		.then(function(response) { return response.json(); })
		.then(function(response) {
			console.log('CSF Filters: Filter response:', response);

			if (response.success && response.data.html) {
				var catalog = form.closest('.csf-product-catalog');

				// Update results grid with new HTML.
				var resultsGrid = catalog.querySelector('.csf-grid-items');
				if (resultsGrid) {
					resultsGrid.innerHTML = response.data.html;
					console.log('CSF Filters: Results updated successfully');
				}

				// Regenerate pagination from response metadata.
				var pagination = catalog.querySelector('.csf-pagination');
				var totalPages = response.data.total_pages || 1;
				var currentPage = response.data.page || 1;

				if (totalPages > 1) {
					var paginationHTML = buildPaginationHTML(currentPage, totalPages);
					if (pagination) {
						pagination.innerHTML = paginationHTML;
						pagination.style.display = '';
					} else {
						// Create pagination container if it didn't exist.
						pagination = document.createElement('div');
						pagination.className = 'csf-pagination';
						pagination.style.cssText = 'margin-top: 32px; display: flex; justify-content: center; gap: 8px; flex-wrap: wrap;';
						pagination.innerHTML = paginationHTML;
						var gridContainer = resultsGrid ? resultsGrid.parentNode : null;
						if (gridContainer) {
							gridContainer.appendChild(pagination);
						}
					}
					// Bind click handlers to new pagination buttons.
					bindPaginationHandlers(pagination, form, loadingOverlay);
				} else if (pagination) {
					pagination.style.display = 'none';
				}

				// Update URL without page reload (for shareable links).
				var urlParams = {
					csf_year: year,
					csf_make: make,
					csf_model: model,
					csf_search: searchQuery
				};
				if (currentPage > 1) {
					urlParams.csf_page = String(currentPage);
				}
				updateURLParams(urlParams);

				// Update results count if present.
				var resultsHeader = catalog.querySelector('.csf-results-header__title');
				if (resultsHeader && response.data.count !== undefined) {
					resultsHeader.textContent = response.data.count + ' ' + (response.data.count === 1 ? csfPartsFilters.resultSingular : csfPartsFilters.resultPlural);
				}
			} else {
				console.error('CSF Filters: Failed to fetch results:', response);
			}

			// Hide loading overlay.
			if (loadingOverlay) {
				loadingOverlay.style.display = 'none';
			}
		})
		.catch(function(error) {
			console.error('CSF Filters: Error fetching filtered results:', error);

			// Hide loading overlay.
			if (loadingOverlay) {
				loadingOverlay.style.display = 'none';
			}
		});
	}

	/**
	 * Build pagination HTML matching server-rendered markup from render.php.
	 *
	 * @param {number} currentPage Current page number.
	 * @param {number} totalPages  Total number of pages.
	 * @return {string} Pagination inner HTML.
	 */
	function buildPaginationHTML(currentPage, totalPages) {
		var html = '';
		var btnStyle = 'padding: 8px 12px; background: var(--global-palette2, #0099CC); color: var(--global-palette9, #FAFAF9); text-decoration: none; border-radius: 4px; font-size: 14px; transition: all 0.3s ease; cursor: pointer; border: none;';
		var navBtnStyle = 'padding: 8px 16px; background: var(--global-palette2, #0099CC); color: var(--global-palette9, #FAFAF9); text-decoration: none; border-radius: 4px; font-size: 14px; transition: all 0.3s ease; cursor: pointer; border: none;';
		var currentStyle = 'padding: 8px 12px; background: transparent; color: var(--global-palette2, #0099CC); border: 2px solid var(--global-palette2, #0099CC); border-radius: 4px; font-size: 14px; font-weight: 600; transition: all 0.3s ease;';
		var ellipsisStyle = 'padding: 8px 4px; color: var(--global-palette3, #5A5A5A);';

		// Previous button.
		if (currentPage > 1) {
			html += '<button type="button" class="csf-pagination-btn csf-pagination-prev" data-page="' + (currentPage - 1) + '" style="' + navBtnStyle + '">';
			html += '\u2190 Previous';
			html += '</button>';
		}

		// Calculate visible page range (2 pages around current).
		var rangeSize = 2;
		var start = Math.max(1, currentPage - rangeSize);
		var end = Math.min(totalPages, currentPage + rangeSize);

		// First page + leading ellipsis.
		if (start > 1) {
			html += '<button type="button" class="csf-pagination-btn" data-page="1" style="' + btnStyle + '">1</button>';
			if (start > 2) {
				html += '<span style="' + ellipsisStyle + '">...</span>';
			}
		}

		// Page number buttons.
		for (var i = start; i <= end; i++) {
			if (i === currentPage) {
				html += '<span class="csf-pagination-btn csf-pagination-current" style="' + currentStyle + '">' + i + '</span>';
			} else {
				html += '<button type="button" class="csf-pagination-btn" data-page="' + i + '" style="' + btnStyle + '">' + i + '</button>';
			}
		}

		// Trailing ellipsis + last page.
		if (end < totalPages) {
			if (end < totalPages - 1) {
				html += '<span style="' + ellipsisStyle + '">...</span>';
			}
			html += '<button type="button" class="csf-pagination-btn" data-page="' + totalPages + '" style="' + btnStyle + '">' + totalPages + '</button>';
		}

		// Next button.
		if (currentPage < totalPages) {
			html += '<button type="button" class="csf-pagination-btn csf-pagination-next" data-page="' + (currentPage + 1) + '" style="' + navBtnStyle + '">';
			html += 'Next \u2192';
			html += '</button>';
		}

		return html;
	}

	/**
	 * Bind click handlers to AJAX pagination buttons.
	 *
	 * @param {HTMLElement}     paginationContainer The pagination wrapper element.
	 * @param {HTMLFormElement} form                The filter form element.
	 * @param {HTMLElement}     loadingOverlay      Loading overlay element.
	 */
	function bindPaginationHandlers(paginationContainer, form, loadingOverlay) {
		var buttons = paginationContainer.querySelectorAll('button[data-page]');
		buttons.forEach(function(btn) {
			btn.addEventListener('click', function(e) {
				e.preventDefault();
				var targetPage = parseInt(btn.getAttribute('data-page'), 10);
				if (targetPage > 0) {
					// Scroll to top of catalog for better UX.
					var catalog = form.closest('.csf-product-catalog');
					if (catalog) {
						catalog.scrollIntoView({ behavior: 'smooth', block: 'start' });
					}
					triggerFilterUpdate(form, loadingOverlay, targetPage);
				}
			});
		});
	}

	/**
	 * Update URL parameters without page reload.
	 */
	function updateURLParams(params) {
		const url = new URL(window.location);

		// Clear existing filter params.
		url.searchParams.delete('csf_year');
		url.searchParams.delete('csf_make');
		url.searchParams.delete('csf_model');
		url.searchParams.delete('csf_search');
		url.searchParams.delete('csf_page');

		// Add new params (only if they have values).
		Object.keys(params).forEach(key => {
			if (params[key]) {
				url.searchParams.set(key, params[key]);
			}
		});

		// Update URL without reload.
		window.history.pushState({}, '', url);
	}

	/**
	 * Fetch makes for a specific year via AJAX.
	 */
	function fetchMakesByYear(year, makeSelect, callback) {
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
			if (callback) callback();
		})
		.catch(error => {
			console.error('CSF Filters: Error fetching makes:', error);
			makeSelect.innerHTML = '<option value="">' + csfPartsFilters.error + '</option>';
			makeSelect.disabled = true;
			if (callback) callback();
		});
	}

	/**
	 * Fetch models for a specific year and make via AJAX.
	 */
	function fetchModelsByYearMake(year, make, modelSelect, callback) {
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
			if (callback) callback();
		})
		.catch(error => {
			console.error('Error fetching models:', error);
			modelSelect.innerHTML = '<option value="">' + csfPartsFilters.error + '</option>';
			modelSelect.disabled = true;
			if (callback) callback();
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
