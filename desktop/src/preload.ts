import { contextBridge, ipcRenderer } from 'electron';
import type {
  ContainerRuntimeBridge,
  RuntimeContainer,
  RuntimeImage,
  RuntimeListResponse,
  RuntimeVolume,
} from './shared/runtime-types';

type ChannelMap = {
  images: 'runtime:list-images';
  containers: 'runtime:list-containers';
  volumes: 'runtime:list-volumes';
};

const CHANNELS: ChannelMap = {
  images: 'runtime:list-images',
  containers: 'runtime:list-containers',
  volumes: 'runtime:list-volumes',
};

const invoke = <T>(channel: ChannelMap[keyof ChannelMap]): Promise<RuntimeListResponse<T>> => {
  return ipcRenderer.invoke(channel) as Promise<RuntimeListResponse<T>>;
};

const bridge: ContainerRuntimeBridge = {
  listImages: () => invoke<RuntimeImage>(CHANNELS.images),
  listContainers: () => invoke<RuntimeContainer>(CHANNELS.containers),
  listVolumes: () => invoke<RuntimeVolume>(CHANNELS.volumes),
};

contextBridge.exposeInMainWorld('containerRuntime', Object.freeze(bridge));
