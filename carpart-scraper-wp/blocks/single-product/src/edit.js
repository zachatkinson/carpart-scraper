import { useBlockProps, InspectorControls } from '@wordpress/block-editor';
import { PanelBody, ToggleControl, Placeholder, ComboboxControl, Spinner, Button } from '@wordpress/components';
import { __ } from '@wordpress/i18n';
import { useState, useMemo, useCallback, useEffect } from '@wordpress/element';
import { copy } from '@wordpress/icons';
import apiFetch from '@wordpress/api-fetch';
import ServerSideRender from '@wordpress/server-side-render';

/**
 * Single Product Block Editor Component (V2 Architecture).
 *
 * Fetches parts from custom REST API endpoint instead of WordPress posts.
 */
export default function Edit({ attributes, setAttributes }) {
	const blockProps = useBlockProps();
	const { sku, showPrice, showSpecs, showFeatures } = attributes;
	const [searchTerm, setSearchTerm] = useState('');
	const [debouncedSearchTerm, setDebouncedSearchTerm] = useState('');
	const [copySuccess, setCopySuccess] = useState(false);
	const [parts, setParts] = useState([]);
	const [isLoading, setIsLoading] = useState(true);

	// Fetch all parts from V2 REST API
	useEffect(() => {
		setIsLoading(true);
		apiFetch({ path: '/csf/v1/parts?per_page=100' })
			.then((response) => {
				setParts(response.parts || []);
				setIsLoading(false);
			})
			.catch((error) => {
				console.error('Error fetching parts:', error);
				setIsLoading(false);
			});
	}, []);

	// Debounce search term for better performance
	useEffect(() => {
		const timer = setTimeout(() => {
			setDebouncedSearchTerm(searchTerm);
		}, 300);

		return () => clearTimeout(timer);
	}, [searchTerm]);

	// Copy SKU to clipboard
	const copySKU = useCallback(() => {
		if (sku) {
			navigator.clipboard.writeText(sku).then(() => {
				setCopySuccess(true);
				setTimeout(() => setCopySuccess(false), 2000);
			});
		}
	}, [sku]);

	// Keyboard shortcuts
	useEffect(() => {
		const handleKeyDown = (event) => {
			// ESC to clear selection when focused on the block
			if (event.key === 'Escape' && sku) {
				event.preventDefault();
				setAttributes({ sku: '' });
				setSearchTerm('');
			}
		};

		document.addEventListener('keydown', handleKeyDown);
		return () => document.removeEventListener('keydown', handleKeyDown);
	}, [sku, setAttributes]);

	// Create searchable options
	const allOptions = useMemo(() => {
		if (!parts || parts.length === 0) return [];

		return parts.map((part) => {
			const searchableText = [
				part.name,
				part.sku,
				part.manufacturer,
				part.category,
			]
				.filter(Boolean)
				.join(' ')
				.toLowerCase();

			return {
				value: part.sku,
				label: `${part.name} (${part.sku}) - ${part.category}`,
				searchableText,
				part,
			};
		});
	}, [parts]);

	// Filter options based on debounced search term
	const filteredOptions = useMemo(() => {
		if (!debouncedSearchTerm) return allOptions.slice(0, 20);

		const lowerSearch = debouncedSearchTerm.toLowerCase();
		return allOptions
			.filter((option) => option.searchableText.includes(lowerSearch))
			.slice(0, 50);
	}, [allOptions, debouncedSearchTerm]);

	// Find the currently selected product
	const selectedProduct = parts?.find((part) => part.sku === sku);

	// Get current display value
	const currentValue = selectedProduct
		? allOptions.find((opt) => opt.value === sku)?.label || sku
		: sku;

	return (
		<div {...blockProps}>
			<InspectorControls>
				<PanelBody title={__('Product Selection', 'csf-parts')}>
					{isLoading ? (
						<div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
							<Spinner />
							<span>{__('Loading products...', 'csf-parts')}</span>
						</div>
					) : (
						<>
							<ComboboxControl
								label={__('Search for Product', 'csf-parts')}
								value={sku}
								onChange={(newSku) => setAttributes({ sku: newSku })}
								options={filteredOptions}
								onFilterValueChange={setSearchTerm}
								help={__(
									'Type to search by name, SKU, make, model, or year. You can paste a SKU directly.',
									'csf-parts'
								)}
								placeholder={__('Search or enter SKU...', 'csf-parts')}
							/>

							{parts.length === 0 && !isLoading && (
								<p style={{ fontSize: '13px', color: '#757575', marginTop: '12px' }}>
									{__('No products found.', 'csf-parts')}{' '}
									<a href="/wp-admin/admin.php?page=csf-parts-import">
										{__('Add your first product', 'csf-parts')} →
									</a>
								</p>
							)}
						</>
					)}
				</PanelBody>

				<PanelBody title={__('Display Settings', 'csf-parts')}>
					<ToggleControl
						label={__('Show Price', 'csf-parts')}
						checked={showPrice}
						onChange={(value) => setAttributes({ showPrice: value })}
					/>
					<ToggleControl
						label={__('Show Specifications', 'csf-parts')}
						checked={showSpecs}
						onChange={(value) => setAttributes({ showSpecs: value })}
					/>
					<ToggleControl
						label={__('Show Features', 'csf-parts')}
						checked={showFeatures}
						onChange={(value) => setAttributes({ showFeatures: value })}
					/>
				</PanelBody>
			</InspectorControls>

			{!sku ? (
				<Placeholder
					icon="cart"
					label={__('CSF Single Product', 'csf-parts')}
					instructions={__(
						'Display a single automotive part with full details, specifications, and features.',
						'csf-parts'
					)}
				>
					<div style={{ maxWidth: '600px', textAlign: 'left' }}>
						<p style={{ marginBottom: '16px', fontSize: '14px' }}>
							<strong>{__('Quick Start:', 'csf-parts')}</strong>
						</p>
						<ul style={{ fontSize: '13px', lineHeight: '1.6', paddingLeft: '20px' }}>
							<li>{__('Open the block settings panel on the right →', 'csf-parts')}</li>
							<li>{__('Search by product name, SKU, make, model, or year', 'csf-parts')}</li>
							<li>{__('Select a product from the results', 'csf-parts')}</li>
							<li>{__('Customize display options in the settings', 'csf-parts')}</li>
						</ul>
						{parts.length === 0 && !isLoading && (
							<div
								style={{
									marginTop: '16px',
									padding: '12px',
									backgroundColor: '#fff8e5',
									border: '1px solid #f0b849',
									borderRadius: '4px',
								}}
							>
								<p style={{ margin: 0, fontSize: '13px' }}>
									{__('No products found.', 'csf-parts')}{' '}
									<a href="/wp-admin/admin.php?page=csf-parts-import">
										{__('Add your first product', 'csf-parts')} →
									</a>
								</p>
							</div>
						)}
					</div>
				</Placeholder>
			) : (
				<div style={{ border: '1px solid #ddd', borderRadius: '4px', padding: '16px', backgroundColor: '#f9f9f9' }}>
					{selectedProduct && (
						<div style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '12px' }}>
							{selectedProduct.image && (
								<img
									src={selectedProduct.image}
									alt={selectedProduct.name || `${selectedProduct.category} ${sku}`}
									style={{ width: '60px', height: '60px', objectFit: 'cover', borderRadius: '4px' }}
								/>
							)}
							<div style={{ flex: 1 }}>
								<h3 style={{ margin: 0, fontSize: '16px', fontWeight: '600' }}>
									{selectedProduct.name || `${selectedProduct.category} - ${sku}`}
								</h3>
								<p style={{ margin: '4px 0 0', fontSize: '13px', color: '#757575' }}>
									{__('SKU:', 'csf-parts')} {sku}
									{showPrice && selectedProduct.price && (
										<>
											{' | '}
											{__('Price:', 'csf-parts')} ${parseFloat(selectedProduct.price).toFixed(2)}
										</>
									)}
									{' | '}
									{selectedProduct.in_stock
										? __('In Stock', 'csf-parts')
										: __('Out of Stock', 'csf-parts')}
								</p>
							</div>
							<Button
								icon={copy}
								label={copySuccess ? __('Copied!', 'csf-parts') : __('Copy SKU', 'csf-parts')}
								onClick={copySKU}
								variant={copySuccess ? 'primary' : 'secondary'}
								size="small"
							/>
						</div>
					)}

					<ServerSideRender block="csf-parts/single-product" attributes={attributes} />
				</div>
			)}
		</div>
	);
}
