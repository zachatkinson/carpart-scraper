import { registerBlockType } from '@wordpress/blocks';
import { __ } from '@wordpress/i18n';
import Edit from './edit';

registerBlockType('csf-parts/product-catalog', {
	edit: Edit,
	save: () => null, // Server-side rendered
});
