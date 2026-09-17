import { registerBlockType } from '@wordpress/blocks';
import { search } from '@wordpress/icons';
import Edit from './edit';
import metadata from '../block.json';

registerBlockType( metadata.name, {
	icon: search,
	edit: Edit,
	save: () => null,
} );
