import { execFile } from "child_process";
import { spawn } from "child_process";
import { promisify } from "util";
import fs from "fs";
import path from "path";
import {
  DEFAULT_CONTAINER_NAME,
  DEFAULT_IMAGE,
  DEFAULT_PORT,
  DockerListResult,
  DockerProgressEvent,
  DockerRemoveResult,
} from "../common/dockerTypes";

const execFileAsync = promisify(execFile);

export class DockerNotAvailableError extends Error {
  public readonly code = "DOCKER_UNAVAILABLE";
  constructor(message: string, public readonly details?: string) {
    super(message);
    this.name = "DockerNotAvailableError";
  }
}

export class DockerCommandError extends Error {
  public readonly code = "DOCKER_COMMAND_FAILED";
  constructor(message: string, public readonly details?: string) {
    super(message);
    this.name = "DockerCommandError";
  }
}

let dockerVerified = false;

async function ensureDockerAvailable(): Promise<void> {
  if (dockerVerified) {
    return;
  }

  try {
    await execFileAsync("docker", ["info"]);
    dockerVerified = true;
  } catch (error) {
    throw normalizeDockerError(
      error,
      "Docker Desktop is not available. Please install or start Docker Desktop and try again."
    );
  }
}

function normalizeDockerError(error: unknown, defaultMessage: string, stderrText = ""): Error {
  const err = error as NodeJS.ErrnoException & { stderr?: string };
  const combinedMessage = [stderrText, err?.stderr].filter(Boolean).join("\n");
  const message = combinedMessage || err?.message || defaultMessage;
  if (err?.code === "ENOENT") {
    dockerVerified = false;
    return new DockerNotAvailableError(
      "Docker CLI was not found. Install Docker Desktop and ensure the docker command is available in your PATH.",
      message
    );
  }

  if (/docker daemon is not running/i.test(message) || /cannot connect to the docker daemon/i.test(message)) {
    dockerVerified = false;
    return new DockerNotAvailableError(
      "Docker Desktop does not appear to be running. Please launch Docker Desktop and wait for it to finish starting before retrying.",
      message
    );
  }

  if (/permission denied/i.test(message)) {
    dockerVerified = false;
    return new DockerNotAvailableError(
      "Docker requires elevated permissions. Make sure your user has access to Docker or run Docker Desktop.",
      message
    );
  }

  return new DockerCommandError(defaultMessage, message);
}

async function runDockerCommand(args: string[]): Promise<{ stdout: string; stderr: string }> {
  await ensureDockerAvailable();
  try {
    const { stdout, stderr } = await execFileAsync("docker", args, { maxBuffer: 1024 * 1024 * 20 });
    return {
      stdout: stdout?.toString() ?? "",
      stderr: stderr?.toString() ?? "",
    };
  } catch (error) {
    throw normalizeDockerError(error, `Failed to execute \"docker ${args.join(" ")}\".`);
  }
}

export async function pullImage(onProgress?: (event: DockerProgressEvent) => void): Promise<void> {
  await ensureDockerAvailable();
  await new Promise<void>((resolve, reject) => {
    const child = spawn("docker", ["pull", DEFAULT_IMAGE]);
    let stderrBuffer = "";

    const emit = (kind: DockerProgressEvent["kind"], message: string) => {
      if (!message.trim()) {
        return;
      }
      onProgress?.({ kind, message: message.trimEnd() });
    };

    child.stdout.on("data", (chunk) => {
      const text = chunk.toString();
      text
        .split(/\r?\n/)
        .filter(Boolean)
        .forEach((line: string) => emit("info", line));
    });

    child.stderr.on("data", (chunk) => {
      const text = chunk.toString();
      stderrBuffer += text;
      text
        .split(/\r?\n/)
        .filter(Boolean)
        .forEach((line: string) => emit("error", line));
    });

    child.on("error", (error) => {
      reject(normalizeDockerError(error, "Docker pull command could not start."));
    });

    child.on("close", (code) => {
      if (code === 0) {
        emit("success", `Docker image ${DEFAULT_IMAGE} pulled successfully.`);
        resolve();
      } else {
        reject(normalizeDockerError(new Error(`docker pull exited with code ${code}`), "Docker pull command failed.", stderrBuffer));
      }
    });
  });
}

