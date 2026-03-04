import { test, expect } from '@playwright/test';

test.describe('Color System - Light and Dark Mode', () => {
	test.beforeEach(async ({ page }) => {
		// Navigate to the parts demo page
		await page.goto('https://csf-parts-catalog.ddev.site/parts-demo/');
		// Wait for the page to fully load
		await page.waitForLoadState('networkidle');
	});

	test('light mode - capture colors', async ({ page }) => {
		// Make sure we're in light mode
		const darkModeToggle = page.locator('.color-toggle-icon');
		const isDarkMode = await page.locator('body.color-switch-dark').count() > 0;

		if (isDarkMode) {
			await darkModeToggle.click();
			await page.waitForTimeout(500);
		}

		// Take full page screenshot
		await page.screenshot({
			path: 'screenshots/light-mode-full.png',
			fullPage: true
		});

		// Take screenshot of the product catalog block
		const catalogBlock = page.locator('.csf-product-catalog').first();
		await catalogBlock.screenshot({
			path: 'screenshots/light-mode-catalog.png'
		});

		// Take screenshot of a product card
		const productCard = page.locator('.csf-part-card').first();
		await productCard.screenshot({
			path: 'screenshots/light-mode-card.png'
		});

		// Take screenshot of search and filters
		const filters = page.locator('.csf-filter-controls');
		await filters.screenshot({
			path: 'screenshots/light-mode-filters.png'
		});

		console.log('✅ Light mode screenshots captured');
	});

	test('dark mode - capture colors', async ({ page }) => {
		// Switch to dark mode
		const darkModeToggle = page.locator('.color-toggle-icon');
		const isDarkMode = await page.locator('body.color-switch-dark').count() > 0;

		if (!isDarkMode) {
			await darkModeToggle.click();
			await page.waitForTimeout(500);
		}

		// Take full page screenshot
		await page.screenshot({
			path: 'screenshots/dark-mode-full.png',
			fullPage: true
		});

		// Take screenshot of the product catalog block
		const catalogBlock = page.locator('.csf-product-catalog').first();
		await catalogBlock.screenshot({
			path: 'screenshots/dark-mode-catalog.png'
		});

		// Take screenshot of a product card
		const productCard = page.locator('.csf-part-card').first();
		await productCard.screenshot({
			path: 'screenshots/dark-mode-card.png'
		});

		// Take screenshot of search and filters
		const filters = page.locator('.csf-filter-controls');
		await filters.screenshot({
			path: 'screenshots/dark-mode-filters.png'
		});

		console.log('✅ Dark mode screenshots captured');
	});

	test('verify CSS variables are present', async ({ page }) => {
		// Check computed styles
		const body = page.locator('body');

		// Get computed values of our CSS variables
		const cssVars = await body.evaluate(() => {
			const styles = getComputedStyle(document.documentElement);
			return {
				primary: styles.getPropertyValue('--csf-primary').trim(),
				secondary: styles.getPropertyValue('--csf-secondary').trim(),
				background: styles.getPropertyValue('--csf-background').trim(),
				text: styles.getPropertyValue('--csf-text').trim(),
				globalPalette1: styles.getPropertyValue('--global-palette1').trim(),
				globalPalette4: styles.getPropertyValue('--global-palette4').trim(),
			};
		});

		console.log('CSS Variables (Light Mode):', cssVars);

		// Switch to dark mode
		const darkModeToggle = page.locator('.color-toggle-icon');
		await darkModeToggle.click();
		await page.waitForTimeout(500);

		const cssVarsDark = await body.evaluate(() => {
			const styles = getComputedStyle(document.documentElement);
			return {
				primary: styles.getPropertyValue('--csf-primary').trim(),
				secondary: styles.getPropertyValue('--csf-secondary').trim(),
				background: styles.getPropertyValue('--csf-background').trim(),
				text: styles.getPropertyValue('--csf-text').trim(),
				globalPalette1: styles.getPropertyValue('--global-palette1').trim(),
				globalPalette4: styles.getPropertyValue('--global-palette4').trim(),
			};
		});

		console.log('CSS Variables (Dark Mode):', cssVarsDark);

		// Verify variables changed
		expect(cssVarsDark.background).not.toBe(cssVars.background);
	});

	test('verify background colors change', async ({ page }) => {
		// Get background color in light mode
		const catalogBlock = page.locator('.csf-product-catalog').first();
		const lightBg = await catalogBlock.evaluate((el) => {
			return getComputedStyle(el).backgroundColor;
		});

		console.log('Light mode background:', lightBg);

		// Switch to dark mode
		const darkModeToggle = page.locator('.color-toggle-icon');
		await darkModeToggle.click();
		await page.waitForTimeout(500);

		// Get background color in dark mode
		const darkBg = await catalogBlock.evaluate((el) => {
			return getComputedStyle(el).backgroundColor;
		});

		console.log('Dark mode background:', darkBg);

		// Verify they're different
		expect(darkBg).not.toBe(lightBg);
	});
});
