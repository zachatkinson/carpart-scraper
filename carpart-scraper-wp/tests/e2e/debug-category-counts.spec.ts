import { test } from '@playwright/test';

test('count parts per category', async ({ page }) => {
	const categories = [
		'A/C Condenser',
		'Radiator',
		'Intercooler',
		'Automatic Transmission Oil Cooler',
		'Engine Oil Cooler',
		'Power Steering Cooler',
		'Drive Motor Inverter Cooler',
	];

	for (const cat of categories) {
		await page.goto(`https://zachatkinson.com/demos/rad/parts/?csf_category=${encodeURIComponent(cat)}`);
		await page.waitForLoadState('networkidle');
		const total = await page.evaluate(() => {
			const header = document.querySelector('.csf-results-header__title');
			return header?.textContent?.trim() || 'No results';
		});
		console.log(`${cat}: ${total}`);
	}
});
