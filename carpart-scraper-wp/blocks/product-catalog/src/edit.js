import { useBlockProps, InspectorControls, PanelColorSettings } from '@wordpress/block-editor';
import {
	PanelBody,
	RangeControl,
	TextControl,
	ToggleControl,
	FormTokenField,
	Notice,
	SelectControl,
	ButtonGroup,
	Button,
	ColorPicker,
	BoxControl
} from '@wordpress/components';
import { __ } from '@wordpress/i18n';
import { useState } from '@wordpress/element';
import { desktop, tablet, mobile } from '@wordpress/icons';
import ServerSideRender from '@wordpress/server-side-render';

export default function Edit({ attributes, setAttributes }) {
	const blockProps = useBlockProps();
	const {
		defaultYears,
		defaultMakes,
		defaultModels,
		defaultCategories,
		showFilters,
		showYearFilter,
		showMakeFilter,
		showModelFilter,
		showCategoryFilter,
		perPage,
		columns,
		gap,
		buttonText,
		enableAjax,
		paginationType,
		imageAspectRatio,
		hoverEffect,
		borderRadius,
		borderWidth,
		borderColor,
		cardShadow,
		blockPadding,
		blockMargin,
		hideOnMobile,
		hideOnTablet,
		hideOnDesktop,
		scrollAnimation,
		colorScheme
	} = attributes;

	// Device switcher state
	const [selectedDevice, setSelectedDevice] = useState('desktop');

	// Suggestion lists (in real implementation, these would come from API)
	const yearSuggestions = ['2024', '2023', '2022', '2021', '2020', '2019', '2018', '2017', '2016', '2015'];
	const makeSuggestions = ['Honda', 'Toyota', 'Ford', 'GM', 'Nissan', 'BMW', 'Mercedes', 'Audi', 'Dodge', 'Jeep'];
	const categorySuggestions = ['Radiators', 'Condensers', 'Intercoolers', 'Oil Coolers', 'Radiator Caps'];

	const hasDefaults = defaultYears.length > 0 || defaultMakes.length > 0 ||
	                    defaultModels.length > 0 || defaultCategories.length > 0;

	return (
		<div {...blockProps}>
			<InspectorControls>
				<PanelBody title={__('Default Filters (Optional)', 'csf-parts')} initialOpen={true}>
					{!hasDefaults && (
						<Notice status="info" isDismissible={false}>
							{__('Leave empty to show all parts. Add defaults to create curated showcases like "Import Cooling Parts" or "Pre-1990s Domestic".', 'csf-parts')}
						</Notice>
					)}

					<FormTokenField
						label={__('Default Years', 'csf-parts')}
						value={defaultYears}
						suggestions={yearSuggestions}
						onChange={(years) => setAttributes({ defaultYears: years })}
						help={__('Example: "2020, 2021, 2022, 2023, 2024" for post-2020 parts', 'csf-parts')}
					/>

					<FormTokenField
						label={__('Default Makes', 'csf-parts')}
						value={defaultMakes}
						suggestions={makeSuggestions}
						onChange={(makes) => setAttributes({ defaultMakes: makes })}
						help={__('Example: "Honda, Toyota, Nissan" for import brands', 'csf-parts')}
					/>

					<FormTokenField
						label={__('Default Models', 'csf-parts')}
						value={defaultModels}
						suggestions={[]}
						onChange={(models) => setAttributes({ defaultModels: models })}
						help={__('Example: "Accord, Civic, CR-V" for specific models', 'csf-parts')}
					/>

					<FormTokenField
						label={__('Default Categories', 'csf-parts')}
						value={defaultCategories}
						suggestions={categorySuggestions}
						onChange={(categories) => setAttributes({ defaultCategories: categories })}
						help={__('Example: "Radiators, Intercoolers" for cooling parts', 'csf-parts')}
					/>
				</PanelBody>

				<PanelBody title={__('Filter Display', 'csf-parts')} initialOpen={true}>
					<ToggleControl
						label={__('Show Filter Controls', 'csf-parts')}
						checked={showFilters}
						onChange={(value) => setAttributes({ showFilters: value })}
						help={showFilters
							? __('Users can search/filter on the frontend', 'csf-parts')
							: __('Filters hidden - locked to defaults only', 'csf-parts')
						}
					/>

					{showFilters && (
						<>
							<Notice status="warning" isDismissible={false}>
								{__('With filters visible, users can override your defaults.', 'csf-parts')}
							</Notice>

							<ToggleControl
								label={__('Show Year Filter', 'csf-parts')}
								checked={showYearFilter}
								onChange={(value) => setAttributes({ showYearFilter: value })}
							/>
							<ToggleControl
								label={__('Show Make Filter', 'csf-parts')}
								checked={showMakeFilter}
								onChange={(value) => setAttributes({ showMakeFilter: value })}
							/>
							<ToggleControl
								label={__('Show Model Filter', 'csf-parts')}
								checked={showModelFilter}
								onChange={(value) => setAttributes({ showModelFilter: value })}
							/>
							<ToggleControl
								label={__('Show Category Filter', 'csf-parts')}
								checked={showCategoryFilter}
								onChange={(value) => setAttributes({ showCategoryFilter: value })}
							/>
						</>
					)}
				</PanelBody>

				<PanelBody title={__('Display Settings', 'csf-parts')} initialOpen={false}>
					{/* Global Device Switcher */}
					<div style={{
						marginBottom: '20px',
						paddingBottom: '16px',
						borderBottom: '1px solid #ddd'
					}}>
						<ButtonGroup style={{ display: 'flex', width: '100%' }}>
							<Button
								icon={desktop}
								label={__('Desktop', 'csf-parts')}
								isPressed={selectedDevice === 'desktop'}
								onClick={() => setSelectedDevice('desktop')}
								style={{ flex: 1, justifyContent: 'center' }}
							>
								{__('Desktop', 'csf-parts')}
							</Button>
							<Button
								icon={tablet}
								label={__('Tablet', 'csf-parts')}
								isPressed={selectedDevice === 'tablet'}
								onClick={() => setSelectedDevice('tablet')}
								style={{ flex: 1, justifyContent: 'center' }}
							>
								{__('Tablet', 'csf-parts')}
							</Button>
							<Button
								icon={mobile}
								label={__('Mobile', 'csf-parts')}
								isPressed={selectedDevice === 'mobile'}
								onClick={() => setSelectedDevice('mobile')}
								style={{ flex: 1, justifyContent: 'center' }}
							>
								{__('Mobile', 'csf-parts')}
							</Button>
						</ButtonGroup>
						<p style={{
							fontSize: '12px',
							color: '#757575',
							marginTop: '8px',
							marginBottom: 0
						}}>
							{selectedDevice === 'mobile' && __('Settings for mobile devices (< 768px)', 'csf-parts')}
							{selectedDevice === 'tablet' && __('Settings for tablets (768px - 1024px)', 'csf-parts')}
							{selectedDevice === 'desktop' && __('Settings for desktop (> 1024px)', 'csf-parts')}
						</p>
					</div>

					<RangeControl
						label={__('Results per page', 'csf-parts')}
						value={perPage}
						onChange={(value) => setAttributes({ perPage: value })}
						min={3}
						max={48}
					/>

					<RangeControl
						label={__('Columns', 'csf-parts')}
						value={columns[selectedDevice]}
						onChange={(value) => {
							const newColumns = { ...columns, [selectedDevice]: value };
							setAttributes({ columns: newColumns });
						}}
						min={1}
						max={4}
					/>
					<RangeControl
						label={__('Gap Between Items', 'csf-parts')}
						value={gap[selectedDevice]}
						onChange={(value) => {
							const newGap = { ...gap, [selectedDevice]: value };
							setAttributes({ gap: newGap });
						}}
						min={0}
						max={80}
						help={__('Space between product cards in pixels', 'csf-parts')}
					/>
					<SelectControl
						label={__('Pagination Type', 'csf-parts')}
						value={paginationType}
						onChange={(value) => setAttributes({ paginationType: value })}
						options={[
							{ label: __('Numbered Pages', 'csf-parts'), value: 'numbered' },
							{ label: __('Endless Scroll', 'csf-parts'), value: 'endless' },
							{ label: __('Load More Button', 'csf-parts'), value: 'loadmore' },
							{ label: __('No Pagination', 'csf-parts'), value: 'none' }
						]}
						help={__('Choose how users navigate through results', 'csf-parts')}
					/>
				</PanelBody>

				<PanelBody title={__('Card Styling', 'csf-parts')} initialOpen={false}>
					<SelectControl
						label={__('Image Aspect Ratio', 'csf-parts')}
						value={imageAspectRatio}
						onChange={(value) => setAttributes({ imageAspectRatio: value })}
						options={[
							{ label: __('Auto (Original)', 'csf-parts'), value: 'auto' },
							{ label: __('Square (1:1)', 'csf-parts'), value: '1/1' },
							{ label: __('Standard (4:3)', 'csf-parts'), value: '4/3' },
							{ label: __('Photo (3:2)', 'csf-parts'), value: '3/2' },
							{ label: __('Wide (16:9)', 'csf-parts'), value: '16/9' }
						]}
						help={__('Controls product image dimensions', 'csf-parts')}
					/>
					<SelectControl
						label={__('Hover Effect', 'csf-parts')}
						value={hoverEffect}
						onChange={(value) => setAttributes({ hoverEffect: value })}
						options={[
							{ label: __('None', 'csf-parts'), value: 'none' },
							{ label: __('Lift', 'csf-parts'), value: 'lift' },
							{ label: __('Zoom', 'csf-parts'), value: 'zoom' },
							{ label: __('Shadow', 'csf-parts'), value: 'shadow' }
						]}
						help={__('Animation when hovering over cards', 'csf-parts')}
					/>
					<RangeControl
						label={__('Border Radius', 'csf-parts')}
						value={borderRadius}
						onChange={(value) => setAttributes({ borderRadius: value })}
						min={0}
						max={50}
						help={__('Rounded corners in pixels', 'csf-parts')}
					/>
					<RangeControl
						label={__('Border Width', 'csf-parts')}
						value={borderWidth}
						onChange={(value) => setAttributes({ borderWidth: value })}
						min={0}
						max={10}
						help={__('Border thickness in pixels', 'csf-parts')}
					/>
					<PanelColorSettings
						title={__('Border Color', 'csf-parts')}
						colorSettings={[
							{
								value: borderColor,
								onChange: (value) => setAttributes({ borderColor: value }),
								label: __('Border', 'csf-parts')
							}
						]}
					/>
					<SelectControl
						label={__('Card Shadow', 'csf-parts')}
						value={cardShadow}
						onChange={(value) => setAttributes({ cardShadow: value })}
						options={[
							{ label: __('None', 'csf-parts'), value: 'none' },
							{ label: __('Small', 'csf-parts'), value: 'sm' },
							{ label: __('Medium', 'csf-parts'), value: 'md' },
							{ label: __('Large', 'csf-parts'), value: 'lg' },
							{ label: __('Extra Large', 'csf-parts'), value: 'xl' }
						]}
						help={__('Drop shadow intensity', 'csf-parts')}
					/>
				</PanelBody>

				<PanelBody title={__('Spacing', 'csf-parts')} initialOpen={false}>
					<BoxControl
						label={__('Block Padding', 'csf-parts')}
						values={blockPadding}
						onChange={(value) => setAttributes({ blockPadding: value })}
						units={[{ value: 'px', label: 'px' }]}
					/>
					<BoxControl
						label={__('Block Margin', 'csf-parts')}
						values={blockMargin}
						onChange={(value) => setAttributes({ blockMargin: value })}
						units={[{ value: 'px', label: 'px' }]}
					/>
				</PanelBody>

				<PanelBody title={__('Visibility', 'csf-parts')} initialOpen={false}>
					<ToggleControl
						label={__('Hide on Mobile', 'csf-parts')}
						checked={hideOnMobile}
						onChange={(value) => setAttributes({ hideOnMobile: value })}
						help={__('Hide this block on mobile devices (< 768px)', 'csf-parts')}
					/>
					<ToggleControl
						label={__('Hide on Tablet', 'csf-parts')}
						checked={hideOnTablet}
						onChange={(value) => setAttributes({ hideOnTablet: value })}
						help={__('Hide this block on tablets (768px - 1024px)', 'csf-parts')}
					/>
					<ToggleControl
						label={__('Hide on Desktop', 'csf-parts')}
						checked={hideOnDesktop}
						onChange={(value) => setAttributes({ hideOnDesktop: value })}
						help={__('Hide this block on desktop (> 1024px)', 'csf-parts')}
					/>
				</PanelBody>

				<PanelBody title={__('Animation & Colors', 'csf-parts')} initialOpen={false}>
					<SelectControl
						label={__('Scroll Animation', 'csf-parts')}
						value={scrollAnimation}
						onChange={(value) => setAttributes({ scrollAnimation: value })}
						options={[
							{ label: __('None', 'csf-parts'), value: 'none' },
							{ label: __('Fade In', 'csf-parts'), value: 'fade' },
							{ label: __('Slide Up', 'csf-parts'), value: 'slideUp' },
							{ label: __('Slide Left', 'csf-parts'), value: 'slideLeft' }
						]}
						help={__('Animation when scrolling into view', 'csf-parts')}
					/>
					<SelectControl
						label={__('Color Scheme', 'csf-parts')}
						value={colorScheme}
						onChange={(value) => setAttributes({ colorScheme: value })}
						options={[
							{ label: __('Default', 'csf-parts'), value: 'default' },
							{ label: __('Light', 'csf-parts'), value: 'light' },
							{ label: __('Dark', 'csf-parts'), value: 'dark' },
							{ label: __('Brand', 'csf-parts'), value: 'brand' }
						]}
						help={__('Preset color scheme for cards', 'csf-parts')}
					/>
				</PanelBody>

				<PanelBody title={__('Advanced', 'csf-parts')} initialOpen={false}>
					<TextControl
						label={__('Button Text', 'csf-parts')}
						value={buttonText}
						onChange={(value) => setAttributes({ buttonText: value })}
						help={__('Only shown if filters are visible', 'csf-parts')}
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
				block="csf-parts/product-catalog"
				attributes={attributes}
			/>
		</div>
	);
}
