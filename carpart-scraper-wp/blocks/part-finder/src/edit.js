import { useBlockProps, InspectorControls } from '@wordpress/block-editor';
import { PanelBody, TextControl, TextareaControl, ToggleControl, SelectControl, Disabled } from '@wordpress/components';
import { __ } from '@wordpress/i18n';
import ServerSideRender from '@wordpress/server-side-render';

/**
 * Part Finder block editor component.
 *
 * Content and behaviour live here; colours, spacing, typography, border and
 * shadow come from the core Styles tab.
 */
export default function Edit( { attributes, setAttributes } ) {
	const blockProps = useBlockProps();
	const {
		eyebrow,
		heading,
		headingLevel,
		showSearch,
		searchPlaceholder,
		showYear,
		showMake,
		showModel,
		buttonText,
		targetUrl,
		showFootnote,
		footnoteText,
	} = attributes;

	return (
		<div { ...blockProps }>
			<InspectorControls>
				<PanelBody title={ __( 'Content', 'csf-parts' ) } initialOpen={ true }>
					<TextControl
						label={ __( 'Eyebrow', 'csf-parts' ) }
						value={ eyebrow }
						onChange={ ( value ) => setAttributes( { eyebrow: value } ) }
						help={ __( 'Small uppercase label above the heading. Leave empty to hide.', 'csf-parts' ) }
					/>
					<TextControl
						label={ __( 'Heading', 'csf-parts' ) }
						value={ heading }
						onChange={ ( value ) => setAttributes( { heading: value } ) }
					/>
					<SelectControl
						label={ __( 'Heading level', 'csf-parts' ) }
						value={ String( headingLevel ) }
						options={ [ 1, 2, 3, 4 ].map( ( n ) => ( { label: `H${ n }`, value: String( n ) } ) ) }
						onChange={ ( value ) => setAttributes( { headingLevel: parseInt( value, 10 ) } ) }
					/>
					<TextControl
						label={ __( 'Button text', 'csf-parts' ) }
						value={ buttonText }
						onChange={ ( value ) => setAttributes( { buttonText: value } ) }
					/>
				</PanelBody>

				<PanelBody title={ __( 'Fields', 'csf-parts' ) } initialOpen={ true }>
					<ToggleControl
						label={ __( 'Part number search box', 'csf-parts' ) }
						checked={ showSearch }
						onChange={ ( value ) => setAttributes( { showSearch: value } ) }
					/>
					{ showSearch && (
						<TextControl
							label={ __( 'Search placeholder', 'csf-parts' ) }
							value={ searchPlaceholder }
							onChange={ ( value ) => setAttributes( { searchPlaceholder: value } ) }
						/>
					) }
					<ToggleControl
						label={ __( 'Year', 'csf-parts' ) }
						checked={ showYear }
						onChange={ ( value ) => setAttributes( { showYear: value } ) }
					/>
					<ToggleControl
						label={ __( 'Make', 'csf-parts' ) }
						checked={ showMake }
						onChange={ ( value ) => setAttributes( { showMake: value } ) }
					/>
					<ToggleControl
						label={ __( 'Model', 'csf-parts' ) }
						checked={ showModel }
						onChange={ ( value ) => setAttributes( { showModel: value } ) }
						help={ __( 'Model options load after a Make is chosen.', 'csf-parts' ) }
					/>
				</PanelBody>

				<PanelBody title={ __( 'Destination', 'csf-parts' ) } initialOpen={ false }>
					<TextControl
						label={ __( 'Parts page URL', 'csf-parts' ) }
						value={ targetUrl }
						onChange={ ( value ) => setAttributes( { targetUrl: value } ) }
						placeholder={ __( 'Auto-detect (page containing the Product Catalog block)', 'csf-parts' ) }
						help={ __( 'Where "Show parts" sends visitors. Filters are appended as csf_search, csf_year, csf_make and csf_model.', 'csf-parts' ) }
					/>
				</PanelBody>

				<PanelBody title={ __( 'Footnote', 'csf-parts' ) } initialOpen={ false }>
					<ToggleControl
						label={ __( 'Show footnote', 'csf-parts' ) }
						checked={ showFootnote }
						onChange={ ( value ) => setAttributes( { showFootnote: value } ) }
					/>
					{ showFootnote && (
						<TextareaControl
							label={ __( 'Footnote text', 'csf-parts' ) }
							value={ footnoteText }
							onChange={ ( value ) => setAttributes( { footnoteText: value } ) }
							help={ __( '{count} is replaced with the live number of parts.', 'csf-parts' ) }
						/>
					) }
				</PanelBody>
			</InspectorControls>

			<Disabled>
				<ServerSideRender block="csf-parts/part-finder" attributes={ attributes } />
			</Disabled>
		</div>
	);
}
