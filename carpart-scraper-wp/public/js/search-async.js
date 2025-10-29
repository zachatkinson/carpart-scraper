/**
 * CSF Async Search Component
 *
 * Provides real-time part search using REST API endpoints.
 * Features debounced search, vehicle filtering, and dynamic result rendering.
 *
 * @package CSF_Parts_Catalog
 * @since   2.0.0
 */

class CSFAsyncSearch {
	/**
	 * Constructor
	 *
	 * @param {string} containerSelector - CSS selector for search container
	 * @param {Object} options - Configuration options
	 */
	constructor(containerSelector, options = {}) {
		this.container = document.querySelector(containerSelector);
		if (!this.container) {
			console.error(`CSF Search: Container "${containerSelector}" not found`);
			return;
		}

		// Configuration
		this.config = {
			restUrl: options.restUrl || (window.csfPartsData && window.csfPartsData.restUrl) || '/wp-json/csf/v1/',
			debounceDelay: options.debounceDelay || 300,
			minSearchLength: options.minSearchLength || 2,
			perPage: options.perPage || 20,
			showFilters: options.showFilters !== false,
			...options
		};

		// State
		this.state = {
			searchQuery: '',
			category: '',
			make: '',
			model: '',
			year: '',
			page: 1,
			isLoading: false,
			results: [],
			total: 0,
			error: null
		};

		// Cache for filter data
		this.cache = {
			makes: null,
			models: {},
			years: null,
			categories: null
		};

		// Debounce timer
		this.debounceTimer = null;

		// Initialize
		this.init();
	}

	/**
	 * Initialize component
	 */
	async init() {
		this.render();
		this.attachEventListeners();

		// Load filter data if filters are enabled
		if (this.config.showFilters) {
			await this.loadFilterData();
		}

		// Always perform initial search to show all parts
		this.performSearch();
	}

	/**
	 * Render component structure
	 */
	render() {
		this.container.innerHTML = `
			<div class="csf-search">
				<div class="csf-search__header">
					<div class="csf-search__input-wrapper">
						<input
							type="text"
							class="csf-search__input"
							placeholder="Search parts by name or SKU..."
							value="${this.state.searchQuery}"
							aria-label="Search parts"
						/>
						<span class="csf-search__input-icon">
							<svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
								<path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd"/>
							</svg>
						</span>
					</div>
					${this.config.showFilters ? this.renderFilters() : ''}
				</div>
				<div class="csf-search__results" role="region" aria-live="polite">
					${this.renderResults()}
				</div>
			</div>
		`;
	}

	/**
	 * Render filter controls
	 *
	 * @return {string} Filter HTML
	 */
	renderFilters() {
		return `
			<div class="csf-search__filters">
				<select class="csf-search__filter" data-filter="category" aria-label="Filter by category">
					<option value="">All Categories</option>
				</select>
				<select class="csf-search__filter" data-filter="make" aria-label="Filter by vehicle make">
					<option value="">All Makes</option>
				</select>
				<select class="csf-search__filter" data-filter="model" aria-label="Filter by vehicle model" ${!this.state.make ? 'disabled' : ''}>
					<option value="">All Models</option>
				</select>
				<select class="csf-search__filter" data-filter="year" aria-label="Filter by vehicle year">
					<option value="">All Years</option>
				</select>
				<button class="csf-search__clear-filters" type="button" ${this.hasActiveFilters() ? '' : 'disabled'}>
					Clear Filters
				</button>
			</div>
		`;
	}

	/**
	 * Render search results
	 *
	 * @return {string} Results HTML
	 */
	renderResults() {
		if (this.state.isLoading) {
			return this.renderLoadingState();
		}

		if (this.state.error) {
			return this.renderErrorState();
		}

		if (this.state.results.length === 0) {
			return this.renderEmptyState();
		}

		return `
			<div class="csf-search__results-header">
				<p class="csf-search__results-count">
					Found ${this.state.total} ${this.state.total === 1 ? 'part' : 'parts'}
				</p>
			</div>
			<div class="csf-search__grid">
				${this.state.results.map(part => this.renderPartCard(part)).join('')}
			</div>
			${this.renderPagination()}
		`;
	}

	/**
	 * Render loading state
	 *
	 * @return {string} Loading HTML
	 */
	renderLoadingState() {
		return `
			<div class="csf-search__loading">
				<div class="csf-search__spinner" role="status">
					<span class="csf-search__sr-only">Loading...</span>
				</div>
				<p>Searching parts...</p>
			</div>
		`;
	}

