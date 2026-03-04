import { test } from '@playwright/test';

test('debug condensers page', async ({ page }) => {
	await page.goto('https://zachatkinson.com/demos/rad/condensers/');
	await page.waitForLoadState('networkidle');

	// Get the catalog div attributes.
	const catalogDiv = await page.evaluate(() => {
		const el = document.querySelector('[class*="csf-product-catalog"]');
		if (!el) return 'No catalog div found';
		const attrs: Record<string, string> = {};
		for (const attr of el.attributes) {
			attrs[attr.name] = attr.value;
		}
		return attrs;
	});
	console.log('Catalog div attributes:', JSON.stringify(catalogDiv, null, 2));

	// Check for results or no-results message.
	const content = await page.evaluate(() => {
		const results = document.querySelector('.csf-grid-items');
		const noResults = document.querySelector('.csf-no-results');
		const placeholder = document.querySelector('.csf-placeholder');
		const cards = document.querySelectorAll('.csf-part-card');
		return {
			hasGrid: !!results,
			hasNoResults: !!noResults,
			hasPlaceholder: !!placeholder,
			placeholderText: placeholder?.textContent?.trim() || '',
			noResultsText: noResults?.textContent?.trim() || '',
			cardCount: cards.length,
		};
	});
	console.log('Page content:', JSON.stringify(content, null, 2));

	await page.screenshot({ path: '/Users/zach/Desktop/condensers-debug.png', fullPage: true });
});
