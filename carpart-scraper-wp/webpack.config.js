import defaultConfig from '@wordpress/scripts/config/webpack.config.js';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname( fileURLToPath( import.meta.url ) );

export default {
	...defaultConfig,
	entry: {
		'product-catalog/index': path.resolve( __dirname, 'blocks/product-catalog/src/index.js' ),
		'single-product/index': path.resolve( __dirname, 'blocks/single-product/src/index.js' ),
	},
	output: {
		...defaultConfig.output,
		path: path.resolve( __dirname, 'blocks/build' ),
	},
};
