import { test } from '@playwright/test';

test('debug category values', async ({ page }) => {
	// Check the main parts page to see what category names are used on the badges.
	await page.goto('https://zachatkinson.com/demos/rad/parts/');
	await page.waitForLoadState('networkidle');

	const badges = await page.evaluate(() => {
		const els = document.querySelectorAll('.csf-part-card__badge');
		return Array.from(els).map(el => el.textContent?.trim());
	});
	console.log('Category badges on catalog page:', JSON.stringify([...new Set(badges)]));

	// Check the REST API for categories.
	const response = await page.goto('https://zachatkinson.com/demos/rad/wp-json/csf/v1/categories');
	const text = await page.textContent('body');
	console.log('REST API categories:', text?.substring(0, 500));
});
