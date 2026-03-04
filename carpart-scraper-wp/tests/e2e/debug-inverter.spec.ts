import { test } from '@playwright/test';

test('check for inverter cooler categories', async ({ page }) => {
	// Search for "inverter" in the catalog.
	await page.goto('https://zachatkinson.com/demos/rad/parts/?csf_search=inverter');
	await page.waitForLoadState('networkidle');

	const results = await page.evaluate(() => {
		const badges = document.querySelectorAll('.csf-part-card__badge');
		const titles = document.querySelectorAll('.csf-part-card__title');
		const header = document.querySelector('.csf-results-header__title');
		return {
			total: header?.textContent?.trim() || 'none',
			categories: [...new Set(Array.from(badges).map(el => el.textContent?.trim()))],
			sampleTitles: Array.from(titles).slice(0, 5).map(el => el.textContent?.trim()),
		};
	});
	console.log('Inverter search results:', JSON.stringify(results, null, 2));
});
