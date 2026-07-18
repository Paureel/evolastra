/// <reference lib="webworker" />
import { layoutScene } from "./layout";
import type { SceneEntity, SpaceMapMode } from "./types";

self.onmessage = (event: MessageEvent<{ entities: SceneEntity[]; seed: number; mode: SpaceMapMode; focusSystemId?: string }>) => {
  self.postMessage(layoutScene(event.data.entities, event.data.seed, event.data.mode, event.data.focusSystemId));
};

export {};