	/**
	 * Render error state
	 *
	 * @return {string} Error HTML
	 */
	renderErrorState() {
		return `
			<div class="csf-search__error">
				<svg width="48" height="48" viewBox="0 0 20 20" fill="currentColor">
					<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
				</svg>
				<h3>Search Error</h3>
				<p>${this.escapeHtml(this.state.error)}</p>
				<button class="csf-search__retry" type="button">Try Again</button>
			</div>
		`;
	}

	/**
	 * Render empty state
	 *
	 * @return {string} Empty HTML
	 */
	renderEmptyState() {
		const hasQuery = this.state.searchQuery || this.hasActiveFilters();
		return `
			<div class="csf-search__empty">
				<svg width="64" height="64" viewBox="0 0 20 20" fill="currentColor" opacity="0.3">
					<path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd"/>
				</svg>
				<h3>${hasQuery ? 'No parts found' : 'Start searching'}</h3>
				<p>${hasQuery ? 'Try adjusting your search or filters' : 'Enter a search term to find parts'}</p>
			</div>
		`;
	}

	/**
	 * Render part card
	 *
	 * @param {Object} part - Part data
	 * @return {string} Card HTML
	 */
	renderPartCard(part) {
		const price = part.price ? `$${parseFloat(part.price).toFixed(2)}` : 'Contact for price';
		const stockClass = part.in_stock ? 'in-stock' : 'out-of-stock';
		const stockText = part.in_stock ? 'In Stock' : 'Out of Stock';

		return `
			<article class="csf-part-card">
				<a href="${this.escapeHtml(part.link)}" class="csf-part-card__link">
					${part.image ? `
						<div class="csf-part-card__image">
							<img src="${this.escapeHtml(part.image)}" alt="${this.escapeHtml(part.name)}" loading="lazy" />
						</div>
					` : `
						<div class="csf-part-card__image csf-part-card__image--placeholder">
							<svg width="48" height="48" viewBox="0 0 20 20" fill="currentColor" opacity="0.2">
								<path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd"/>
							</svg>
						</div>
					`}
					<div class="csf-part-card__content">
						<p class="csf-part-card__category">${this.escapeHtml(part.category)}</p>
						<h3 class="csf-part-card__title">${this.escapeHtml(part.name)}</h3>
						<p class="csf-part-card__sku">SKU: ${this.escapeHtml(part.sku)}</p>
						${part.manufacturer ? `<p class="csf-part-card__manufacturer">${this.escapeHtml(part.manufacturer)}</p>` : ''}
						<div class="csf-part-card__footer">
							<span class="csf-part-card__price">${price}</span>
							<span class="csf-part-card__stock csf-part-card__stock--${stockClass}">${stockText}</span>
						</div>
					</div>
				</a>
			</article>
		`;
	}

	/**
	 * Render pagination
	 *
	 * @return {string} Pagination HTML
	 */
	renderPagination() {
		const totalPages = Math.ceil(this.state.total / this.config.perPage);
		if (totalPages <= 1) return '';

		const currentPage = this.state.page;
		const maxButtons = 5;
		let startPage = Math.max(1, currentPage - Math.floor(maxButtons / 2));
		let endPage = Math.min(totalPages, startPage + maxButtons - 1);

		if (endPage - startPage < maxButtons - 1) {
			startPage = Math.max(1, endPage - maxButtons + 1);
		}

		let buttons = '';

		// Previous button
		buttons += `
			<button
				class="csf-pagination__button"
				data-page="${currentPage - 1}"
				${currentPage === 1 ? 'disabled' : ''}
				aria-label="Previous page"
			>
				&laquo;
			</button>
		`;

		// First page
		if (startPage > 1) {
			buttons += `<button class="csf-pagination__button" data-page="1">1</button>`;
			if (startPage > 2) {
				buttons += `<span class="csf-pagination__ellipsis">...</span>`;
			}
		}

		// Page numbers
		for (let i = startPage; i <= endPage; i++) {
			buttons += `
				<button
					class="csf-pagination__button ${i === currentPage ? 'csf-pagination__button--active' : ''}"
					data-page="${i}"
					${i === currentPage ? 'aria-current="page"' : ''}
				>
					${i}
				</button>
			`;
		}

		// Last page
		if (endPage < totalPages) {
			if (endPage < totalPages - 1) {
				buttons += `<span class="csf-pagination__ellipsis">...</span>`;
			}
			buttons += `<button class="csf-pagination__button" data-page="${totalPages}">${totalPages}</button>`;
		}

		// Next button
		buttons += `
			<button
				class="csf-pagination__button"
				data-page="${currentPage + 1}"
				${currentPage === totalPages ? 'disabled' : ''}
				aria-label="Next page"
			>
				&raquo;
			</button>
		`;

		return `
			<nav class="csf-pagination" role="navigation" aria-label="Pagination">
				${buttons}
			</nav>
		`;
	}

