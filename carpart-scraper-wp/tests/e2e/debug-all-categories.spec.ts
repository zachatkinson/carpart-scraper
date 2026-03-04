import { test } from '@playwright/test';

test('list all category values from catalog', async ({ page }) => {
	// Page through to get all categories.
	const allBadges = new Set<string>();

	for (let p = 1; p <= 5; p++) {
		await page.goto(`https://zachatkinson.com/demos/rad/parts/?csf_page=${p}`);
		await page.waitForLoadState('networkidle');

		const badges = await page.evaluate(() => {
			const els = document.querySelectorAll('.csf-part-card__badge');
			return Array.from(els).map(el => el.textContent?.trim() || '');
		});
		badges.forEach(b => allBadges.add(b));
	}

	console.log('All category values found:', JSON.stringify([...allBadges].sort()));
});
