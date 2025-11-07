import { contextBridge, ipcRenderer, IpcRendererEvent } from "electron";
import type {
  DockerProgressEvent,
  DockerListResult,
  DockerRemoveResult,
  IpcResponse,
} from "../common/dockerTypes";

function subscribe<T>(channel: string, listener: (event: IpcRendererEvent, payload: T) => void): () => void {
  const wrapped = (event: IpcRendererEvent, ...args: unknown[]) => {
    listener(event, args[0] as T);
  };
  ipcRenderer.on(channel, wrapped);
  return () => {
    ipcRenderer.removeListener(channel, wrapped);
  };
}

contextBridge.exposeInMainWorld("electronAPI", {
  pullDockerImage: (): Promise<IpcResponse<void>> => ipcRenderer.invoke("docker:pull"),
  startDockerContainer: (): Promise<IpcResponse<{ containerId?: string; startedExisting: boolean }>> =>
    ipcRenderer.invoke("docker:start"),
  stopDockerContainer: (): Promise<IpcResponse<{ stopped: boolean }>> => ipcRenderer.invoke("docker:stop"),
  removeDockerResources: (): Promise<IpcResponse<DockerRemoveResult>> => ipcRenderer.invoke("docker:remove"),
  listDockerResources: (): Promise<IpcResponse<DockerListResult>> => ipcRenderer.invoke("docker:list"),
  onDockerPullProgress: (callback: (event: DockerProgressEvent) => void): (() => void) =>
    subscribe<DockerProgressEvent>("docker:pull-progress", (_event, payload) => {
      callback(payload);
    }),
});

declare global {
  interface Window {
    electronAPI: {
      pullDockerImage: () => Promise<IpcResponse<void>>;
      startDockerContainer: () => Promise<IpcResponse<{ containerId?: string; startedExisting: boolean }>>;
      stopDockerContainer: () => Promise<IpcResponse<{ stopped: boolean }>>;
      removeDockerResources: () => Promise<IpcResponse<DockerRemoveResult>>;
      listDockerResources: () => Promise<IpcResponse<DockerListResult>>;
      onDockerPullProgress: (callback: (event: DockerProgressEvent) => void) => () => void;
    };
  }
}
