import { app, BrowserWindow, ipcMain } from 'electron';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import type {
  ContainerRuntime,
  RuntimeContainer,
  RuntimeImage,
  RuntimeListResponse,
  RuntimeVolume,
} from './shared/runtime-types';

declare const MAIN_WINDOW_WEBPACK_ENTRY: string;
declare const MAIN_WINDOW_PRELOAD_WEBPACK_ENTRY: string;

const execFileAsync = promisify(execFile);

if (require('electron-squirrel-startup')) {
  app.quit();
}

const RUNTIME_CANDIDATES: ContainerRuntime[] = ['docker', 'podman'];
let detectedRuntime: ContainerRuntime | null = null;

const detectRuntime = async (): Promise<ContainerRuntime> => {
  if (detectedRuntime) {
    return detectedRuntime;
  }

  for (const runtime of RUNTIME_CANDIDATES) {
    try {
      await execFileAsync(runtime, ['version']);
      detectedRuntime = runtime;
      return runtime;
    } catch (error) {
      const err = error as NodeJS.ErrnoException;
      if (err.code === 'ENOENT') {
        continue;
      }

      // If the command exists but returns a non-zero exit code we still
      // treat it as detected to give users feedback from the downstream
      // handlers. The CLI sometimes returns non-zero when the daemon is not
      // running, which is still a useful signal for the UI.
      detectedRuntime = runtime;
      return runtime;
    }
  }

  throw new Error('Neither Docker nor Podman is available on this system.');
};

type ExecResult<T> = RuntimeListResponse<T>;

const parseJsonLines = <TRow>(input: string): TRow[] => {
  return input
    .split(/\r?\n/g)
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
    .map((line) => {
      try {
        return JSON.parse(line) as TRow;
      } catch (error) {
        throw new Error(`Failed to parse CLI output: ${(error as Error).message}`);
      }
    });
};

const asErrorResponse = <T>(runtime: ContainerRuntime | null, error: unknown): ExecResult<T> => ({
  runtime,
  items: [],
  error: error instanceof Error ? error.message : String(error),
});

const listImages = async (): Promise<ExecResult<RuntimeImage>> => {
  try {
    const runtime = await detectRuntime();
    const { stdout } = await execFileAsync(runtime, ['images', '--format', '{{json .}}']);

    type RawImage = {
      Repository?: string;
      Tag?: string;
      ID?: string;
      CreatedAt?: string;
      Size?: string;
    };

    const items = parseJsonLines<RawImage>(stdout).map((image) => ({
      id: image.ID ?? 'unknown',
      repository: image.Repository ?? '<none>',
      tag: image.Tag ?? '<none>',
      createdAt: image.CreatedAt,
      size: image.Size,
    }));

    return { runtime, items };
  } catch (error) {
    return asErrorResponse<RuntimeImage>(detectedRuntime, error);
  }
};

const listContainers = async (): Promise<ExecResult<RuntimeContainer>> => {
  try {
    const runtime = await detectRuntime();
    const { stdout } = await execFileAsync(runtime, ['ps', '--all', '--format', '{{json .}}']);

    type RawContainer = {
      ID?: string;
      Names?: string;
      Image?: string;
      State?: string;
      Status?: string;
      CreatedAt?: string;
    };

    const items = parseJsonLines<RawContainer>(stdout).map((container) => ({
      id: container.ID ?? 'unknown',
      name: container.Names ?? '<unnamed>',
      image: container.Image ?? '<unknown>',
      state: container.State,
      status: container.Status,
      createdAt: container.CreatedAt,
    }));

    return { runtime, items };
  } catch (error) {
    return asErrorResponse<RuntimeContainer>(detectedRuntime, error);
  }
};

const listVolumes = async (): Promise<ExecResult<RuntimeVolume>> => {
  try {
    const runtime = await detectRuntime();
    const { stdout } = await execFileAsync(runtime, ['volume', 'ls', '--format', '{{json .}}']);

    type RawVolume = {
      Name?: string;
      Driver?: string;
      Mountpoint?: string;
    };

    const items = parseJsonLines<RawVolume>(stdout).map((volume) => ({
      name: volume.Name ?? '<unknown>',
      driver: volume.Driver,
      mountpoint: volume.Mountpoint,
    }));

    return { runtime, items };
  } catch (error) {
    return asErrorResponse<RuntimeVolume>(detectedRuntime, error);
  }
};

const registerIpcHandlers = (): void => {
  ipcMain.handle('runtime:list-images', () => listImages());
  ipcMain.handle('runtime:list-containers', () => listContainers());
  ipcMain.handle('runtime:list-volumes', () => listVolumes());
};

const createWindow = (): void => {
  const mainWindow = new BrowserWindow({
    height: 720,
    width: 1080,
    minHeight: 600,
    minWidth: 960,
    backgroundColor: '#0f172a',
    webPreferences: {
      preload: MAIN_WINDOW_PRELOAD_WEBPACK_ENTRY,
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  mainWindow.loadURL(MAIN_WINDOW_WEBPACK_ENTRY);

  if (!app.isPackaged) {
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  }
};

app.whenReady().then(() => {
  registerIpcHandlers();
  createWindow();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
