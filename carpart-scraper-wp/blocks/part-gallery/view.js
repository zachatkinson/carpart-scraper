/**
 * Part gallery block: swap the main image when a thumbnail is chosen.
 */
(function () {
	'use strict';
	function boot() {
		document.querySelectorAll('.csf-product-gallery').forEach(function (gallery) {
			var main = gallery.querySelector('.csf-main-image');
			gallery.querySelectorAll('.csf-thumb').forEach(function (thumb) {
				thumb.addEventListener('click', function () {
					if (main && thumb.dataset.src) { main.src = thumb.dataset.src; }
					gallery.querySelectorAll('.csf-thumb').forEach(function (t) { t.classList.toggle('active', t === thumb); });
				});
			});
		});
	}
	if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', boot); } else { boot(); }
})();
