/**
 * Playwright Test Configuration
 */

import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
	testDir: './tests/e2e',
	fullyParallel: false,
	forbidOnly: !!process.env.CI,
	retries: process.env.CI ? 2 : 0,
	workers: 1,
	reporter: 'html',
	use: {
		baseURL: process.env.BASE_URL || 'https://zachatkinson.com/demos/rad/',
		trace: 'on-first-retry',
		screenshot: 'only-on-failure',
		video: 'retain-on-failure',
		// Headless mode - set to false to see browser
		headless: false,
	},

	projects: [
		{
			name: 'chromium',
			use: { ...devices['Desktop Chrome'] },
		},
	],

	// Run local dev server before tests if needed
	// webServer: {
	// 	command: 'ddev start',
	// 	url: 'https://csf-parts-catalog.ddev.site',
	// 	reuseExistingServer: true,
	// },
});
