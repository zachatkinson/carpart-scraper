import { test } from '@playwright/test';

test('list all categories via search API', async ({ page }) => {
	// Try the AJAX endpoint to get all categories.
	const response = await page.goto('https://zachatkinson.com/demos/rad/wp-json/csf/v1/parts?per_page=1');
	await page.waitForLoadState('networkidle');

	// Try pages with different categories visible.
	const allBadges = new Set<string>();
	const pages = [1, 10, 20, 50, 80, 100, 120, 140];
	for (const p of pages) {
		await page.goto(`https://zachatkinson.com/demos/rad/parts/?csf_page=${p}`);
		await page.waitForLoadState('networkidle');
		const badges = await page.evaluate(() => {
			const els = document.querySelectorAll('.csf-part-card__badge');
			return Array.from(els).map(el => el.textContent?.trim() || '');
		});
		badges.forEach(b => allBadges.add(b));
	}

	console.log('All categories across pages:', JSON.stringify([...allBadges].sort()));
});
