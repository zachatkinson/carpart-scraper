import { test } from '@playwright/test';

test('get exact total count and find all categories', async ({ page }) => {
	// Get total from page 1.
	await page.goto('https://zachatkinson.com/demos/rad/parts/');
	await page.waitForLoadState('networkidle');
	const total = await page.evaluate(() => {
		const header = document.querySelector('.csf-results-header__title');
		return header?.textContent?.trim() || 'none';
	});
	console.log('Total parts:', total);

	// Now check last few pages to find any stragglers.
	for (const p of [140, 141, 142, 143, 144]) {
		await page.goto(`https://zachatkinson.com/demos/rad/parts/?csf_page=${p}`);
		await page.waitForLoadState('networkidle');
		const results = await page.evaluate(() => {
			const badges = document.querySelectorAll('.csf-part-card__badge');
			const cards = document.querySelectorAll('.csf-part-card');
			const header = document.querySelector('.csf-results-header__title');
			return {
				total: header?.textContent?.trim() || 'none',
				cardCount: cards.length,
				categories: [...new Set(Array.from(badges).map(el => el.textContent?.trim()))],
			};
		});
		console.log(`Page ${p}:`, JSON.stringify(results));
	}
});
