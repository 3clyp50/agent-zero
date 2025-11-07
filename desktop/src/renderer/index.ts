import type {
  DockerContainerInfo,
  DockerImageInfo,
  DockerListResult,
  DockerProgressEvent,
  DockerRemoveResult,
  IpcErrorPayload,
  IpcResponse,
} from "../common/dockerTypes";

interface OperationState {
  busy: boolean;
  label: string;
}

const imageStatusEl = document.getElementById("image-status") as HTMLParagraphElement;
const imageDetailsEl = document.getElementById("image-details") as HTMLParagraphElement;
const containerStatusEl = document.getElementById("container-status") as HTMLParagraphElement;
const containerDetailsEl = document.getElementById("container-details") as HTMLParagraphElement;
const progressSection = document.getElementById("progress-section") as HTMLElement;
const progressLog = document.getElementById("progress-log") as HTMLPreElement;
const progressTitle = document.getElementById("progress-title") as HTMLHeadingElement;
const spinner = document.getElementById("spinner") as HTMLElement;
const errorSection = document.getElementById("error-section") as HTMLElement;
const instructionsSection = document.getElementById("instructions") as HTMLElement;

const pullButton = document.getElementById("pull") as HTMLButtonElement;
const startButton = document.getElementById("start") as HTMLButtonElement;
const stopButton = document.getElementById("stop") as HTMLButtonElement;
const removeButton = document.getElementById("remove") as HTMLButtonElement;
const refreshButton = document.getElementById("refresh") as HTMLButtonElement;

let operation: OperationState = { busy: false, label: "" };
let unsubscribeProgress: (() => void) | null = null;

function setBusy(label: string | null): void {
  operation = {
    busy: Boolean(label),
    label: label ?? "",
  };

  [pullButton, startButton, stopButton, removeButton, refreshButton].forEach((button) => {
    button.disabled = operation.busy;
  });

  if (operation.busy && label) {
    progressSection.classList.remove("hidden");
    spinner.classList.remove("hidden");
    progressTitle.textContent = label;
  } else {
    spinner.classList.add("hidden");
    progressTitle.textContent = "Activity";
  }
}

function appendProgress(event: DockerProgressEvent): void {
  if (event.kind === "success") {
    progressLog.textContent += `\n✅ ${event.message}`;
  } else if (event.kind === "error") {
    progressLog.textContent += `\n⚠️ ${event.message}`;
  } else {
    progressLog.textContent += `\n${event.message}`;
  }
  progressLog.scrollTop = progressLog.scrollHeight;
}

function resetProgress(): void {
  progressLog.textContent = "";
  progressSection.classList.add("hidden");
}

function showError(message: string, details?: string, showInstructions = false): void {
  errorSection.textContent = details ? `${message}\n${details}` : message;
  errorSection.classList.remove("hidden");
  if (showInstructions) {
    instructionsSection.classList.remove("hidden");
  } else {
    instructionsSection.classList.add("hidden");
  }
}

function clearError(): void {
  errorSection.classList.add("hidden");
  errorSection.textContent = "";
  instructionsSection.classList.add("hidden");
}

function parseListResult(result: DockerListResult): { image: DockerImageInfo | null; container: DockerContainerInfo | null } {
  const image = result.images.find((img) => img.repository === "agent0ai/agent-zero" && img.tag === "latest") ?? null;
  const container =
    result.containers.find((item) => item.name === "agent-zero" || item.image.startsWith("agent0ai/agent-zero")) ?? null;
  return { image, container };
}

function setStatusUnknown(): void {
  imageStatusEl.textContent = "Unknown";
  imageDetailsEl.textContent = "Docker status unavailable.";
  containerStatusEl.textContent = "Unknown";
  containerDetailsEl.textContent = "Docker status unavailable.";
  stopButton.disabled = true;
  startButton.disabled = true;
  removeButton.disabled = true;
  pullButton.disabled = true;
}