export async function startContainer(): Promise<{ containerId?: string; startedExisting: boolean }> {
  await ensureDockerAvailable();
  const existing = await getContainerId();
  if (existing) {
    await runDockerCommand(["start", DEFAULT_CONTAINER_NAME]);
    return { containerId: existing, startedExisting: true };
  }

  const runArgs = [
    "run",
    "-d",
    "--name",
    DEFAULT_CONTAINER_NAME,
    "-p",
    DEFAULT_PORT + ":80",
    DEFAULT_IMAGE,
  ];

  const { stdout } = await runDockerCommand(runArgs);
  const containerId = stdout.trim();
  return { containerId, startedExisting: false };
}

export async function stopContainer(): Promise<{ stopped: boolean }> {
  await ensureDockerAvailable();
  const existing = await getContainerId();
  if (!existing) {
    return { stopped: false };
  }

  try {
    await runDockerCommand(["stop", DEFAULT_CONTAINER_NAME]);
    return { stopped: true };
  } catch (error) {
    throw normalizeDockerError(error, "Failed to stop Docker container.");
  }
}

export async function removeResources(): Promise<DockerRemoveResult> {
  await ensureDockerAvailable();
  let removedContainer = false;
  let removedImage = false;

  try {
    const existing = await getContainerId();
    if (existing) {
      await runDockerCommand(["rm", "-f", DEFAULT_CONTAINER_NAME]);
      removedContainer = true;
    }
  } catch (error) {
    const normalized = normalizeDockerError(error, "Failed to remove Docker container.");
    if (normalized instanceof DockerCommandError && normalized.details?.includes("No such container")) {
      // treat as already removed
    } else {
      throw normalized;
    }
  }

  try {
    await runDockerCommand(["rmi", DEFAULT_IMAGE]);
    removedImage = true;
  } catch (error) {
    const normalized = normalizeDockerError(error, "Failed to remove Docker image.");
    if (normalized instanceof DockerCommandError && normalized.details?.includes("No such image")) {
      // ignore missing image
    } else {
      throw normalized;
    }
  }

  return { removedContainer, removedImage };
}

export async function listDockerResources(): Promise<DockerListResult> {
  await ensureDockerAvailable();
  const [containersOutput, imagesOutput] = await Promise.all([
    runDockerCommand([
      "ps",
      "-a",
      "--format",
      "{{json .}}",
      "--filter",
      "name=" + DEFAULT_CONTAINER_NAME,
    ]),
    runDockerCommand(["images", "--format", "{{json .}}", "agent0ai/agent-zero"]),
  ]);

  const containers = containersOutput.stdout
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => {
      try {
        const parsed = JSON.parse(line);
        return {
          id: parsed.ID as string,
          name: parsed.Names as string,
          image: parsed.Image as string,
          state: parsed.State as string,
          status: parsed.Status as string,
          createdAt: parsed.CreatedAt as string | undefined,
          runningFor: parsed.RunningFor as string | undefined,
          ports: parsed.Ports as string | undefined,
        };
      } catch (error) {
        throw new DockerCommandError("Failed to parse docker ps output.", String(error));
      }
    });

  const images = imagesOutput.stdout
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => {
      try {
        const parsed = JSON.parse(line);
        return {
          id: parsed.ID as string,
          repository: parsed.Repository as string,
          tag: parsed.Tag as string,
          createdSince: parsed.CreatedSince as string | undefined,
          createdAt: parsed.CreatedAt as string | undefined,
          size: parsed.Size as string | undefined,
        };
      } catch (error) {
        throw new DockerCommandError("Failed to parse docker images output.", String(error));
      }
    });

  return {
    containers,
    images,
  };
}

async function getContainerId(): Promise<string | null> {
  const { stdout } = await runDockerCommand([
    "ps",
    "-a",
    "-q",
    "--filter",
    "name=^/" + DEFAULT_CONTAINER_NAME + "$",
  ]);
  const id = stdout.trim();
  return id || null;
}

export function ensureRendererAssets(): void {
  const projectRoot = path.resolve(__dirname, "..", "..");
  const srcDir = path.join(projectRoot, "src", "renderer");
  const destDir = path.join(projectRoot, "dist", "renderer");
  fs.mkdirSync(destDir, { recursive: true });

  const assets = ["index.html", "styles.css"];
  for (const asset of assets) {
    const srcPath = path.join(srcDir, asset);
    const destPath = path.join(destDir, asset);
    if (fs.existsSync(srcPath)) {
      fs.copyFileSync(srcPath, destPath);
    }
  }
}
