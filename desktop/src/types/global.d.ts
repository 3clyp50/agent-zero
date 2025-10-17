import type { ContainerRuntimeBridge } from '../shared/runtime-types';

declare global {
  interface Window {
    containerRuntime?: ContainerRuntimeBridge;
  }
}

export {};
