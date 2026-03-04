/**
 * v1.2.4 Fix Verification Tests
 *
 * Tests against the live site at https://zachatkinson.com/demos/rad/
 *
 * 1. Part card links resolve (no 404) — rewrite rules fix
 * 2. Images load correctly — uploads directory resolution
 * 3. Dark mode CSS tokens are defined — color system
 */

import { test, expect } from '@playwright/test';

// Full URL to avoid any baseURL path resolution issues.
const CATALOG_URL = 'https://zachatkinson.com/demos/rad/parts/';

test.describe('Part card navigation (404 fix)', () => {
	test('catalog page loads with part cards', async ({ page }) => {
		await page.goto(CATALOG_URL);
		await page.waitForLoadState('networkidle');

		const cards = page.locator('.csf-part-card');
		await expect(cards.first()).toBeVisible({ timeout: 10000 });
		const count = await cards.count();
		expect(count).toBeGreaterThan(0);
	});

	test('clicking a part card does not 404', async ({ page }) => {
		await page.goto(CATALOG_URL);
		await page.waitForLoadState('networkidle');

		const firstCardLink = page.locator('.csf-part-card__link').first();
		await expect(firstCardLink).toBeVisible({ timeout: 10000 });

		const href = await firstCardLink.getAttribute('href');
		expect(href).toBeTruthy();
		expect(href).toContain('/parts/csf');

		// Navigate to the part page.
		await firstCardLink.click();
		await page.waitForLoadState('networkidle');

		// Should NOT be a 404 page.
		const is404 = await page.locator('.error-404, .not-found, .page-not-found').count();
		expect(is404).toBe(0);

		const title = await page.title();
		expect(title.toLowerCase()).not.toContain('not found');
		expect(title.toLowerCase()).not.toContain('page not found');
	});

	test('canonical part URL /parts/csf{sku} returns 200', async ({ page }) => {
		await page.goto(CATALOG_URL);
		await page.waitForLoadState('networkidle');

		const firstCardLink = page.locator('.csf-part-card__link').first();
		await expect(firstCardLink).toBeVisible({ timeout: 10000 });
		const href = await firstCardLink.getAttribute('href');

		// Navigate directly to the URL.
		const response = await page.goto(href!);
		expect(response).not.toBeNull();
		expect(response!.status()).toBe(200);
	});
});

test.describe('Image loading', () => {
	test('catalog page image requests tracked', async ({ page }) => {
		const brokenImages: string[] = [];

		page.on('response', (response) => {
			if (
				response.url().match(/\.(avif|webp|jpg|png|svg)/) &&
				response.status() >= 400
			) {
				brokenImages.push(`${response.status()} ${response.url()}`);
			}
		});

		await page.goto(CATALOG_URL);
		await page.waitForLoadState('networkidle');
		await page.waitForTimeout(3000);

		// Log broken images for diagnostics (test always passes to report).
		if (brokenImages.length > 0) {
			console.log('Broken images on catalog page:', brokenImages);
		}
		expect(brokenImages).toEqual([]);
	});

	test('part detail page image requests tracked', async ({ page }) => {
		const brokenImages: string[] = [];

		page.on('response', (response) => {
			if (
				response.url().match(/\.(avif|webp|jpg|png|svg)/) &&
				response.status() >= 400
			) {
				brokenImages.push(`${response.status()} ${response.url()}`);
			}
		});

		await page.goto(CATALOG_URL);
		await page.waitForLoadState('networkidle');

		const firstCardLink = page.locator('.csf-part-card__link').first();
		await expect(firstCardLink).toBeVisible({ timeout: 10000 });
		await firstCardLink.click();
		await page.waitForLoadState('networkidle');
		await page.waitForTimeout(3000);

		if (brokenImages.length > 0) {
			console.log('Broken images on detail page:', brokenImages);
		}
		expect(brokenImages).toEqual([]);
	});
});

test.describe('Dark mode CSS tokens', () => {
	test('light mode CSS tokens are defined on :root', async ({ page }) => {
		await page.goto(CATALOG_URL);
		await page.waitForLoadState('networkidle');

		const tokens = await page.evaluate(() => {
			const style = getComputedStyle(document.documentElement);
			return {
				text: style.getPropertyValue('--csf-text').trim(),
				bg: style.getPropertyValue('--csf-bg').trim(),
				border: style.getPropertyValue('--csf-border').trim(),
				primary: style.getPropertyValue('--csf-primary').trim(),
				secondary: style.getPropertyValue('--csf-secondary').trim(),
				surface: style.getPropertyValue('--csf-surface').trim(),
			};
		});

		for (const [name, value] of Object.entries(tokens)) {
			expect(value, `--csf-${name} should be defined`).not.toBe('');
		}
	});

	test('dark mode emulation changes token values', async ({ page }) => {
		await page.goto(CATALOG_URL);
		await page.waitForLoadState('networkidle');

		const lightBg = await page.evaluate(() =>
			getComputedStyle(document.documentElement).getPropertyValue('--csf-bg').trim()
		);

		await page.emulateMedia({ colorScheme: 'dark' });
		await page.waitForTimeout(500);

		const darkBg = await page.evaluate(() =>
			getComputedStyle(document.documentElement).getPropertyValue('--csf-bg').trim()
		);

		expect(lightBg).not.toBe('');
		expect(darkBg).not.toBe('');
		expect(lightBg).not.toBe(darkBg);
	});

	test('catalog cards render with visible borders', async ({ page }) => {
		await page.goto(CATALOG_URL);
		await page.waitForLoadState('networkidle');

		const card = page.locator('.csf-part-card').first();
		await expect(card).toBeVisible({ timeout: 10000 });

		const borderColor = await card.evaluate((el) =>
			getComputedStyle(el).borderColor
		);

		expect(borderColor).toBeTruthy();
		expect(borderColor).not.toBe('transparent');
	});
});
