import { useBlockProps, InspectorControls } from '@wordpress/block-editor';
import { PanelBody, RangeControl, TextControl, ToggleControl } from '@wordpress/components';
import { __ } from '@wordpress/i18n';
import ServerSideRender from '@wordpress/server-side-render';

export default function Edit({ attributes, setAttributes }) {
	const blockProps = useBlockProps();
	const { showYear, showMake, showModel, resultsPerPage, columns, buttonText, enableAjax } = attributes;

	return (
		<div {...blockProps}>
			<InspectorControls>
				<PanelBody title={__('Filter Settings', 'csf-parts')}>
					<ToggleControl
						label={__('Show Year Filter', 'csf-parts')}
						checked={showYear}
						onChange={(value) => setAttributes({ showYear: value })}
						help={__('Allow filtering by vehicle year', 'csf-parts')}
					/>
					<ToggleControl
						label={__('Show Make Filter', 'csf-parts')}
						checked={showMake}
						onChange={(value) => setAttributes({ showMake: value })}
						help={__('Allow filtering by vehicle make', 'csf-parts')}
					/>
					<ToggleControl
						label={__('Show Model Filter', 'csf-parts')}
						checked={showModel}
						onChange={(value) => setAttributes({ showModel: value })}
						help={__('Allow filtering by vehicle model', 'csf-parts')}
					/>
				</PanelBody>
				<PanelBody title={__('Results Settings', 'csf-parts')} initialOpen={false}>
					<RangeControl
						label={__('Results per page', 'csf-parts')}
						value={resultsPerPage}
						onChange={(value) => setAttributes({ resultsPerPage: value })}
						min={3}
						max={24}
					/>
					<RangeControl
						label={__('Columns', 'csf-parts')}
						value={columns}
						onChange={(value) => setAttributes({ columns: value })}
						min={1}
						max={4}
					/>
				</PanelBody>
				<PanelBody title={__('Advanced', 'csf-parts')} initialOpen={false}>
					<TextControl
						label={__('Button Text', 'csf-parts')}
						value={buttonText}
						onChange={(value) => setAttributes({ buttonText: value })}
					/>
					<ToggleControl
						label={__('Enable AJAX Search', 'csf-parts')}
						checked={enableAjax}
						onChange={(value) => setAttributes({ enableAjax: value })}
						help={__('Load results without page reload', 'csf-parts')}
					/>
				</PanelBody>
			</InspectorControls>

			<ServerSideRender
				block="csf-parts/vehicle-selector"
				attributes={attributes}
			/>
		</div>
	);
}
