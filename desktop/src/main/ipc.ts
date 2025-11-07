import { ipcMain, IpcMainInvokeEvent } from "electron";
import {
  DockerCommandError,
  DockerNotAvailableError,
  listDockerResources,
  pullImage,
  removeResources,
  startContainer,
  stopContainer,
} from "./dockerService";
import {
  DockerListResult,
  DockerProgressEvent,
  DockerRemoveResult,
  IpcErrorPayload,
  IpcResponse,
} from "../common/dockerTypes";

function toErrorPayload(error: unknown): IpcErrorPayload {
  if (error instanceof DockerNotAvailableError || error instanceof DockerCommandError) {
    return {
      code: error.code,
      message: error.message,
      details: error.details,
    };
  }

  const message = error instanceof Error ? error.message : "Unexpected error";
  return {
    code: "UNEXPECTED_ERROR",
    message,
    details: error instanceof Error && error.stack ? error.stack : undefined,
  };
}

function wrapHandler<T>(handler: (event: IpcMainInvokeEvent) => Promise<IpcResponse<T>>): (event: IpcMainInvokeEvent) => Promise<IpcResponse<T>> {
  return async (event) => {
    try {
      return await handler(event);
    } catch (error) {
      return { success: false, error: toErrorPayload(error) };
    }
  };
}

export function registerDockerIpcHandlers(): void {
  ipcMain.handle(
    "docker:pull",
    wrapHandler<void>(async (event) => {
      const sendProgress = (payload: DockerProgressEvent) => {
        event.sender.send("docker:pull-progress", payload);
      };
      await pullImage(sendProgress);
      return { success: true };
    })
  );

  ipcMain.handle(
    "docker:start",
    wrapHandler(async () => {
      const result = await startContainer();
      return { success: true, data: result };
    })
  );

  ipcMain.handle(
    "docker:stop",
    wrapHandler(async () => {
      const result = await stopContainer();
      return { success: true, data: result };
    })
  );

  ipcMain.handle(
    "docker:remove",
    wrapHandler<DockerRemoveResult>(async () => {
      const result = await removeResources();
      return { success: true, data: result };
    })
  );

  ipcMain.handle(
    "docker:list",
    wrapHandler<DockerListResult>(async () => {
      const data = await listDockerResources();
      return { success: true, data };
    })
  );
}
