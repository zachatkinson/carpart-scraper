import { test } from '@playwright/test';

test('find uncategorized or unusual parts', async ({ page }) => {
	// Sample a bunch of pages and look for parts without badges or unusual badges.
	const allCategories = new Map<string, number>();
	let noBadgeCount = 0;

	for (let p = 1; p <= 144; p++) {
		await page.goto(`https://zachatkinson.com/demos/rad/parts/?csf_page=${p}`);
		await page.waitForLoadState('networkidle');
		const results = await page.evaluate(() => {
			const cards = document.querySelectorAll('.csf-part-card');
			const data: { title: string; badge: string }[] = [];
			cards.forEach(card => {
				const title = card.querySelector('.csf-part-card__title')?.textContent?.trim() || '';
				const badge = card.querySelector('.csf-part-card__badge')?.textContent?.trim() || '';
				data.push({ title, badge });
			});
			return data;
		});
		for (const r of results) {
			if (!r.badge) {
				noBadgeCount++;
				console.log(`NO BADGE on page ${p}: ${r.title}`);
			} else {
				allCategories.set(r.badge, (allCategories.get(r.badge) || 0) + 1);
			}
		}
		if (results.length === 0) break;
	}

	console.log('\n=== FINAL CATEGORY COUNTS ===');
	const sorted = [...allCategories.entries()].sort((a, b) => b[1] - a[1]);
	let total = 0;
	for (const [cat, count] of sorted) {
		console.log(`${cat}: ${count}`);
		total += count;
	}
	console.log(`Parts with no badge: ${noBadgeCount}`);
	console.log(`Grand total: ${total + noBadgeCount}`);
});
