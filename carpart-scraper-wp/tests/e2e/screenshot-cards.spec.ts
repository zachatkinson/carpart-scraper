import { test } from '@playwright/test';

test('screenshot catalog cards', async ({ page }) => {
	await page.goto('https://zachatkinson.com/demos/rad/parts/');
	await page.waitForLoadState('networkidle');
	await page.waitForTimeout(2000);
	await page.screenshot({ path: '/Users/zach/Desktop/catalog-cards.png', fullPage: false });

	// Scroll down to see cards better.
	await page.evaluate(() => window.scrollBy(0, 400));
	await page.waitForTimeout(500);
	await page.screenshot({ path: '/Users/zach/Desktop/catalog-cards-scrolled.png', fullPage: false });
});
