import { app, BrowserWindow } from "electron";
import path from "path";
import { ensureRendererAssets } from "./dockerService";
import { registerDockerIpcHandlers } from "./ipc";

let mainWindow: BrowserWindow | null = null;

async function createWindow(): Promise<void> {
  ensureRendererAssets();

  mainWindow = new BrowserWindow({
    width: 1024,
    height: 720,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  const rendererHtmlPath = path.join(__dirname, "../renderer/index.html");
  await mainWindow.loadFile(rendererHtmlPath);
}

app.whenReady().then(async () => {
  registerDockerIpcHandlers();
  await createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      void createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
