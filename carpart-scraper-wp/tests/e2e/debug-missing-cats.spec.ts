import { test } from '@playwright/test';

test('find missing categories', async ({ page }) => {
	// Search for pressure cap.
	await page.goto('https://zachatkinson.com/demos/rad/parts/?csf_search=pressure+cap');
	await page.waitForLoadState('networkidle');
	let results = await page.evaluate(() => {
		const badges = document.querySelectorAll('.csf-part-card__badge');
		const header = document.querySelector('.csf-results-header__title');
		return {
			total: header?.textContent?.trim() || 'No results',
			categories: [...new Set(Array.from(badges).map(el => el.textContent?.trim()))],
		};
	});
	console.log('Pressure cap search:', JSON.stringify(results));

	// Search for just "cap".
	await page.goto('https://zachatkinson.com/demos/rad/parts/?csf_search=cap');
	await page.waitForLoadState('networkidle');
	results = await page.evaluate(() => {
		const badges = document.querySelectorAll('.csf-part-card__badge');
		const header = document.querySelector('.csf-results-header__title');
		return {
			total: header?.textContent?.trim() || 'No results',
			categories: [...new Set(Array.from(badges).map(el => el.textContent?.trim()))],
		};
	});
	console.log('Cap search:', JSON.stringify(results));

	// Try the exact category name.
	await page.goto('https://zachatkinson.com/demos/rad/parts/?csf_category=Pressure+Cap');
	await page.waitForLoadState('networkidle');
	results = await page.evaluate(() => {
		const badges = document.querySelectorAll('.csf-part-card__badge');
		const header = document.querySelector('.csf-results-header__title');
		return {
			total: header?.textContent?.trim() || 'No results',
			categories: [...new Set(Array.from(badges).map(el => el.textContent?.trim()))],
		};
	});
	console.log('Pressure Cap category filter:', JSON.stringify(results));

	// Try Radiator Cap.
	await page.goto('https://zachatkinson.com/demos/rad/parts/?csf_category=Radiator+Cap');
	await page.waitForLoadState('networkidle');
	results = await page.evaluate(() => {
		const badges = document.querySelectorAll('.csf-part-card__badge');
		const header = document.querySelector('.csf-results-header__title');
		return {
			total: header?.textContent?.trim() || 'No results',
			categories: [...new Set(Array.from(badges).map(el => el.textContent?.trim()))],
		};
	});
	console.log('Radiator Cap category filter:', JSON.stringify(results));
});
