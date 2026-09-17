/**
 * Part Finder block - front-end behaviour.
 *
 * Progressive enhancement over a plain GET form:
 *  - Year → Make → Model cascade using the catalog's existing AJAX endpoints.
 *  - Empty fields are disabled on submit so the destination URL stays clean.
 */
(function () {
	'use strict';

	var cfg = window.csfPartFinder || {};

	function setOptions(select, values, placeholder) {
		var html = '<option value="">' + placeholder + '</option>';
		values.forEach(function (value) {
			var v = String(value);
			html += '<option value="' + v.replace(/&/g, '&amp;').replace(/"/g, '&quot;') + '">' + v.replace(/&/g, '&amp;').replace(/</g, '&lt;') + '</option>';
		});
		select.innerHTML = html;
	}

	function request(action, params) {
		var data = new FormData();
		data.append('action', action);
		data.append('nonce', cfg.nonce || '');
		Object.keys(params).forEach(function (k) { data.append(k, params[k]); });
		return fetch(cfg.ajaxUrl, { method: 'POST', body: data, credentials: 'same-origin' }).then(function (r) { return r.json(); });
	}

	function loading(select, on) {
		select.disabled = true;
		if (on) { select.innerHTML = '<option value="">' + (cfg.loading || 'Loading…') + '</option>'; }
	}

	function init(form) {
		var year = form.querySelector('[data-role="year"]');
		var make = form.querySelector('[data-role="make"]');
		var model = form.querySelector('[data-role="model"]');
		var allMakes = make ? Array.prototype.map.call(make.options, function (o) { return o.value; }).filter(Boolean) : [];

		function resetModel() {
			if (!model) { return; }
			setOptions(model, [], cfg.selectModel || 'Model');
			model.disabled = true;
		}

		if (year && make) {
			year.addEventListener('change', function () {
				resetModel();
				if (!year.value) {
					setOptions(make, allMakes, cfg.selectMake || 'Make');
					make.disabled = false;
					return;
				}
				loading(make, true);
				request('csf_get_makes_by_year', { year: year.value }).then(function (res) {
					var makes = res && res.success && res.data && res.data.makes ? res.data.makes : [];
					setOptions(make, makes, makes.length ? (cfg.selectMake || 'Make') : (cfg.none || 'None available'));
					make.disabled = makes.length === 0;
				}).catch(function () {
					setOptions(make, [], cfg.error || 'Could not load options');
				});
			});
		}

		if (make && model) {
			make.addEventListener('change', function () {
				if (!make.value) { resetModel(); return; }
				loading(model, true);
				request('csf_get_models_by_year_make', { year: year && year.value ? year.value : 0, make: make.value }).then(function (res) {
					var models = res && res.success && res.data && res.data.models ? res.data.models : [];
					setOptions(model, models, models.length ? (cfg.selectModel || 'Model') : (cfg.none || 'None available'));
					model.disabled = models.length === 0;
				}).catch(function () {
					setOptions(model, [], cfg.error || 'Could not load options');
				});
			});
		}

		form.addEventListener('submit', function () {
			// Keep the destination URL to the filters the visitor actually chose.
			Array.prototype.forEach.call(form.querySelectorAll('input[name], select[name]'), function (field) {
				if (!field.value) { field.disabled = true; }
			});
		});
	}

	function boot() {
		Array.prototype.forEach.call(document.querySelectorAll('.csf-part-finder__form'), init);
	}

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', boot);
	} else {
		boot();
	}
})();
