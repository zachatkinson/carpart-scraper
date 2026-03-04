#!/bin/bash
# Update Kadence Global Palette via WP-CLI

echo "🎨 Updating Kadence Color Palettes via WP-CLI..."
echo ""

# Light mode palette
echo "Setting Light Mode Palette:"
ddev wp theme mod set global_palette '[
  {"color":"#2563eb"},
  {"color":"#1d4ed8"},
  {"color":"#7c3aed"},
  {"color":"#dbeafe"},
  {"color":"#6b7280"},
  {"color":"#4b5563"},
  {"color":"#e5e7eb"},
  {"color":"#fcfcfc"},
  {"color":"#111827"}
]'

echo "✓ Light mode palette set!"
echo ""

# Dark mode palette (if Kadence Pro is installed)
echo "Setting Dark Mode Palette:"
ddev wp theme mod set global_palette_dark '[
  {"color":"#60a5fa"},
  {"color":"#3b82f6"},
  {"color":"#a78bfa"},
  {"color":"#1e3a8a"},
  {"color":"#cbd5e1"},
  {"color":"#94a3b8"},
  {"color":"#334155"},
  {"color":"#f8fafc"},
  {"color":"#0f172a"}
]'

echo "✓ Dark mode palette set!"
echo ""
echo "✅ Kadence color palettes updated successfully!"
echo ""
echo "Verify by running:"
echo "  ddev wp theme mod get global_palette"
echo "  ddev wp theme mod get global_palette_dark"
