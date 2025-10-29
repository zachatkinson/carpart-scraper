import { registerBlockType } from '@wordpress/blocks';
import Edit from './edit';

registerBlockType('csf-parts/vehicle-selector', {
	edit: Edit,
});
