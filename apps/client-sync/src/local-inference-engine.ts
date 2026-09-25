export type LocalInferenceRequest = {
  text: string;
  languageTag: string;
  modelPackageId: string;
  signal?: AbortSignal;
  maxOutputTokens?: number;
};

export type LocalInferenceResult = {
  text: string;
  modelPackageId: string;
  modelVersion: string;
};

export interface LocalTextInferenceEngine {
  load(
    modelPackageId: string,
    modelVersion: string,
    artifact: Uint8Array,
  ): Promise<void>;
  unload(modelPackageId: string): Promise<void>;
  isLoaded(modelPackageId: string, modelVersion: string): boolean;
  complete(request: LocalInferenceRequest): Promise<LocalInferenceResult>;
}

export type LocalVoiceInputRequest = {
  audio: Uint8Array;
  languageTag: string;
  modelPackageId: string;
  signal?: AbortSignal;
};

export type LocalVoiceOutputRequest = {
  text: string;
  languageTag: string;
  modelPackageId: string;
  signal?: AbortSignal;
};

export type LocalVoiceInputResult = {
  text: string;
  modelPackageId: string;
  modelVersion: string;
};

export interface LocalVoiceEngine {
  loadInput(
    modelPackageId: string,
    modelVersion: string,
    artifact: Uint8Array,
  ): Promise<void>;
  loadOutput(
    modelPackageId: string,
    modelVersion: string,
    artifact: Uint8Array,
  ): Promise<void>;
  unloadInput(modelPackageId: string): Promise<void>;
  unloadOutput(modelPackageId: string): Promise<void>;
  isInputLoaded(modelPackageId: string, modelVersion: string): boolean;
  isOutputLoaded(modelPackageId: string, modelVersion: string): boolean;
  transcribe(request: LocalVoiceInputRequest): Promise<LocalVoiceInputResult>;
  synthesize(request: LocalVoiceOutputRequest): Promise<Uint8Array>;
}
