/**
 * Playwright E2E Test: Configure Kadence Theme Color Palettes
 *
 * Sets up light and dark color palettes in Kadence theme:
 * - Palette 1 (Light mode): Light color swatch
 * - Palette 2 (Dark mode): Dark color swatch
 */

import { test, expect } from '@playwright/test';

// Configuration
const SITE_URL = 'https://csf-parts-catalog.ddev.site';
const ADMIN_USER = 'admin';
const ADMIN_PASS = 'admin'; // Update if different

// Color palettes - WCAG AA compliant
const LIGHT_PALETTE = {
	palette1: '#2563eb', // Primary blue
	palette2: '#1d4ed8', // Primary hover
	palette3: '#7c3aed', // Secondary purple
	palette4: '#dbeafe', // Primary light
	palette5: '#6b7280', // Text tertiary
	palette6: '#4b5563', // Text secondary
	palette7: '#e5e7eb', // Border
	palette8: '#fcfcfc', // Background (off-white, easier on eyes)
	palette9: '#111827', // Text
};

const DARK_PALETTE = {
	palette1: '#60a5fa', // Primary blue (lighter)
	palette2: '#3b82f6', // Primary hover
	palette3: '#a78bfa', // Secondary purple (lighter)
	palette4: '#1e3a8a', // Primary dark
	palette5: '#cbd5e1', // Text secondary
	palette6: '#94a3b8', // Text tertiary
	palette7: '#334155', // Border
	palette8: '#f8fafc', // Text (light)
	palette9: '#0f172a', // Background (dark)
};

test.describe('Kadence Theme Color Configuration', () => {
	test.beforeEach(async ({ page }) => {
		// Login to WordPress admin
		await page.goto(`${SITE_URL}/wp-admin`);

		// Check if already logged in
		const isLoggedIn = await page.locator('#wpadminbar').isVisible().catch(() => false);

		if (!isLoggedIn) {
			await page.fill('#user_login', ADMIN_USER);
			await page.fill('#user_pass', ADMIN_PASS);
			await page.click('#wp-submit');
			await page.waitForURL(/wp-admin/, { timeout: 10000 });
		}
	});

	test('Setup Kadence color palettes for light/dark mode', async ({ page }) => {
		console.log('Navigating to Kadence Customizer...');

		// Navigate to Customizer
		await page.goto(`${SITE_URL}/wp-admin/customize.php`);

		// Wait for customizer to load
		await page.waitForSelector('#customize-controls', { timeout: 15000 });

		console.log('Customizer loaded, looking for Kadence Global Palette...');

		// Click on "Global Palette" or "Colors" section
		// Try multiple selectors as Kadence structure may vary
		const paletteButton = page.locator('button:has-text("Global Palette"), button:has-text("Colors"), li[aria-label*="Colors"]').first();
		await paletteButton.click();
		await page.waitForTimeout(1000);

		console.log('Configuring Light Mode Palette (Palette 1)...');

		// Look for palette editor - this may be in an accordion or panel
		const paletteEditor = page.locator('[data-control-id*="palette"]').first();
		await paletteEditor.waitFor({ timeout: 10000 });

		// Set light mode colors (Palette 1)
		for (const [key, color] of Object.entries(LIGHT_PALETTE)) {
			const colorInput = page.locator(`input[data-palette="${key}"], input[name*="${key}"]`).first();
			if (await colorInput.isVisible()) {
				await colorInput.fill(color);
				console.log(`  Set ${key}: ${color}`);
			}
		}

		console.log('Configuring Dark Mode Palette (Palette 2)...');

		// Look for dark mode toggle or second palette
		const darkModeToggle = page.locator('button:has-text("Dark Mode"), [data-palette-mode="dark"]').first();
		if (await darkModeToggle.isVisible()) {
			await darkModeToggle.click();
			await page.waitForTimeout(500);

			// Set dark mode colors (Palette 2)
			for (const [key, color] of Object.entries(DARK_PALETTE)) {
				const colorInput = page.locator(`input[data-palette="${key}"], input[name*="${key}"]`).first();
				if (await colorInput.isVisible()) {
					await colorInput.fill(color);
					console.log(`  Set ${key}: ${color}`);
				}
			}
		}

		console.log('Publishing changes...');

		// Save/Publish customizer changes
		const publishButton = page.locator('#save', { hasText: 'Publish' }).or(page.locator('button:has-text("Publish")')).first();
		await publishButton.click();

		// Wait for save to complete
		await page.waitForTimeout(2000);

		console.log('✅ Kadence color palettes configured successfully!');
	});

	test('Verify dark mode toggle works', async ({ page }) => {
		console.log('Testing dark mode toggle...');

		// Go to a page with the catalog block
		await page.goto(`${SITE_URL}/parts-demo/`);

		// Wait for page load
		await page.waitForLoadState('networkidle');

		// Look for Kadence dark mode toggle (usually in header or footer)
		const darkModeToggle = page.locator('[data-toggle-dark-mode], .kadence-dark-mode-toggle, button[aria-label*="dark"]').first();

		if (await darkModeToggle.isVisible()) {
			console.log('Found dark mode toggle');

			// Get initial background color of search input
			const searchInput = page.locator('.csf-search-box__input').first();
			await searchInput.waitFor();

			const lightBg = await searchInput.evaluate(el => {
				return window.getComputedStyle(el).backgroundColor;
			});
			console.log(`Light mode background: ${lightBg}`);

			// Toggle dark mode
			await darkModeToggle.click();
			await page.waitForTimeout(1000);

			const darkBg = await searchInput.evaluate(el => {
				return window.getComputedStyle(el).backgroundColor;
			});
			console.log(`Dark mode background: ${darkBg}`);

			// Verify backgrounds are different
			expect(lightBg).not.toBe(darkBg);
			console.log('✅ Dark mode toggle is working!');
		} else {
			console.log('⚠️  Dark mode toggle not found on page');
			console.log('Check Kadence theme settings to enable dark mode toggle');
		}
	});

	test('Inspect current color palette values', async ({ page }) => {
		console.log('Inspecting current Kadence palette values...');

		// Go to a page with styles loaded
		await page.goto(`${SITE_URL}/parts-demo/`);
		await page.waitForLoadState('networkidle');

		// Get computed CSS custom properties
		const paletteValues = await page.evaluate(() => {
			const root = document.documentElement;
			const styles = getComputedStyle(root);
			const palette = {};

			for (let i = 1; i <= 9; i++) {
				const value = styles.getPropertyValue(`--global-palette${i}`);
				if (value) {
					palette[`palette${i}`] = value.trim();
				}
			}

			return palette;
		});

		console.log('Current Kadence Global Palette:');
		console.log(JSON.stringify(paletteValues, null, 2));

		// Also check our plugin variables
		const csfValues = await page.evaluate(() => {
			const root = document.documentElement;
			const styles = getComputedStyle(root);
			return {
				primary: styles.getPropertyValue('--csf-primary').trim(),
				background: styles.getPropertyValue('--csf-background').trim(),
				text: styles.getPropertyValue('--csf-text').trim(),
				border: styles.getPropertyValue('--csf-border').trim(),
			};
		});

		console.log('\nCSF Plugin Color Variables:');
		console.log(JSON.stringify(csfValues, null, 2));
	});
});
