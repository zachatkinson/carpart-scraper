import { registerBlockType } from '@wordpress/blocks';
import { search } from '@wordpress/icons';
import Edit from './edit.js';
import metadata from '../block.json';

registerBlockType( metadata.name, {
	icon: search,
	edit: Edit,
	save: () => null,
} );