	/**
	 * Attach event listeners
	 */
	attachEventListeners() {
		// Search input
		const searchInput = this.container.querySelector('.csf-search__input');
		if (searchInput) {
			searchInput.addEventListener('input', (e) => {
				this.handleSearchInput(e.target.value);
			});
		}

		// Filter dropdowns
		this.container.querySelectorAll('.csf-search__filter').forEach(filter => {
			filter.addEventListener('change', (e) => {
				this.handleFilterChange(e.target.dataset.filter, e.target.value);
			});
		});

		// Clear filters button
		const clearButton = this.container.querySelector('.csf-search__clear-filters');
		if (clearButton) {
			clearButton.addEventListener('click', () => {
				this.clearFilters();
			});
		}

		// Delegation for dynamic elements
		this.container.addEventListener('click', (e) => {
			// Pagination buttons
			if (e.target.matches('.csf-pagination__button')) {
				const page = parseInt(e.target.dataset.page);
				if (!isNaN(page)) {
					this.changePage(page);
				}
			}

			// Retry button
			if (e.target.matches('.csf-search__retry')) {
				this.performSearch();
			}
		});
	}

	/**
	 * Handle search input
	 *
	 * @param {string} query - Search query
	 */
	handleSearchInput(query) {
		this.state.searchQuery = query;

		// Clear previous debounce timer
		if (this.debounceTimer) {
			clearTimeout(this.debounceTimer);
		}

		// Debounce search
		if (query.length >= this.config.minSearchLength || query.length === 0) {
			this.debounceTimer = setTimeout(() => {
				this.state.page = 1; // Reset to first page
				this.performSearch();
			}, this.config.debounceDelay);
		}
	}

	/**
	 * Handle filter change
	 *
	 * @param {string} filterType - Filter type (category, make, model, year)
	 * @param {string} value - Filter value
	 */
	async handleFilterChange(filterType, value) {
		this.state[filterType] = value;
		this.state.page = 1; // Reset to first page

		// If make changed, reload models
		if (filterType === 'make') {
			this.state.model = ''; // Reset model
			if (value) {
				await this.loadModels(value);
			}
			// Update model dropdown
			this.updateModelDropdown();
		}

		this.performSearch();
	}

	/**
	 * Clear all filters
	 */
	clearFilters() {
		this.state.category = '';
		this.state.make = '';
		this.state.model = '';
		this.state.year = '';
		this.state.page = 1;

		// Reset filter dropdowns
		this.container.querySelectorAll('.csf-search__filter').forEach(filter => {
			filter.value = '';
		});

		this.performSearch();
	}

	/**
	 * Change page
	 *
	 * @param {number} page - Page number
	 */
	changePage(page) {
		this.state.page = page;
		this.performSearch();

		// Scroll to top of results
		this.container.querySelector('.csf-search__results').scrollIntoView({
			behavior: 'smooth',
			block: 'start'
		});
	}

	/**
	 * Perform search
	 */
	async performSearch() {
		this.state.isLoading = true;
		this.state.error = null;
		this.updateResults();

		try {
			const params = new URLSearchParams({
				per_page: this.config.perPage,
				page: this.state.page
			});

			if (this.state.searchQuery) {
				params.append('search', this.state.searchQuery);
			}
			if (this.state.category) {
				params.append('category', this.state.category);
			}
			if (this.state.make) {
				params.append('make', this.state.make);
			}
			if (this.state.model) {
				params.append('model', this.state.model);
			}
			if (this.state.year) {
				params.append('year', this.state.year);
			}

			const response = await fetch(`${this.config.restUrl}parts?${params}`);

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			const data = await response.json();

			this.state.results = data.parts || [];
			this.state.total = data.total || 0;
			this.state.isLoading = false;

			this.updateResults();
		} catch (error) {
			console.error('CSF Search error:', error);
			this.state.error = 'Failed to load parts. Please try again.';
			this.state.isLoading = false;
			this.updateResults();
		}
	}

	/**
	 * Load filter data
	 */
	async loadFilterData() {
		await Promise.all([
			this.loadMakes(),
			this.loadYears(),
			this.loadCategories()
		]);
	}

