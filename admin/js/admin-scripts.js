/**
 * CSF Parts Admin Scripts
 *
 * Enhanced admin functionality for CSF Parts Catalog plugin.
 * Provides validation, error handling, and UX improvements.
 *
 * @package CSF_Parts_Catalog
 * @since   1.0.0
 */

(function($) {
	'use strict';

	/**
	 * Main Admin Object
	 */
	const CSFPartsAdmin = {
		/**
		 * Initialize admin functionality
		 */
		init: function() {
			this.initFileUpload();
			this.initFormValidation();
			this.initTooltips();
			this.initConfirmations();
			this.bindEvents();
		},

		/**
		 * Initialize file upload validation
		 */
		initFileUpload: function() {
			const fileInput = $('#csf-json-file');

			if (fileInput.length) {
				fileInput.on('change', function(e) {
					const file = e.target.files[0];

					if (!file) {
						return;
					}

					// Validate file type
					if (!file.name.endsWith('.json')) {
						CSFPartsAdmin.showError(
							'Invalid file type. Please select a JSON file.'
						);
						fileInput.val('');
						return;
					}

					// Validate file size (50MB max)
					const maxSize = 50 * 1024 * 1024;
					if (file.size > maxSize) {
						CSFPartsAdmin.showError(
							'File too large. Maximum size is 50MB.'
						);
						fileInput.val('');
						return;
					}

					// Show file info
					CSFPartsAdmin.showFileInfo(file);
				});
			}
		},

		/**
		 * Display file information
		 */
		showFileInfo: function(file) {
			const sizeInMB = (file.size / (1024 * 1024)).toFixed(2);
			const info = `
				<div class="notice notice-info inline" style="margin-top: 10px;">
					<p>
						<strong>Selected:</strong> ${file.name} (${sizeInMB} MB)
					</p>
				</div>
			`;

			// Remove existing info
			$('.csf-file-info').remove();

			// Add new info
			$('#csf-upload-form').after('<div class="csf-file-info">' + info + '</div>');
		},

		/**
		 * Initialize form validation
		 */
		initFormValidation: function() {
			// Settings form validation
			$('form.csf-settings-form').on('submit', function(e) {
				let isValid = true;
				const form = $(this);

				// Validate required fields
				form.find('[required]').each(function() {
					if (!$(this).val()) {
						isValid = false;
						$(this).addClass('error');
					} else {
						$(this).removeClass('error');
					}
				});

				if (!isValid) {
					e.preventDefault();
					CSFPartsAdmin.showError('Please fill in all required fields.');
				}
			});
		},

		/**
		 * Initialize tooltips
		 */
		initTooltips: function() {
			// Add tooltips to help icons
			$('.csf-help-icon').each(function() {
				$(this).attr('title', $(this).data('help'));
			});
		},

		/**
		 * Initialize confirmation dialogs
		 */
		initConfirmations: function() {
			// Confirm before clearing import log
			$('.csf-clear-log').on('click', function(e) {
				if (!confirm('Are you sure you want to clear the import log? This cannot be undone.')) {
					e.preventDefault();
				}
			});

			// Confirm before deleting all parts
			$('.csf-delete-all-parts').on('click', function(e) {
				const confirmText = 'Are you sure you want to delete ALL parts? This will permanently remove all CSF parts from your database. This cannot be undone.\n\nType "DELETE" to confirm.';
				const userInput = prompt(confirmText);

				if (userInput !== 'DELETE') {
					e.preventDefault();
					CSFPartsAdmin.showError('Deletion cancelled.');
				}
			});
		},

		/**
		 * Bind additional events
		 */
		bindEvents: function() {
			// Dismiss notices
			$(document).on('click', '.notice-dismiss', function() {
				$(this).closest('.notice').fadeOut();
			});

			// Auto-dismiss success messages after 5 seconds
			setTimeout(function() {
				$('.notice-success.is-dismissible').fadeOut();
			}, 5000);
		},

		/**
		 * Show error message
		 */
		showError: function(message) {
			const errorDiv = `
				<div class="notice notice-error is-dismissible">
					<p><strong>Error:</strong> ${message}</p>
					<button type="button" class="notice-dismiss">
						<span class="screen-reader-text">Dismiss this notice.</span>
					</button>
				</div>
			`;

			// Remove existing errors
			$('.notice-error').remove();

			// Add error to top of page
			$('.wrap h1').after(errorDiv);

			// Scroll to error
			$('html, body').animate({
				scrollTop: $('.notice-error').offset().top - 50
			}, 300);
		},

		/**
		 * Show success message
		 */
		showSuccess: function(message) {
			const successDiv = `
				<div class="notice notice-success is-dismissible">
					<p>${message}</p>
					<button type="button" class="notice-dismiss">
						<span class="screen-reader-text">Dismiss this notice.</span>
					</button>
				</div>
			`;

			// Remove existing success messages
			$('.notice-success').remove();

			// Add success to top of page
			$('.wrap h1').after(successDiv);

			// Auto-dismiss after 5 seconds
			setTimeout(function() {
				$('.notice-success').fadeOut();
			}, 5000);
		},

		/**
		 * Show warning message
		 */
		showWarning: function(message) {
			const warningDiv = `
				<div class="notice notice-warning is-dismissible">
					<p><strong>Warning:</strong> ${message}</p>
					<button type="button" class="notice-dismiss">
						<span class="screen-reader-text">Dismiss this notice.</span>
					</button>
				</div>
			`;

			// Remove existing warnings
			$('.notice-warning').remove();

			// Add warning to top of page
			$('.wrap h1').after(warningDiv);
		},

		/**
		 * Format number with commas
		 */
		formatNumber: function(num) {
			return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
		},

		/**
		 * Format bytes to human-readable size
		 */
		formatBytes: function(bytes, decimals = 2) {
			if (bytes === 0) return '0 Bytes';

			const k = 1024;
			const dm = decimals < 0 ? 0 : decimals;
			const sizes = ['Bytes', 'KB', 'MB', 'GB'];
			const i = Math.floor(Math.log(bytes) / Math.log(k));

			return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
		},

		/**
		 * Sanitize HTML to prevent XSS
		 */
		sanitizeHTML: function(str) {
			const temp = document.createElement('div');
			temp.textContent = str;
			return temp.innerHTML;
		},

		/**
		 * Enhanced AJAX wrapper with better error handling
		 */
		ajax: function(action, data, successCallback, errorCallback) {
			$.ajax({
				url: ajaxurl,
				type: 'POST',
				data: {
					action: action,
					...data
				},
				beforeSend: function() {
					// Show loading indicator
					$('.csf-loading').show();
				},
				success: function(response) {
					$('.csf-loading').hide();

					if (response.success) {
						if (successCallback) {
							successCallback(response.data);
						}
					} else {
						const errorMsg = response.data?.message || 'An unknown error occurred.';
						CSFPartsAdmin.showError(errorMsg);

						if (errorCallback) {
							errorCallback(response.data);
						}
					}
				},
				error: function(xhr, status, error) {
					$('.csf-loading').hide();

					let errorMsg = 'Server error: ';
					if (xhr.responseJSON && xhr.responseJSON.data && xhr.responseJSON.data.message) {
						errorMsg += xhr.responseJSON.data.message;
					} else {
						errorMsg += error || status;
					}

					CSFPartsAdmin.showError(errorMsg);

					if (errorCallback) {
						errorCallback({ message: errorMsg });
					}
				}
			});
		},

		/**
		 * Debounce function for search/filter inputs
		 */
		debounce: function(func, wait) {
			let timeout;
			return function executedFunction(...args) {
				const later = () => {
					clearTimeout(timeout);
					func(...args);
				};
				clearTimeout(timeout);
				timeout = setTimeout(later, wait);
			};
		},

		/**
		 * Copy text to clipboard
		 */
		copyToClipboard: function(text) {
			const temp = $('<textarea>');
			$('body').append(temp);
			temp.val(text).select();
			document.execCommand('copy');
			temp.remove();

			CSFPartsAdmin.showSuccess('Copied to clipboard!');
		},

		/**
		 * Enable/disable form submit button
		 */
		toggleSubmitButton: function(formSelector, enable) {
			const button = $(formSelector).find('button[type="submit"], input[type="submit"]');

			if (enable) {
				button.prop('disabled', false).removeClass('disabled');
			} else {
				button.prop('disabled', true).addClass('disabled');
			}
		},

		/**
		 * Add loading spinner to button
		 */
		addButtonSpinner: function(button) {
			const $button = $(button);
			$button.data('original-text', $button.html());
			$button.html('<span class="spinner is-active" style="float: none; margin: 0;"></span> Processing...');
			$button.prop('disabled', true);
		},

		/**
		 * Remove loading spinner from button
		 */
		removeButtonSpinner: function(button) {
			const $button = $(button);
			const originalText = $button.data('original-text');
			if (originalText) {
				$button.html(originalText);
			}
			$button.prop('disabled', false);
		}
	};

	/**
	 * Import Page Specific Functions
	 */
	const CSFImportPage = {
		/**
		 * Initialize import page
		 */
		init: function() {
			if ($('#csf-import-page').length === 0) {
				return;
			}

			this.bindEvents();
		},

		/**
		 * Bind import page events
		 */
		bindEvents: function() {
			// Preview JSON before import
			$('#csf-preview-btn').on('click', function(e) {
				e.preventDefault();
				CSFImportPage.previewJSON();
			});

			// Add copy buttons to error messages
			$('.csf-error-list li, .csf-warning-list li').each(function() {
				const text = $(this).text();
				const copyBtn = $('<button type="button" class="button button-small" style="margin-left: 10px;">Copy</button>');

				copyBtn.on('click', function() {
					CSFPartsAdmin.copyToClipboard(text);
				});

				$(this).append(copyBtn);
			});
		},

		/**
		 * Preview JSON file before importing
		 */
		previewJSON: function() {
			const fileInput = $('#csf-json-file')[0];

			if (!fileInput.files.length) {
				CSFPartsAdmin.showError('Please select a JSON file first.');
				return;
			}

			const file = fileInput.files[0];
			const reader = new FileReader();

			reader.onload = function(e) {
				try {
					const json = JSON.parse(e.target.result);

					// Display preview modal
					CSFImportPage.showPreviewModal(json);
				} catch (error) {
					CSFPartsAdmin.showError('Invalid JSON file: ' + error.message);
				}
			};

			reader.readAsText(file);
		},

		/**
		 * Show preview modal
		 */
		showPreviewModal: function(json) {
			const parts = json.parts || [];
			const metadata = json.metadata || {};

			const modalContent = `
				<div class="csf-preview-modal">
					<div class="csf-preview-content">
						<h2>JSON Preview</h2>
						<div class="csf-preview-stats">
							<p><strong>Parts Count:</strong> ${parts.length}</p>
							<p><strong>Exported:</strong> ${metadata.exported_at || 'Unknown'}</p>
							<p><strong>Source:</strong> ${metadata.source || 'Unknown'}</p>
						</div>
						<h3>Sample Part (First Item):</h3>
						<pre>${JSON.stringify(parts[0], null, 2)}</pre>
						<button type="button" class="button button-primary csf-close-modal">Close</button>
					</div>
				</div>
			`;

			$('body').append(modalContent);

			$('.csf-close-modal').on('click', function() {
				$('.csf-preview-modal').remove();
			});
		}
	};

	/**
	 * Initialize on document ready
	 */
	$(document).ready(function() {
		CSFPartsAdmin.init();
		CSFImportPage.init();
	});

	// Expose to global scope for inline scripts
	window.CSFPartsAdmin = CSFPartsAdmin;
	window.CSFImportPage = CSFImportPage;

})(jQuery);
