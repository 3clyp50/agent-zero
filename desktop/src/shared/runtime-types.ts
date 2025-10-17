export type ContainerRuntime = 'docker' | 'podman';

export interface RuntimeImage {
  id: string;
  repository: string;
  tag: string;
  createdAt?: string;
  size?: string;
}

export interface RuntimeContainer {
  id: string;
  name: string;
  image: string;
  state?: string;
  status?: string;
  createdAt?: string;
}

export interface RuntimeVolume {
  name: string;
  driver?: string;
  mountpoint?: string;
}

export interface RuntimeListResponse<TItem> {
  runtime: ContainerRuntime | null;
  items: TItem[];
  error?: string;
}

export interface ContainerRuntimeBridge {
  listImages(): Promise<RuntimeListResponse<RuntimeImage>>;
  listContainers(): Promise<RuntimeListResponse<RuntimeContainer>>;
  listVolumes(): Promise<RuntimeListResponse<RuntimeVolume>>;
}
