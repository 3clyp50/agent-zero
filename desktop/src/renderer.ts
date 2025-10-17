import './index.css';
import type {
  RuntimeContainer,
  RuntimeImage,
  RuntimeListResponse,
  RuntimeVolume,
} from './shared/runtime-types';

type SectionKey = 'images' | 'containers' | 'volumes';

interface SectionElements {
  status: HTMLElement;
  empty: HTMLElement;
  list: HTMLUListElement;
}

const getSectionElements = (key: SectionKey): SectionElements => {
  const status = document.querySelector<HTMLElement>(`[data-section="${key}"]`);
  const empty = document.querySelector<HTMLElement>(`[data-section="${key}-empty"]`);
  const list = document.querySelector<HTMLUListElement>(`[data-section="${key}-list"]`);

  if (!status || !empty || !list) {
    throw new Error(`Missing markup for ${key} section`);
  }

  return { status, empty, list };
};

const sections: Record<SectionKey, SectionElements> = {
  images: getSectionElements('images'),
  containers: getSectionElements('containers'),
  volumes: getSectionElements('volumes'),
};

const runtimeLabel = (runtime: RuntimeListResponse<unknown>['runtime']): string => {
  if (!runtime) {
    return 'Runtime unavailable';
  }

  return runtime === 'docker' ? 'Docker' : 'Podman';
};

const renderImages = (images: RuntimeImage[]): DocumentFragment => {
  const fragment = document.createDocumentFragment();

  images.forEach((image) => {
    const item = document.createElement('li');
    item.className = 'resource__item';

    const title = document.createElement('div');
    title.className = 'resource__item-title';
    title.textContent = `${image.repository}:${image.tag}`;

    const meta = document.createElement('div');
    meta.className = 'resource__item-meta';
    const metaParts = [image.id];
    if (image.size) {
      metaParts.push(image.size);
    }
    if (image.createdAt) {
      metaParts.push(`Created ${image.createdAt}`);
    }
    meta.textContent = metaParts.join(' • ');

    item.append(title, meta);
    fragment.append(item);
  });

  return fragment;
};

const renderContainers = (containers: RuntimeContainer[]): DocumentFragment => {
  const fragment = document.createDocumentFragment();

  containers.forEach((container) => {
    const item = document.createElement('li');
    item.className = 'resource__item';

    const title = document.createElement('div');
    title.className = 'resource__item-title';
    title.textContent = container.name;

    const meta = document.createElement('div');
    meta.className = 'resource__item-meta';

    const metaParts = [container.image];
    if (container.state) {
      metaParts.push(container.state);
    }
    if (container.status) {
      metaParts.push(container.status);
    }
    if (container.createdAt) {
      metaParts.push(`Created ${container.createdAt}`);
    }

    meta.textContent = metaParts.join(' • ');
    item.append(title, meta);
    fragment.append(item);
  });

  return fragment;
};

const renderVolumes = (volumes: RuntimeVolume[]): DocumentFragment => {
  const fragment = document.createDocumentFragment();

  volumes.forEach((volume) => {
    const item = document.createElement('li');
    item.className = 'resource__item';

    const title = document.createElement('div');
    title.className = 'resource__item-title';
    title.textContent = volume.name;

    const meta = document.createElement('div');
    meta.className = 'resource__item-meta';

    const metaParts: string[] = [];
    if (volume.driver) {
      metaParts.push(`Driver: ${volume.driver}`);
    }
    if (volume.mountpoint) {
      metaParts.push(volume.mountpoint);
    }

    meta.textContent = metaParts.join(' • ');
    item.append(title);
    if (metaParts.length > 0) {
      item.append(meta);
    }
    fragment.append(item);
  });

  return fragment;
};

const applyResponse = <T>(
  key: SectionKey,
  response: RuntimeListResponse<T>,
  renderItems: (items: T[]) => DocumentFragment,
  emptyMessage: string,
): void => {
  const { status, empty, list } = sections[key];

  status.textContent = runtimeLabel(response);

  if (response.error) {
    empty.textContent = response.error;
    empty.hidden = false;
    list.replaceChildren();
    list.hidden = true;
    return;
  }

  if (response.items.length === 0) {
    empty.textContent = emptyMessage;
    empty.hidden = false;
    list.replaceChildren();
    list.hidden = true;
    return;
  }

  list.replaceChildren(renderItems(response.items));
  list.hidden = false;
  empty.hidden = true;
};

const loadDashboard = async (): Promise<void> => {
  const api = window.containerRuntime;
  if (!api) {
    const message = 'Secure runtime bridge is unavailable. Check preload configuration.';
    (Object.keys(sections) as SectionKey[]).forEach((key) => {
      const { status, empty, list } = sections[key];
      status.textContent = 'Unavailable';
      empty.textContent = message;
      empty.hidden = false;
      list.hidden = true;
    });
    return;
  }

  const [images, containers, volumes] = await Promise.all([
    api.listImages(),
    api.listContainers(),
    api.listVolumes(),
  ]);

  applyResponse('images', images, renderImages, 'No images found.');
  applyResponse('containers', containers, renderContainers, 'No containers found.');
  applyResponse('volumes', volumes, renderVolumes, 'No volumes found.');
};

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    void loadDashboard();
  });
} else {
  void loadDashboard();
}
