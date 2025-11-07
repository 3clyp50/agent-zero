import type { ContainerRuntimeBridge } from '../shared/runtime-types';

declare global {
  interface Window {
    readonly containerRuntime?: ContainerRuntimeBridge;
  }
}

export {};
