<?php
/**
 * Design tokens, presets, and the CSS that applies them.
 *
 * The plugin's component CSS reads only --csf-* custom properties. This class
 * owns the catalogue of tokens an administrator may override, the named
 * presets that supply coordinated values, and the inline CSS that pushes the
 * resolved values into the page after the base and dark stylesheets.
 *
 * Everything here except get_settings() is static and pure so it can be unit
 * tested without WordPress.
 *
 * @package CSF_Parts_Catalog
 * @since   1.9.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

/**
 * Class CSF_Parts_Design
 */
class CSF_Parts_Design {

	public const TYPE_COLOR  = 'color';
	public const TYPE_LENGTH = 'length';

	/** Maximum value, in px, accepted for a length token. */
	private const LENGTH_MAX_PX = 64;

	/**
	 * Tokens whose overrides apply in dark mode as well as light.
	 * Brand colours are a deliberate choice that should survive the scheme switch;
	 * everything else has a dedicated dark value in the preset or stylesheet.
	 */
	private const BOTH_SCHEMES = array( 'primary', 'secondary', 'accent', 'on-primary', 'on-secondary', 'on-accent', 'radius-sm', 'radius-md', 'radius-lg' );

	/**
	 * Token catalogue, in display order.
	 *
	 * Keys are the token name without the --csf- prefix.
	 *
	 * @return array<string, array{label: string, type: string, group: string, help: string}>
	 */
	public static function tokens(): array {
		return array(
			'primary'        => array( 'label' => 'Primary', 'type' => self::TYPE_COLOR, 'group' => 'Brand', 'help' => 'Buttons, links, highlights. Inherits Kadence palette 1.' ),
			'on-primary'     => array( 'label' => 'Text on primary', 'type' => self::TYPE_COLOR, 'group' => 'Brand', 'help' => 'Text placed on a primary-coloured background.' ),
			'secondary'      => array( 'label' => 'Secondary', 'type' => self::TYPE_COLOR, 'group' => 'Brand', 'help' => 'Pagination, tabs, year badges, focus rings. Inherits Kadence palette 2.' ),
			'on-secondary'   => array( 'label' => 'Text on secondary', 'type' => self::TYPE_COLOR, 'group' => 'Brand', 'help' => 'Text placed on a secondary-coloured background.' ),
			'accent'         => array( 'label' => 'Accent', 'type' => self::TYPE_COLOR, 'group' => 'Brand', 'help' => 'Notices such as "possible match" and engine confirmation.' ),
			'on-accent'      => array( 'label' => 'Text on accent', 'type' => self::TYPE_COLOR, 'group' => 'Brand', 'help' => 'Text placed on an accent-coloured background.' ),
			'text'           => array( 'label' => 'Text', 'type' => self::TYPE_COLOR, 'group' => 'Text', 'help' => 'Headings and body copy. Inherits Kadence palette 3.' ),
			'text-secondary' => array( 'label' => 'Text secondary', 'type' => self::TYPE_COLOR, 'group' => 'Text', 'help' => 'Inherits Kadence palette 4.' ),
			'text-muted'     => array( 'label' => 'Text muted', 'type' => self::TYPE_COLOR, 'group' => 'Text', 'help' => 'Labels, helper text, ellipses. Inherits Kadence palette 5.' ),
			'bg'             => array( 'label' => 'Page background', 'type' => self::TYPE_COLOR, 'group' => 'Surfaces', 'help' => 'Inherits Kadence palette 8.' ),
			'bg-alt'         => array( 'label' => 'Background alt', 'type' => self::TYPE_COLOR, 'group' => 'Surfaces', 'help' => 'Spec boxes, description panels, disabled controls. Inherits Kadence palette 7.' ),
			'surface'        => array( 'label' => 'Surface', 'type' => self::TYPE_COLOR, 'group' => 'Surfaces', 'help' => 'Cards, inputs, panels. Inherits Kadence palette 9.' ),
			'border'         => array( 'label' => 'Border', 'type' => self::TYPE_COLOR, 'group' => 'Surfaces', 'help' => 'Card and input borders.' ),
			'inverse-bg'     => array( 'label' => 'Inverse panel', 'type' => self::TYPE_COLOR, 'group' => 'Surfaces', 'help' => 'A dark panel on a light page, like the contact page "Direct lines" card.' ),
			'inverse-text'   => array( 'label' => 'Inverse panel text', 'type' => self::TYPE_COLOR, 'group' => 'Surfaces', 'help' => 'Text inside an inverse panel.' ),
			'success'        => array( 'label' => 'Success', 'type' => self::TYPE_COLOR, 'group' => 'Status', 'help' => 'In stock, confirmed fitment.' ),
			'error'          => array( 'label' => 'Error', 'type' => self::TYPE_COLOR, 'group' => 'Status', 'help' => 'Reset button, discontinued, validation errors.' ),
			'radius-sm'      => array( 'label' => 'Radius small', 'type' => self::TYPE_LENGTH, 'group' => 'Shape', 'help' => 'Buttons, inputs, selects, small notices (px).' ),
			'radius-md'      => array( 'label' => 'Radius medium', 'type' => self::TYPE_LENGTH, 'group' => 'Shape', 'help' => 'Corner badges and thumbnails inside cards (px).' ),
			'radius-lg'      => array( 'label' => 'Radius large', 'type' => self::TYPE_LENGTH, 'group' => 'Shape', 'help' => 'Cards, panels, gallery, sections (px).' ),
		);
	}