	/**
	 * Load vehicle makes
	 */
	async loadMakes() {
		if (this.cache.makes) return;

		try {
			const response = await fetch(`${this.config.restUrl}vehicles/makes`);
			if (!response.ok) throw new Error('Failed to load makes');

			const makes = await response.json();
			this.cache.makes = makes;

			// Populate dropdown
			const makeSelect = this.container.querySelector('[data-filter="make"]');
			if (makeSelect) {
				makes.forEach(make => {
					const option = document.createElement('option');
					option.value = make.name;
					option.textContent = `${make.name} (${make.count})`;
					makeSelect.appendChild(option);
				});
			}
		} catch (error) {
			console.error('Failed to load makes:', error);
		}
	}

	/**
	 * Load vehicle models
	 *
	 * @param {string} make - Vehicle make
	 */
	async loadModels(make) {
		if (this.cache.models[make]) return;

		try {
			const response = await fetch(`${this.config.restUrl}vehicles/models?make=${encodeURIComponent(make)}`);
			if (!response.ok) throw new Error('Failed to load models');

			const models = await response.json();
			this.cache.models[make] = models;
		} catch (error) {
			console.error('Failed to load models:', error);
		}
	}

	/**
	 * Update model dropdown
	 */
	updateModelDropdown() {
		const modelSelect = this.container.querySelector('[data-filter="model"]');
		if (!modelSelect) return;

		// Clear existing options
		modelSelect.innerHTML = '<option value="">All Models</option>';

		// Enable/disable based on make selection
		modelSelect.disabled = !this.state.make;

		if (this.state.make && this.cache.models[this.state.make]) {
			this.cache.models[this.state.make].forEach(model => {
				const option = document.createElement('option');
				option.value = model.name;
				option.textContent = model.name;
				modelSelect.appendChild(option);
			});
		}
	}

	/**
	 * Load vehicle years
	 */
	async loadYears() {
		if (this.cache.years) return;

		try {
			const response = await fetch(`${this.config.restUrl}vehicles/years`);
			if (!response.ok) throw new Error('Failed to load years');

			const years = await response.json();
			this.cache.years = years;

			// Populate dropdown (most recent first)
			const yearSelect = this.container.querySelector('[data-filter="year"]');
			if (yearSelect) {
				years.reverse().forEach(item => {
					const option = document.createElement('option');
					option.value = item.year;
					option.textContent = `${item.year} (${item.count})`;
					yearSelect.appendChild(option);
				});
			}
		} catch (error) {
			console.error('Failed to load years:', error);
		}
	}

	/**
	 * Load categories
	 */
	async loadCategories() {
		if (this.cache.categories) return;

		try {
			// Get categories from initial parts query
			const response = await fetch(`${this.config.restUrl}parts?per_page=100`);
			if (!response.ok) throw new Error('Failed to load categories');

			const data = await response.json();
			const categories = [...new Set(data.parts.map(part => part.category))].sort();
			this.cache.categories = categories;

			// Populate dropdown
			const categorySelect = this.container.querySelector('[data-filter="category"]');
			if (categorySelect) {
				categories.forEach(category => {
					const option = document.createElement('option');
					option.value = category;
					option.textContent = category;
					categorySelect.appendChild(option);
				});
			}
		} catch (error) {
			console.error('Failed to load categories:', error);
		}
	}

	/**
	 * Update results display
	 */
	updateResults() {
		const resultsContainer = this.container.querySelector('.csf-search__results');
		if (resultsContainer) {
			resultsContainer.innerHTML = this.renderResults();
		}

		// Update clear filters button state
		const clearButton = this.container.querySelector('.csf-search__clear-filters');
		if (clearButton) {
			clearButton.disabled = !this.hasActiveFilters();
		}
	}

	/**
	 * Check if any filters are active
	 *
	 * @return {boolean} True if filters are active
	 */
	hasActiveFilters() {
		return !!(this.state.category || this.state.make || this.state.model || this.state.year);
	}

	/**
	 * Escape HTML to prevent XSS
	 *
	 * @param {string} text - Text to escape
	 * @return {string} Escaped text
	 */
	escapeHtml(text) {
		const div = document.createElement('div');
		div.textContent = text;
		return div.innerHTML;
	}
}

// Initialize on DOM ready
if (document.readyState === 'loading') {
	document.addEventListener('DOMContentLoaded', initCSFSearch);
} else {
	initCSFSearch();
}

/**
 * Initialize CSF search instances
 */
function initCSFSearch() {
	// Look for search containers
	const containers = document.querySelectorAll('[data-csf-search]');

	containers.forEach(container => {
		const options = {
			...container.dataset
		};

		new CSFAsyncSearch(`#${container.id}`, options);
	});
}

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
	module.exports = CSFAsyncSearch;
}
