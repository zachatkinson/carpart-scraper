import { test } from '@playwright/test';

test('check oil cooler categories', async ({ page }) => {
	await page.goto('https://zachatkinson.com/demos/rad/parts/?csf_search=oil+cooler');
	await page.waitForLoadState('networkidle');

	const results = await page.evaluate(() => {
		const badges = document.querySelectorAll('.csf-part-card__badge');
		const header = document.querySelector('.csf-results-header__title');
		const cats: Record<string, number> = {};
		badges.forEach(el => {
			const t = el.textContent?.trim() || '';
			cats[t] = (cats[t] || 0) + 1;
		});
		return {
			total: header?.textContent?.trim() || 'none',
			categoryCounts: cats,
		};
	});
	console.log('Oil cooler search:', JSON.stringify(results, null, 2));
});