	/**
	 * Named presets.
	 *
	 * "kadence" is intentionally empty: the base stylesheet already inherits the
	 * theme palette, so the preset simply applies no overrides.
	 *
	 * @return array<string, array{label: string, description: string, light: array<string, string>, dark: array<string, string>}>
	 */
	public static function presets(): array {
		return array(
			'kadence' => array(
				'label'       => 'Inherit theme palette',
				'description' => 'Colours follow the Kadence Global Palette slots. No overrides.',
				'light'       => array(),
				'dark'        => array(),
			),
			'csf-red' => array(
				'label'       => 'CSF Red',
				'description' => 'Matches the About and Contact page design: CSF red accents, navy inverse panels, Exo/Open Sans typography from the theme, 16px cards and 3px buttons.',
				'light'       => array(
					'primary'        => '#CF2E2E',
					'on-primary'     => '#FCFCFC',
					'secondary'      => '#2D3748',
					'on-secondary'   => '#FCFCFC',
					'accent'         => '#D97706',
					'on-accent'      => '#1A202C',
					'text'           => '#1A202C',
					'text-secondary' => '#2D3748',
					'text-muted'     => '#4A5568',
					'bg'             => '#F7FAFC',
					'bg-alt'         => '#F1F2F2',
					'surface'        => '#FCFCFC',
					'border'         => '#E2E8F0',
					'inverse-bg'     => '#2D3748',
					'inverse-text'   => '#FCFCFC',
					'success'        => '#16A34A',
					'error'          => '#CF2E2E',
					'radius-sm'      => '3px',
					'radius-md'      => '10px',
					'radius-lg'      => '16px',
				),
				'dark'        => array(
					'primary'      => '#F05252',
					'on-primary'   => '#FFFFFF',
					'secondary'    => '#90CDF4',
					'on-secondary' => '#0B1220',
					'inverse-bg'   => '#0F172A',
					'inverse-text' => '#F0F0F1',
				),
			),
		);
	}

	/**
	 * Settings shape with defaults.
	 *
	 * @return array{preset: string, overrides: array<string, string>}
	 */
	public static function default_settings(): array {
		return array(
			'preset'    => CSF_Parts_Constants::DESIGN_PRESET_DEFAULT,
			'overrides' => array(),
		);
	}

	/**
	 * Coerce raw (form or option) input into valid settings.
	 *
	 * Unknown tokens and invalid values are dropped; an empty override means
	 * "use the preset value" and is dropped too.
	 *
	 * @param array<string, mixed> $raw Raw input.
	 * @return array{preset: string, overrides: array<string, string>}
	 */
	public static function sanitize_settings( array $raw ): array {
		$settings = self::default_settings();

		$preset = isset( $raw['preset'] ) ? (string) $raw['preset'] : '';
		if ( array_key_exists( $preset, self::presets() ) ) {
			$settings['preset'] = $preset;
		}

		$overrides = isset( $raw['overrides'] ) && is_array( $raw['overrides'] ) ? $raw['overrides'] : array();
		foreach ( self::tokens() as $token => $meta ) {
			if ( ! isset( $overrides[ $token ] ) ) {
				continue;
			}
			$value = self::sanitize_value( (string) $overrides[ $token ], $meta['type'] );
			if ( '' !== $value ) {
				$settings['overrides'][ $token ] = $value;
			}
		}

		return $settings;
	}

