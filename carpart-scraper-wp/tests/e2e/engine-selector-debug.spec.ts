import { test, expect } from '@playwright/test';

test('debug engine selector', async ({ page }) => {
  // Capture console logs
  const logs: string[] = [];
  page.on('console', msg => {
    const text = msg.text();
    logs.push(text);
    console.log('CONSOLE:', text);
  });

  // Navigate to the page
  console.log('Navigating to page...');
  await page.goto('https://csf-parts-catalog.ddev.site/parts/csf4514/?csf_year=1996&csf_make=Honda&csf_model=Civic%20Del%20Sol');

  // Wait for page to load
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(2000);

  // Check if engine dropdown exists
  const dropdown = await page.locator('#csf-engine-variant');
  await expect(dropdown).toBeVisible();

  console.log('\n=== Engine dropdown found ===\n');

  // Get all options
  const options = await page.locator('#csf-engine-variant option').evaluateAll(opts =>
    opts.map(opt => ({ value: (opt as HTMLOptionElement).value, text: opt.textContent || '' }))
  );

  console.log('Available engine options:');
  options.forEach((opt, i) => {
    console.log(`  ${i}: "${opt.text}" (value: "${opt.value}")`);
  });

  // Select the first non-empty option
  const engineToSelect = options.find(opt => opt.value && opt.value !== '');

  if (!engineToSelect) {
    throw new Error('No engine options to select!');
  }

  console.log(`\n=== Selecting engine: "${engineToSelect.text}" (value: "${engineToSelect.value}") ===\n`);

  // Select the engine
  await page.selectOption('#csf-engine-variant', engineToSelect.value);

  // Wait for any animations/updates
  await page.waitForTimeout(1000);

  console.log('\n=== All console logs ===\n');
  logs.forEach(log => console.log(log));

  // Check the badge status
  const badges = await page.locator('.fitment-match-badge').evaluateAll(badges =>
    badges.map(b => ({
      text: b.textContent,
      classes: b.className
    }))
  );

  console.log('\n=== Fitment badges after selection ===');
  console.log(JSON.stringify(badges, null, 2));

  // Take a screenshot
  await page.screenshot({ path: '/private/tmp/engine-selector-debug.png', fullPage: true });
  console.log('\n=== Screenshot saved to /private/tmp/engine-selector-debug.png ===');
});
