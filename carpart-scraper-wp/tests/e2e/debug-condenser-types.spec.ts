import { test } from '@playwright/test';

test('check all distinct categories in database', async ({ page }) => {
	// Get all categories by sampling many pages.
	const allCategories = new Set<string>();
	const pagesToCheck = [1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 143];

	for (const p of pagesToCheck) {
		await page.goto(`https://zachatkinson.com/demos/rad/parts/?csf_page=${p}`);
		await page.waitForLoadState('networkidle');
		const badges = await page.evaluate(() => {
			const els = document.querySelectorAll('.csf-part-card__badge');
			return Array.from(els).map(el => el.textContent?.trim() || '');
		});
		badges.forEach(b => allCategories.add(b));
		if (badges.length === 0) break; // Past last page.
	}

	console.log('ALL distinct categories in database:', JSON.stringify([...allCategories].sort()));
	console.log('Total unique categories:', allCategories.size);
});
