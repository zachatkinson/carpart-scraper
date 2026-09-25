/**
 * Part Finder block - front-end behaviour.
 *
 * Progressive enhancement over a plain GET form:
 *  - Year, Make and Model narrow each other in whichever order the visitor
 *    picks them (Year → Makes, Make → Models and Years, Model → Years).
 *  - A selection is kept whenever it is still valid after narrowing.
 *  - Empty fields are disabled on submit so the destination URL stays clean.
 */
(function () {
	'use strict';

	var cfg = window.csfPartFinder || {};

	function escapeHtml(v) {
		return String(v).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
	}

	// An option is {value, label}: the value is the stored form the query matches on, the label its display name.
	function toOption(item) {
		if (item !== null && typeof item === 'object') {
			return { value: String(item.value), label: item.label ? String(item.label) : String(item.value) };
		}
		return { value: String(item), label: String(item) };
	}

	function setOptions(select, options, placeholder, keep) {
		var html = '<option value="">' + escapeHtml(placeholder) + '</option>';
		options.forEach(function (option) {
			html += '<option value="' + escapeHtml(option.value) + '"' + (option.value === keep ? ' selected' : '') + '>' + escapeHtml(option.label) + '</option>';
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

	function values(res, key) {
		return res && res.success && res.data && Array.isArray(res.data[key]) ? res.data[key].map(toOption) : [];
	}

	function init(form) {
		var year = form.querySelector('[data-role="year"]');
		var make = form.querySelector('[data-role="make"]');
		var model = form.querySelector('[data-role="model"]');
		var optionValues = function (select) {
			return select ? Array.prototype.filter.call(select.options, function (o) { return o.value; }).map(function (o) { return { value: o.value, label: o.textContent }; }) : [];
		};
		var allYears = optionValues(year);
		var allMakes = optionValues(make);
		var labels = { year: cfg.selectYear || 'Year', make: cfg.selectMake || 'Make', model: cfg.selectModel || 'Model' };

		function fill(select, list, role, current) {
			if (!select) { return; }
			// `current` is the value before any "Loading…" placeholder replaced the options.
			var keep = list.some(function (o) { return o.value === current; }) ? current : '';
			setOptions(select, list, list.length ? labels[role] : (cfg.none || 'None available'), keep);
			select.disabled = list.length === 0;
		}

		function loading(select) {
			if (!select) { return; }
			select.disabled = true;
			select.innerHTML = '<option value="">' + escapeHtml(cfg.loading || 'Loading…') + '</option>';
		}

		function failed(select) {
			if (!select) { return; }
			setOptions(select, [], cfg.error || 'Could not load options', '');
			select.disabled = true;
		}

		// Years that fit the current make/model, or every year when no make is chosen.
		function refreshYears() {
			if (!year) { return Promise.resolve(); }
			var current = year.value;
			if (!make || !make.value) { fill(year, allYears, 'year', current); return Promise.resolve(); }
			loading(year);
			return request('csf_get_years_by_make', { make: make.value, model: model && model.value ? model.value : '' })
				.then(function (res) { fill(year, values(res, 'years'), 'year', current); })
				.catch(function () { fill(year, allYears, 'year', current); });

		}

		// Makes that fit the current year, or every make when no year is chosen.
		function refreshMakes() {
			if (!make) { return Promise.resolve(); }
			var current = make.value;
			if (!year || !year.value) { fill(make, allMakes, 'make', current); return Promise.resolve(); }
			loading(make);
			return request('csf_get_makes_by_year', { year: year.value })
				.then(function (res) { fill(make, values(res, 'makes'), 'make', current); })
				.catch(function () { failed(make); });
		}

		// Models for the current make (narrowed by year when one is chosen).
		function refreshModels() {
			if (!model) { return Promise.resolve(); }
			var current = model.value;
			if (!make || !make.value) { fill(model, [], 'model', ''); model.disabled = true; return Promise.resolve(); }
			loading(model);
			return request('csf_get_models_by_year_make', { year: year && year.value ? year.value : 0, make: make.value })
				.then(function (res) { fill(model, values(res, 'models'), 'model', current); })
				.catch(function () { failed(model); });
		}

		if (year) {
			year.addEventListener('change', function () {
				refreshMakes().then(refreshModels);
			});
		}

		if (make) {
			make.addEventListener('change', function () {
				refreshModels().then(refreshYears);
			});
		}

		if (model) {
			model.addEventListener('change', refreshYears);
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
