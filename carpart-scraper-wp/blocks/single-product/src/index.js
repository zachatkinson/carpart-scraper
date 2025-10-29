import { registerBlockType } from '@wordpress/blocks';
import { __ } from '@wordpress/i18n';
import Edit from './edit';
import variations from './variations';

registerBlockType('csf-parts/single-product', {
	edit: Edit,
	variations,
});
