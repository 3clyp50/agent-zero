import { contextBridge, ipcRenderer } from 'electron';
import type {
  ContainerRuntimeBridge,
  RuntimeContainer,
  RuntimeImage,
  RuntimeListResponse,
  RuntimeVolume,
} from './shared/runtime-types';

const CHANNELS = {
  images: 'runtime:list-images',
  containers: 'runtime:list-containers',
  volumes: 'runtime:list-volumes',
} as const;

// Runtime validators to ensure untrusted IPC data is validated before use
const isNonNullObject = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null;

const isString = (value: unknown): value is string => typeof value === 'string';

const isContainerRuntime = (value: unknown): value is import('./shared/runtime-types').ContainerRuntime =>
  value === 'docker' || value === 'podman';

const isRuntimeImage = (value: unknown): value is RuntimeImage => {
  if (!isNonNullObject(value)) return false;
  const v = value as Record<string, unknown>;
  return (
    isString(v.id) &&
    isString(v.repository) &&
    isString(v.tag) &&
    (v.createdAt === undefined || isString(v.createdAt)) &&
    (v.size === undefined || isString(v.size))
  );
};

const isRuntimeContainer = (value: unknown): value is RuntimeContainer => {
  if (!isNonNullObject(value)) return false;
  const v = value as Record<string, unknown>;
  return (
    isString(v.id) &&
    isString(v.name) &&
    isString(v.image) &&
    (v.state === undefined || isString(v.state)) &&
    (v.status === undefined || isString(v.status)) &&
    (v.createdAt === undefined || isString(v.createdAt))
  );
};

const isRuntimeVolume = (value: unknown): value is RuntimeVolume => {
  if (!isNonNullObject(value)) return false;
  const v = value as Record<string, unknown>;
  return (
    isString(v.name) &&
    (v.driver === undefined || isString(v.driver)) &&
    (v.mountpoint === undefined || isString(v.mountpoint))
  );
};

const isRuntimeListResponse = <T>(
  value: unknown,
  isItem: (v: unknown) => v is T,
): value is RuntimeListResponse<T> => {
  if (!isNonNullObject(value)) return false;
  const v = value as Record<string, unknown>;
  const runtime = v.runtime as unknown;
  const items = v.items as unknown;
  const error = v.error as unknown;

  if (!(runtime === null || isContainerRuntime(runtime))) return false;
  if (!Array.isArray(items) || !items.every(isItem)) return false;
  if (!(error === undefined || isString(error))) return false;
  return true;
};

const asTypedError = <T>(message: string): RuntimeListResponse<T> => ({
  runtime: null,
  items: [],
  error: message,
});

const invokeValidated = async <T>(
  channel: typeof CHANNELS[keyof typeof CHANNELS],
  isItem: (v: unknown) => v is T,
): Promise<RuntimeListResponse<T>> => {
  try {
    const raw = await ipcRenderer.invoke(channel);
    if (isRuntimeListResponse<T>(raw, isItem)) {
      return raw;
    }
    return asTypedError<T>(`Invalid response received for channel \"${channel}\"`);
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown IPC error';
    return asTypedError<T>(message);
  }
};

const bridge: ContainerRuntimeBridge = {
  listImages: () => invokeValidated<RuntimeImage>(CHANNELS.images, isRuntimeImage),
  listContainers: () => invokeValidated<RuntimeContainer>(CHANNELS.containers, isRuntimeContainer),
  listVolumes: () => invokeValidated<RuntimeVolume>(CHANNELS.volumes, isRuntimeVolume),
};

contextBridge.exposeInMainWorld('containerRuntime', Object.freeze(bridge));