	/**
	 * Validate a single token value.
	 *
	 * @param string $value Raw value.
	 * @param string $type  One of the TYPE_* constants.
	 * @return string Normalised value, or '' when invalid/empty.
	 */
	public static function sanitize_value( string $value, string $type ): string {
		$value = trim( $value );
		if ( '' === $value ) {
			return '';
		}

		if ( self::TYPE_COLOR === $type ) {
			return preg_match( '/^#([0-9a-f]{3}|[0-9a-f]{6})$/i', $value ) ? strtoupper( $value ) : '';
		}

		if ( self::TYPE_LENGTH === $type ) {
			if ( ! preg_match( '/^(\d{1,3})(?:px)?$/', $value, $m ) ) {
				return '';
			}
			$px = min( (int) $m[1], self::LENGTH_MAX_PX );
			return $px . 'px';
		}

		return '';
	}

	/**
	 * Merge preset values with overrides into per-scheme token maps.
	 *
	 * @param array<string, mixed> $settings Sanitized settings.
	 * @return array{light: array<string, string>, dark: array<string, string>}
	 */
	public static function resolve( array $settings ): array {
		$settings  = self::sanitize_settings( $settings );
		$presets   = self::presets();
		$preset    = $presets[ $settings['preset'] ];
		$overrides = $settings['overrides'];

		$light = array_merge( $preset['light'], $overrides );

		$dark = $preset['dark'];
		foreach ( $overrides as $token => $value ) {
			if ( in_array( $token, self::BOTH_SCHEMES, true ) ) {
				$dark[ $token ] = $value;
			}
		}

		return array(
			'light' => $light,
			'dark'  => $dark,
		);
	}

	/**
	 * Build the inline CSS for the resolved tokens.
	 *
	 * Light values go on :root unconditionally. Dark values are wrapped to match
	 * how the dark stylesheet is gated by the Color Scheme setting.
	 *
	 * @param array<string, mixed> $settings Sanitized settings.
	 * @param string               $scheme   One of CSF_Parts_Constants::COLOR_SCHEMES.
	 * @return string CSS, possibly empty.
	 */
	public static function build_css( array $settings, string $scheme ): string {
		$resolved = self::resolve( $settings );
		$css      = self::declarations_block( $resolved['light'] );

		if ( CSF_Parts_Constants::COLOR_SCHEME_LIGHT === $scheme || empty( $resolved['dark'] ) ) {
			return $css;
		}

		$dark_block = self::declarations_block( $resolved['dark'] );
		if ( CSF_Parts_Constants::COLOR_SCHEME_DARK === $scheme ) {
			return $css . $dark_block;
		}

		return $css . '@media (prefers-color-scheme: dark){' . $dark_block . '}';
	}

	/**
	 * Render a :root declaration block.
	 *
	 * @param array<string, string> $tokens Token => value.
	 * @return string
	 */
	private static function declarations_block( array $tokens ): string {
		if ( empty( $tokens ) ) {
			return '';
		}
		$decls = '';
		foreach ( $tokens as $token => $value ) {
			$decls .= sprintf( '--csf-%s:%s;', $token, $value );
		}
		return ':root{' . $decls . '}';
	}

	/**
	 * Current settings from the database, sanitized.
	 *
	 * @return array{preset: string, overrides: array<string, string>}
	 */
	public function get_settings(): array {
		$stored = get_option( CSF_Parts_Constants::OPTION_DESIGN, array() );
		return self::sanitize_settings( is_array( $stored ) ? $stored : array() );
	}

	/**
	 * Inline CSS for the current settings and scheme.
	 *
	 * @param string $scheme One of CSF_Parts_Constants::COLOR_SCHEMES.
	 * @return string
	 */
	public function inline_css( string $scheme ): string {
		return self::build_css( $this->get_settings(), $scheme );
	}
}
