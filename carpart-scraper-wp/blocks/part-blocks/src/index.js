import { registerBlockType } from '@wordpress/blocks';
import { useBlockProps, InspectorControls } from '@wordpress/block-editor';
import { PanelBody, TextControl, TextareaControl, ToggleControl, SelectControl, RangeControl, Disabled, Notice } from '@wordpress/components';
import { __ } from '@wordpress/i18n';
import ServerSideRender from '@wordpress/server-side-render';

import breadcrumbs from '../../part-breadcrumbs/block.json';
import gallery from '../../part-gallery/block.json';
import header from '../../part-header/block.json';
import keySpecs from '../../part-key-specs/block.json';
import replaces from '../../part-replaces/block.json';
import fitment from '../../part-fitment/block.json';
import specCards from '../../part-spec-cards/block.json';
import features from '../../part-features/block.json';
import related from '../../part-related/block.json';

/**
 * Inspector controls per block: [attribute, label, type, extra].
 * Empty text attributes mean "use the plugin default".
 */
const CONTROLS = {
	'csf-parts/part-gallery': [ [ 'showThumbnails', __( 'Show thumbnails', 'csf-parts' ), 'toggle' ] ],
	'csf-parts/part-header': [
		[ 'showEyebrow', __( 'Show eyebrow (category · construction · part number)', 'csf-parts' ), 'toggle' ],
		[ 'showIntro', __( 'Show intro paragraph and tech note', 'csf-parts' ), 'toggle' ],
		[ 'showActions', __( 'Show buttons and note', 'csf-parts' ), 'toggle' ],
		[ 'noteText', __( 'Note text', 'csf-parts' ), 'textarea', { help: __( 'Leave empty to use Settings → Part Page.', 'csf-parts' ) } ],
		[ 'showVehicleBox', __( 'Show "Your vehicle" box on vehicle URLs', 'csf-parts' ), 'toggle' ],
	],
	'csf-parts/part-key-specs': [
		[ 'title', __( 'Title', 'csf-parts' ), 'text', { placeholder: __( 'Key specifications', 'csf-parts' ) } ],
		[ 'maxRows', __( 'Maximum rows', 'csf-parts' ), 'range', { min: 1, max: 12 } ],
	],
	'csf-parts/part-replaces': [ [ 'label', __( 'Label', 'csf-parts' ), 'text', { placeholder: __( 'Replaces', 'csf-parts' ) } ] ],
	'csf-parts/part-fitment': [
		[ 'title', __( 'Title', 'csf-parts' ), 'text', { placeholder: __( 'Fits these vehicles', 'csf-parts' ) } ],
		[ 'showSummary', __( 'Show "1 make · 1 model · …" summary', 'csf-parts' ), 'toggle' ],
		[ 'layout', __( 'Layout', 'csf-parts' ), 'select', { options: [ { label: __( 'Plugin default (Settings → Part Page)', 'csf-parts' ), value: '' }, { label: __( 'Table', 'csf-parts' ), value: 'table' }, { label: __( 'Expandable cards', 'csf-parts' ), value: 'cards' } ] } ],
	],
	'csf-parts/part-spec-cards': [
		[ 'showDimensions', __( 'Dimensions card', 'csf-parts' ), 'toggle' ],
		[ 'showConstruction', __( 'Construction card', 'csf-parts' ), 'toggle' ],
		[ 'showMore', __( 'Remaining specifications', 'csf-parts' ), 'toggle' ],
	],
	'csf-parts/part-features': [ [ 'title', __( 'Title', 'csf-parts' ), 'text', { placeholder: __( 'Features & benefits', 'csf-parts' ) } ] ],
	'csf-parts/part-related': [
		[ 'title', __( 'Title', 'csf-parts' ), 'text', { placeholder: __( 'Automatic: "Other parts for this …" or "Related parts"', 'csf-parts' ) } ],
		[ 'count', __( 'Number of parts', 'csf-parts' ), 'range', { min: 0, max: 8, allowReset: true, help: __( 'Reset to use Settings → Part Page.', 'csf-parts' ) } ],
	],
};

function Control( { def, attributes, setAttributes } ) {
	const [ key, label, type, extra = {} ] = def;
	const value = attributes[ key ];
	const set = ( v ) => setAttributes( { [ key ]: v } );
	switch ( type ) {
		case 'toggle':
			return <ToggleControl label={ label } checked={ !! value } onChange={ set } />;
		case 'textarea':
			return <TextareaControl label={ label } value={ value || '' } onChange={ set } help={ extra.help } />;
		case 'select':
			return <SelectControl label={ label } value={ value || '' } options={ extra.options } onChange={ set } />;
		case 'range':
			return <RangeControl label={ label } value={ value } onChange={ set } min={ extra.min } max={ extra.max } allowReset={ extra.allowReset } resetFallbackValue={ undefined } help={ extra.help } />;
		default:
			return <TextControl label={ label } value={ value || '' } onChange={ set } placeholder={ extra.placeholder } />;
	}
}

function makeEdit( metadata ) {
	return function Edit( { attributes, setAttributes } ) {
		const blockProps = useBlockProps();
		const controls = CONTROLS[ metadata.name ] || [];
		return (
			<div { ...blockProps }>
				<InspectorControls>
					{ controls.length > 0 && (
						<PanelBody title={ __( 'Content', 'csf-parts' ) } initialOpen={ true }>
							{ controls.map( ( def ) => <Control key={ def[ 0 ] } def={ def } attributes={ attributes } setAttributes={ setAttributes } /> ) }
						</PanelBody>
					) }
					<PanelBody title={ __( 'About', 'csf-parts' ) } initialOpen={ false }>
						<Notice status="info" isDismissible={ false }>
							{ __( 'Previews use a sample part. On a real part page the block shows that part.', 'csf-parts' ) }
						</Notice>
					</PanelBody>
				</InspectorControls>
				<Disabled>
					<ServerSideRender block={ metadata.name } attributes={ attributes } />
				</Disabled>
			</div>
		);
	};
}

[ breadcrumbs, gallery, header, keySpecs, replaces, fitment, specCards, features, related ].forEach( ( metadata ) => {
	registerBlockType( metadata.name, { edit: makeEdit( metadata ), save: () => null } );
} );
