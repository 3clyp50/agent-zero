export const DEFAULT_IMAGE = "agent0ai/agent-zero:latest";
export const DEFAULT_CONTAINER_NAME = "agent-zero";
export const DEFAULT_PORT = 50001;

export type DockerProgressKind = "info" | "error" | "success";

export interface DockerProgressEvent {
  kind: DockerProgressKind;
  message: string;
}

export interface DockerContainerInfo {
  id: string;
  name: string;
  image: string;
  state: string;
  status: string;
  createdAt?: string;
  runningFor?: string;
  ports?: string;
}

export interface DockerImageInfo {
  id: string;
  repository: string;
  tag: string;
  createdSince?: string;
  createdAt?: string;
  size?: string;
}

export interface DockerListResult {
  containers: DockerContainerInfo[];
  images: DockerImageInfo[];
}

export interface DockerOperationResult {
  success: boolean;
  details?: Record<string, unknown>;
}

export interface DockerRemoveResult {
  removedContainer: boolean;
  removedImage: boolean;
}

export interface IpcErrorPayload {
  code: string;
  message: string;
  details?: string;
}

export interface IpcResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: IpcErrorPayload;
}
