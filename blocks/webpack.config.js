const defaultConfig = require( '@wordpress/scripts/config/webpack.config' );
const path = require( 'path' );

module.exports = {
	...defaultConfig,
	entry: {
		'single-product/index': './single-product/src/index.js',
		'product-grid/index': './product-grid/src/index.js',
		'vehicle-selector/index': './vehicle-selector/index.js',
	},
	output: {
		path: path.resolve( __dirname, 'build' ),
		filename: '[name].js',
	},
};
