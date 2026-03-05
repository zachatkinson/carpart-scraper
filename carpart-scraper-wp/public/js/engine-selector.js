/**
 * Engine Selector - Dynamic fitment confirmation
 *
 * Updates fitment badges from "Possible Match" to "Your Vehicle" when user
 * selects an engine that matches the part's compatibility.
 */

(function() {
	'use strict';

	// Wait for DOM to be ready
	document.addEventListener('DOMContentLoaded', function() {
		const engineDropdown = document.getElementById('csf-engine-variant');
		if (!engineDropdown) {
			return; // No dropdown on this page
		}

		// Get the user's YMM from the page
		const vehicleBox = document.querySelector('.csf-your-vehicle-box');
		if (!vehicleBox) {
			return;
		}

		// Extract YMM from the box (format: "YYYY Make Model")
		const ymmText = vehicleBox.querySelector('.your-vehicle-ymm');
		if (!ymmText) {
			return;
		}

		const ymm = ymmText.textContent.trim().split(' ');
		const userYear = ymm[0];
		const userMake = ymm[1];
		const userModel = ymm.slice(2).join(' ');

		console.log('Engine Selector initialized:', { userYear, userMake, userModel });

		/**
		 * Helper function to create or update a badge
		 */
		function createOrUpdateBadge(card, text, className) {
			let badge = card.querySelector('.fitment-match-badge');

			if (!badge) {
				// Create new badge
				badge = document.createElement('span');
				badge.className = 'fitment-match-badge';

				// Insert at the beginning of the card header
				const cardHeader = card.querySelector('.fitment-card-header');
				if (cardHeader) {
					cardHeader.insertBefore(badge, cardHeader.firstChild);
				}
			}

			// Update badge
			badge.textContent = text;
			badge.className = 'fitment-match-badge ' + className;
			badge.style.transition = 'all 0.3s ease';

			return badge;
		}

		// Listen for engine selection
		engineDropdown.addEventListener('change', function() {
			const selectedEngine = this.value;
			console.log('Engine selected:', selectedEngine);

			// Find all fitment cards
			const fitmentCards = document.querySelectorAll('.csf-fitment-card');

			// Reset all cards - remove highlighting
			fitmentCards.forEach(function(card) {
				card.classList.remove('csf-fitment-highlighted');
				// Remove any existing confirmation messages
				const existing = card.querySelector('.engine-confirmation');
				if (existing) {
					existing.remove();
				}
			});

			// Update badges based on engine selection
			fitmentCards.forEach(function(card) {
				// Check if this card matches user's YMM
				const cardMake = card.querySelector('.fitment-make')?.textContent.trim();
				const cardModel = card.querySelector('.fitment-model')?.textContent.trim();

				if (cardMake !== userMake || cardModel !== userModel) {
					// Not the user's vehicle - remove any badge
					const badge = card.querySelector('.fitment-match-badge');
					if (badge) {
						badge.remove();
					}
					return;
				}

				// Check years match
				const yearsText = card.querySelector('.fitment-years')?.textContent.trim();
				if (!yearsText || !yearsText.includes(userYear)) {
					// User's year not in range - remove any badge
					const badge = card.querySelector('.fitment-match-badge');
					if (badge) {
						badge.remove();
					}
					return;
				}

				// This card matches user's make, model, and year range
				// Get all engine cells in this card's fitment table
				const engineCells = card.querySelectorAll('.fitment-engine');
				let engineMatches = false;

				// If no engine selected or "Standard / All Engines"
				if (!selectedEngine || selectedEngine === '') {
					// Check if this is a universal part (no engine cells or empty cells)
					const hasEngines = Array.from(engineCells).some(cell => {
						const text = cell.textContent.trim();
						return text !== '' && text !== '—';
					});

					if (!hasEngines) {
						// Universal part - this is confirmed
						engineMatches = true;
					} else {
						// Has engines but none selected - show as "Possible Match"
						createOrUpdateBadge(card, 'Possible Match', 'fitment-possible-match');
						card.classList.add('csf-fitment-highlighted');
						return;
					}
				} else {
					// Check if selected engine matches any cell in this card
					engineCells.forEach(function(cell) {
						const cellText = cell.textContent.trim();
						if (cellText && cellText !== '—' && cellText.toLowerCase() === selectedEngine.toLowerCase()) {
							engineMatches = true;
						}
					});
				}

				if (engineMatches) {
					// Exact match - show as "Your Vehicle"
					createOrUpdateBadge(card, 'Your Vehicle', 'badge-confirmed');
					card.classList.add('csf-fitment-highlighted');

					// Show checkmark briefly
					showConfirmation(card);
				} else {
					// Make/model/year match but wrong engine - remove badge (goes to alphabetical)
					const badge = card.querySelector('.fitment-match-badge');
					if (badge) {
						badge.remove();
					}
				}
			});

			// Update the notice box
			updateNoticeBox(selectedEngine);
		});

		/**
		 * Show visual confirmation when engine matches
		 */
		function showConfirmation(card) {
			// Remove existing confirmation if any
			const existing = card.querySelector('.engine-confirmation');
			if (existing) {
				existing.remove();
			}

			// Create checkmark element
			const confirmation = document.createElement('div');
			confirmation.className = 'engine-confirmation';
			confirmation.innerHTML = `
				<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
					<polyline points="20 6 9 17 4 12"></polyline>
				</svg>
				<span>Confirmed fit for your engine</span>
			`;

			// Insert after fitment badges
			const badgesContainer = card.querySelector('.fitment-badges');
			if (badgesContainer) {
				badgesContainer.insertAdjacentElement('afterend', confirmation);
			}

			// Fade in
			setTimeout(() => confirmation.classList.add('visible'), 10);
		}

		/**
		 * Update the engine notice box with confirmation
		 */
		function updateNoticeBox(selectedEngine) {
			const noticeBox = document.querySelector('.engine-notice');
			if (!noticeBox) {
				return;
			}

			const svg = noticeBox.querySelector('svg');
			const strong = noticeBox.querySelector('strong');
			const span = noticeBox.querySelector('span');

			if (!selectedEngine || selectedEngine === '') {
				// Revert to original state
				noticeBox.classList.remove('engine-confirmed');
				if (svg) {
					svg.innerHTML = '<circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line>';
				}
				if (strong) {
					strong.textContent = 'Please select your vehicle\'s engine.';
				}
				if (span) {
					span.textContent = 'Unsure? Contact your local dealer or distributor to verify this part fits your specific vehicle configuration.';
				}
			} else {
				// Update to confirmed state
				noticeBox.classList.add('engine-confirmed');
				if (svg) {
					svg.innerHTML = '<polyline points="20 6 9 17 4 12" stroke-width="2"></polyline>';
				}
				if (strong) {
					strong.textContent = 'Engine confirmed!';
				}
				if (span) {
					span.textContent = 'This part is confirmed to fit your ' + selectedEngine + ' engine.';
				}
			}
		}
	});
})();
