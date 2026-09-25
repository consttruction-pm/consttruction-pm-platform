import {
  ClientLanguageRuntime,
} from "../../client-sync/src/language-runtime.js";
import {
  IndexedDbLanguagePackStore,
} from "./language-pack-store.js";

export class WebLanguageRuntime {
  readonly language: ClientLanguageRuntime;

  constructor(databaseName?: string) {
    this.language = new ClientLanguageRuntime(
      new IndexedDbLanguagePackStore(databaseName),
    );
  }
}
