/**
 * Inspect Kadence Customizer Structure
 * Debug script to find the correct selectors for color palette settings
 */

import { chromium } from '@playwright/test';

const SITE_URL = 'https://csf-parts-catalog.ddev.site';

async function inspectCustomizer() {
	console.log('🔍 Inspecting Kadence Customizer Structure...\n');

	const browser = await chromium.launch({ headless: false });
	const context = await browser.newContext();
	const page = await context.newPage();

	try {
		// Login
		console.log('1. Authenticating...');
		await page.goto(`${SITE_URL}/wp-admin`);

		const isLoggedIn = await page.locator('#wpadminbar').isVisible().catch(() => false);
		if (!isLoggedIn) {
			await page.fill('#user_login', 'admin');
			await page.fill('#user_pass', 'admin');
			await page.click('#wp-submit');
			await page.waitForURL(/wp-admin/, { timeout: 10000 });
		}
		console.log('   ✓ Authenticated\n');

		// Navigate to customizer
		console.log('2. Opening WordPress Customizer...');
		await page.goto(`${SITE_URL}/wp-admin/customize.php`);
		await page.waitForSelector('#customize-controls', { timeout: 15000 });
		console.log('   ✓ Customizer loaded\n');

		// Wait a bit for everything to load
		await page.waitForTimeout(2000);

		// Log all accordion sections
		console.log('3. Finding Accordion Sections:');
		const sections = await page.locator('#customize-controls li.accordion-section').all();
		console.log(`   Found ${sections.length} sections\n`);

		for (let i = 0; i < Math.min(sections.length, 30); i++) {
			const section = sections[i];
			const button = section.locator('button.accordion-section-title, h3.accordion-section-title').first();

			if (await button.isVisible()) {
				const text = await button.textContent();
				const ariaLabel = await button.getAttribute('aria-label').catch(() => null);
				const id = await section.getAttribute('id').catch(() => null);

				console.log(`   [${i + 1}] "${text?.trim()}" (id: ${id}, aria: ${ariaLabel})`);
			}
		}

		console.log('\n4. Looking for palette-related sections...');
		const paletteRelated = await page.locator('li.accordion-section:has-text("Palette"), li.accordion-section:has-text("Color"), li.accordion-section:has-text("color"), li.accordion-section:has-text("palette")').all();
		console.log(`   Found ${paletteRelated.length} palette/color-related sections\n`);

		for (const section of paletteRelated) {
			const button = section.locator('button.accordion-section-title, h3.accordion-section-title').first();
			if (await button.isVisible()) {
				const text = await button.textContent();
				const id = await section.getAttribute('id');
				console.log(`   • "${text?.trim()}" (id: ${id})`);
			}
		}

		// Try to find Kadence-specific sections
		console.log('\n5. Looking for Kadence-specific sections...');
		const kadenceSections = await page.locator('li.accordion-section[id*="kadence"], li.accordion-section[id*="global"]').all();
		console.log(`   Found ${kadenceSections.length} Kadence sections\n`);

		for (const section of kadenceSections) {
			const button = section.locator('button.accordion-section-title, h3.accordion-section-title').first();
			if (await button.isVisible()) {
				const text = await button.textContent();
				const id = await section.getAttribute('id');
				console.log(`   • "${text?.trim()}" (id: ${id})`);
			}
		}

		console.log('\n✅ Inspection complete! Leave browser open to manually explore...\n');
		console.log('Press Ctrl+C when done.\n');

		// Keep browser open
		await page.waitForTimeout(300000); // 5 minutes

	} catch (error) {
		console.error('❌ Error:', error.message);
	}

	await browser.close();
}

inspectCustomizer().catch(console.error);