function updateStatuses(result: DockerListResult): void {
  const { image, container } = parseListResult(result);

  if (image) {
    imageStatusEl.textContent = "Pulled";
    imageDetailsEl.textContent = `${image.repository}:${image.tag}${image.size ? ` • ${image.size}` : ""}`;
  } else {
    imageStatusEl.textContent = "Not Found";
    imageDetailsEl.textContent = "Pull the docker image to continue.";
  }

  if (container) {
    const running = container.state.toLowerCase() === "running";
    containerStatusEl.textContent = running ? "Running" : "Stopped";
    const info: string[] = [];
    if (container.status) {
      info.push(container.status);
    }
    if (container.ports) {
      info.push(container.ports);
    }
    containerDetailsEl.textContent = info.join(" • ");
    stopButton.disabled = !running || operation.busy;
    startButton.disabled = running || operation.busy;
  } else {
    containerStatusEl.textContent = "Not Created";
    containerDetailsEl.textContent = "Start the container to launch Agent Zero.";
    stopButton.disabled = true;
    startButton.disabled = operation.busy || !image;
  }

  removeButton.disabled = operation.busy || (!image && !container);
  pullButton.disabled = operation.busy;
  refreshButton.disabled = operation.busy;
}

function handleErrorResponse(error: IpcErrorPayload): void {
  const isDockerMissing = error.code === "DOCKER_UNAVAILABLE";
  showError(error.message, error.details, isDockerMissing);
}

async function invokeAndHandle<T>(
  action: () => Promise<IpcResponse<T>>,
  label: string,
  options?: { resetProgress?: boolean }
): Promise<IpcResponse<T> | null> {
  try {
    if (options?.resetProgress) {
      resetProgress();
    }
    setBusy(label);
    const response = await action();
    if (!response.success && response.error) {
      handleErrorResponse(response.error);
      return null;
    }
    clearError();
    return response;
  } catch (error) {
    showError(error instanceof Error ? error.message : "Unexpected error");
    return null;
  } finally {
    setBusy(null);
  }
}

async function refreshStatus(): Promise<void> {
  const response = await invokeAndHandle(() => window.electronAPI.listDockerResources(), "Refreshing status", {
    resetProgress: true,
  });
  if (response && response.success && response.data) {
    updateStatuses(response.data);
  } else {
    setStatusUnknown();
  }
}

async function handlePull(): Promise<void> {
  resetProgress();
  clearError();
  if (!unsubscribeProgress) {
    unsubscribeProgress = window.electronAPI.onDockerPullProgress((event) => {
      progressSection.classList.remove("hidden");
      appendProgress(event);
    });
  }

  const response = await invokeAndHandle(() => window.electronAPI.pullDockerImage(), "Pulling docker image");
  if (response && response.success) {
    await refreshStatus();
  }
}

async function handleStart(): Promise<void> {
  const response = await invokeAndHandle(() => window.electronAPI.startDockerContainer(), "Starting container");
  if (response && response.success) {
    await refreshStatus();
  }
}

async function handleStop(): Promise<void> {
  const response = await invokeAndHandle(() => window.electronAPI.stopDockerContainer(), "Stopping container");
  if (response && response.success) {
    await refreshStatus();
  }
}

async function handleRemove(): Promise<void> {
  const response = await invokeAndHandle(() => window.electronAPI.removeDockerResources(), "Removing resources");
  if (response && response.success) {
    const data = response.data as DockerRemoveResult | undefined;
    const summary: string[] = [];
    if (data?.removedContainer) {
      summary.push("Container removed");
    }
    if (data?.removedImage) {
      summary.push("Image removed");
    }
    if (summary.length) {
      appendProgress({ kind: "success", message: summary.join(" • ") });
      progressSection.classList.remove("hidden");
    }
    await refreshStatus();
  }
}

pullButton.addEventListener("click", () => {
  void handlePull();
});
startButton.addEventListener("click", () => {
  void handleStart();
});
stopButton.addEventListener("click", () => {
  void handleStop();
});
removeButton.addEventListener("click", () => {
  void handleRemove();
});
refreshButton.addEventListener("click", () => {
  void refreshStatus();
});

window.addEventListener("DOMContentLoaded", () => {
  resetProgress();
  void refreshStatus();
});
