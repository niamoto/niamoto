import { API_BASE_URL } from '@/lib/api-config';

export interface ImportConfig {
  taxonomy?: {
    path: string;
    hierarchy?: {
      levels: Array<{ name: string; column: string }>;
      taxon_id_column?: string;
      authors_column?: string;
    };
    api_enrichment?: {
      enabled: boolean;
      plugin: string;
      api_key?: string;
      query_field?: string;
      rate_limit?: number;
      cache_results?: boolean;
      include_images?: boolean;
      include_synonyms?: boolean;
      include_distributions?: boolean;
      include_references?: boolean;
    };
  };
  plots?: {
    type: string;
    path: string;
    identifier: string;
    locality_field: string;
    location_field: string;
    link_field?: string;
    occurrence_link_field?: string;
    hierarchy?: {
      enabled: boolean;
      levels: string[];
      aggregate_geometry: boolean;
    };
  };
  occurrences?: {
    type: string;
    path: string;
    identifier: string;
    location_field: string;
    plot_field?: string;
  };
  shapes?: Array<{
    type: string;
    path: string;
    name_field: string;
    id_field?: string;
    properties?: string[];
  }>;
}

export interface TransformConfig {
  groups: Record<string, any>;
}

export interface ExportConfig {
  exports: any[];
  static_pages: any[];
}

class ConfigService {
  async getImportConfig(): Promise<ImportConfig> {
    const response = await fetch(`${API_BASE_URL}/config/import`);
    if (!response.ok) {
      throw new Error('Failed to fetch import configuration');
    }
    return response.json();
  }

  async updateImportConfig(config: ImportConfig): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/config/import`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        content: config,
        backup: true,
      }),
    });

    if (!response.ok) {
      throw new Error('Failed to update import configuration');
    }
    return response.json();
  }

  async getTransformConfig(): Promise<TransformConfig> {
    const response = await fetch(`${API_BASE_URL}/config/transform`);
    if (!response.ok) {
      throw new Error('Failed to fetch transform configuration');
    }
    return response.json();
  }

  async updateTransformConfig(config: TransformConfig): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/config/transform`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        content: config,
        backup: true,
      }),
    });

    if (!response.ok) {
      throw new Error('Failed to update transform configuration');
    }
    return response.json();
  }

  async getExportConfig(): Promise<ExportConfig> {
    const response = await fetch(`${API_BASE_URL}/config/export`);
    if (!response.ok) {
      throw new Error('Failed to fetch export configuration');
    }
    return response.json();
  }

  async updateExportConfig(config: ExportConfig): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/config/export`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        content: config,
        backup: true,
      }),
    });

    if (!response.ok) {
      throw new Error('Failed to update export configuration');
    }
    return response.json();
  }

  async validateConfig(configType: 'import' | 'transform' | 'export', config: any): Promise<{
    valid: boolean;
    errors: string[];
    warnings: string[];
  }> {
    const response = await fetch(`${API_BASE_URL}/config/${configType}/validate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(config),
    });

    if (!response.ok) {
      throw new Error(`Failed to validate ${configType} configuration`);
    }
    return response.json();
  }

  // Parse import config to populate the Import UI state
  parseImportConfigToState(config: ImportConfig): any {
    const state: any = {
      occurrences: {
        file: null,
        fieldMappings: {},
        taxonomyHierarchy: {
          ranks: [],
          mappings: {}
        },
        apiEnrichment: {
          enabled: false
        }
      }
    };

    // Parse taxonomy configuration
    if (config.taxonomy) {
      if (config.taxonomy.hierarchy) {
        // Extract ranks and mappings
        config.taxonomy.hierarchy.levels.forEach(level => {
          state.occurrences.taxonomyHierarchy.ranks.push(level.name);
          state.occurrences.taxonomyHierarchy.mappings[level.name] = level.column;
        });

        // Add special columns
        if (config.taxonomy.hierarchy.taxon_id_column) {
          state.occurrences.fieldMappings.taxon_id = config.taxonomy.hierarchy.taxon_id_column;
        }
        if (config.taxonomy.hierarchy.authors_column) {
          state.occurrences.fieldMappings.authors = config.taxonomy.hierarchy.authors_column;
        }
      }

      // Parse API enrichment
      if (config.taxonomy.api_enrichment) {
        state.occurrences.apiEnrichment = config.taxonomy.api_enrichment;
      }
    }

    // Parse occurrences configuration
    if (config.occurrences) {
      state.occurrences.fieldMappings.location = config.occurrences.location_field;
      if (config.occurrences.plot_field) {
        state.occurrences.fieldMappings.plot_name = config.occurrences.plot_field;
      }
    }

    // Parse plots configuration
    if (config.plots) {
      state.plots = {
        file: null,
        fieldMappings: {
          identifier: config.plots.identifier,
          locality: config.plots.locality_field,
          location: config.plots.location_field,
        },
        hierarchy: config.plots.hierarchy || { enabled: false, levels: [] }
      };

      if (config.plots.link_field) {
        state.plots.linkField = config.plots.link_field;
      }
      if (config.plots.occurrence_link_field) {
        state.plots.occurrenceLinkField = config.plots.occurrence_link_field;
      }
    }

    // Parse shapes configuration
    if (config.shapes && config.shapes.length > 0) {
      state.shapes = config.shapes.map(shape => ({
        file: null,
        fieldMappings: {
          name: shape.name_field,
          id: shape.id_field || '',
          type: shape.type
        },
        properties: shape.properties || []
      }));
    }

    return state;
  }
}

export const configService = new ConfigService();
