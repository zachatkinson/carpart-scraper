import { registerBlockType } from '@wordpress/blocks';
import { __ } from '@wordpress/i18n';
import Edit from './edit.js';
import variations from './variations.js';

registerBlockType('csf-parts/single-product', {
	edit: Edit,
	variations,
});
