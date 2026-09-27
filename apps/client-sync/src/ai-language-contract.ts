export type AILanguageContext={input_language:string;output_language:string;project_language:string;terminology_profile:string;locale:string;voice_language:string|null;text_capable:boolean;voice_input_capable:boolean;voice_output_capable:boolean;offline_ai_capable:boolean;provenance_context?:Record<string,unknown>|null};
export function requireTextOutput(context:AILanguageContext):void{if(!context.text_capable)throw new Error("AI_TEXT_OUTPUT_UNAVAILABLE");}
export function requireVoiceInput(context:AILanguageContext):void{if(!context.voice_input_capable)throw new Error("AI_VOICE_INPUT_UNAVAILABLE");}
export function requireVoiceOutput(context:AILanguageContext):void{if(!context.voice_output_capable)throw new Error("AI_VOICE_OUTPUT_UNAVAILABLE");}
export function requireOfflineAi(context:AILanguageContext):void{if(!context.offline_ai_capable)throw new Error("AI_OFFLINE_UNAVAILABLE");}
