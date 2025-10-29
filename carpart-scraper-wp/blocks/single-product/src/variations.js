/**
 * Block Variations for Single Product Block
 *
 * Provides preset configurations for common use cases.
 */
import { __ } from '@wordpress/i18n';

const variations = [
	{
		name: 'full-details',
		title: __('Full Details', 'csf-parts'),
		description: __('Display all product information including price, specs, and features', 'csf-parts'),
		icon: 'list-view',
		attributes: {
			showPrice: true,
			showSpecs: true,
			showFeatures: true,
		},
		isDefault: true,
		scope: ['block'],
	},
	{
		name: 'minimal-card',
		title: __('Minimal Card', 'csf-parts'),
		description: __('Simple product card with image, title, and price only', 'csf-parts'),
		icon: 'id-alt',
		attributes: {
			showPrice: true,
			showSpecs: false,
			showFeatures: false,
		},
		scope: ['block'],
	},
	{
		name: 'specs-focus',
		title: __('Specifications Focus', 'csf-parts'),
		description: __('Highlight technical specifications, hide features and price', 'csf-parts'),
		icon: 'editor-table',
		attributes: {
			showPrice: false,
			showSpecs: true,
			showFeatures: false,
		},
		scope: ['block'],
	},
	{
		name: 'catalog-view',
		title: __('Catalog View', 'csf-parts'),
		description: __('Product overview with price and features, no detailed specs', 'csf-parts'),
		icon: 'products',
		attributes: {
			showPrice: true,
			showSpecs: false,
			showFeatures: true,
		},
		scope: ['block'],
	},
];

export default variations;
