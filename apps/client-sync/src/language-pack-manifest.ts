export type LanguagePackManifest = {
  package_id: string;
  language_tag: string;
  version: string;
  app_compatibility: {
    min_version: string;
    max_version: string | null;
  };
  artifact: {
    format: "zip" | "zstd" | "tar.zst";
    compressed_size_bytes: number;
    download_uri: string;
    delta_from: string | null;
  };
  resources: {
    translation: string;
    glossary: string;
    help: string;
    reports: string;
    voice_input: string | null;
    voice_output: string | null;
    offline_ai_model: string | null;
  };
  integrity: {
    checksum: string;
    signature: string;
    signing_key_id: string | null;
  };
  capabilities: {
    ui: boolean;
    help: boolean;
    ai_text: boolean;
    voice_input: boolean;
    voice_output: boolean;
    offline_ai: boolean;
  };
  rollback: {
    previous_version: string | null;
    rollback_supported: boolean;
  };
};
