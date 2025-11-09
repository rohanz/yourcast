/**
 * Frontend Application Configuration
 * 
 * Centralized configuration for the Next.js frontend application.
 * Environment-specific values are loaded from environment variables.
 */

export interface AppConfig {
  api: {
    baseUrl: string;
    timeout: number;
  };
  ui: {
    animations: {
      fast: number;
      medium: number;
      slow: number;
      verySlow: number;
      fade: number;
      arrowRotation: number;
    };
    layout: {
      maxWidth: string;
      gridColumns: {
        mobile: number;
        tablet: number;
        desktop: number;
      };
    };
    player: {
      defaultSpeed: number;
      speedOptions: number[];
      seekStep: number;
    };
    forms: {
      maxSelections: number;
      validationDelay: number;
      autoSaveDelay: number;
    };
  };
  limits: {
    defaultEpisodeDuration: number;
    apiRequestTimeout: number;
    selectionLimit: number;
  };
}

const createConfig = (): AppConfig => {
  const environment = process.env.NODE_ENV || 'development';
  
  // Base configuration
  const baseConfig: AppConfig = {
    api: {
      baseUrl: process.env.API_BASE_URL || 'http://localhost:8000',
      timeout: parseInt(process.env.API_TIMEOUT || '30000'),
    },
    ui: {
      animations: {
        fast: 200,
        medium: 300,
        slow: 700,
        verySlow: 1000,
        fade: 100,
        arrowRotation: 300,
      },
      layout: {
        maxWidth: '4xl',
        gridColumns: {
          mobile: 2,
          tablet: 3,
          desktop: 4,
        },
      },
      player: {
        defaultSpeed: 1.0,
        speedOptions: [0.75, 1.0, 1.25, 1.5, 2.0],
        seekStep: 10,
      },
      forms: {
        maxSelections: 8,
        validationDelay: 500,
        autoSaveDelay: 2000,
      },
    },
    limits: {
      defaultEpisodeDuration: 5,
      apiRequestTimeout: 30000,
      selectionLimit: 8,
    },
  };

  // Environment-specific overrides
  if (environment === 'production') {
    baseConfig.api.timeout = 60000; // Longer timeout for production
    baseConfig.limits.apiRequestTimeout = 60000;
  } else if (environment === 'development') {
    baseConfig.api.timeout = 15000; // Shorter timeout for dev
    baseConfig.limits.apiRequestTimeout = 15000;
  }

  return baseConfig;
};

// Export singleton instance
export const appConfig = createConfig();

// Convenience getters
export const getApiConfig = () => appConfig.api;
export const getUIConfig = () => appConfig.ui;
export const getLimitsConfig = () => appConfig.limits;

// Environment helpers
export const isDevelopment = () => process.env.NODE_ENV === 'development';
export const isProduction = () => process.env.NODE_ENV === 'production';