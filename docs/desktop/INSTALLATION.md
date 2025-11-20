# Desktop Runtime Installation & Environment Validation

This document captures the exploratory work required to onboard Agent Zero's
desktop runtime onto developer machines. It summarizes the feasibility of
shipping Podman directly, enumerates platform prerequisites, and introduces a
prototype onboarding wizard that can evolve into an automated installer.

## 1. Feasibility: Ship Podman vs. Trigger Installation

### Option A — Bundle a minimal Podman runtime

| Platform | Status | Notes |
| --- | --- | --- |
| Windows | ⚠️ Feasible with effort | Requires distributing `podman-remote.exe`, the `podman machine` assets, and provisioning a WSL2 VM. Shipping a custom VM image increases the download size (~800 MB) and demands driver updates for each Windows build. Maintenance burden is high because security updates must be re-issued promptly. |
| macOS | ⚠️ Feasible but heavy | Podman on macOS depends on the Apple Hypervisor framework plus a Lima VM. Shipping a trimmed Lima + QEMU bundle is possible, yet notarization and Rosetta compatibility tests are required. Continuous updates for each Podman release would fall on us. |
| Linux | ✅ Straightforward | Native Podman packages are available on most distributions. A portable static build could be shipped, but distro package managers already provide timely updates. |

**Risks:**

* Larger application footprint (hundreds of megabytes) and longer install times.
* We become responsible for Podman CVE response times and OS-specific packaging.
* Requires implementing privileged setup steps (WSL2 features, kernel modules) that the app cannot perform without elevated permissions.

### Option B — Trigger official Podman Desktop or Engine installation

| Platform | Status | Notes |
| --- | --- | --- |
| Windows | ✅ Recommended | Podman Desktop installer handles enabling WSL2 integration and ships signed binaries. We can deep-link to `podman-desktop.exe` or invoke `winget install -e --id RedHat.Podman-Desktop`. |
| macOS | ✅ Recommended | Podman Desktop (`.dmg`) or Homebrew packages manage the Lima VM and virtualization entitlements. Trigger downloads via `brew install podman-desktop` or open the DMG URL in the browser. |
| Linux | ✅ Recommended | Point users to `dnf`, `apt`, or `pacman` commands; optional `brew` on Linux. No need to ship binaries ourselves. |

**Benefits:**

* Offloads maintenance and security updates to Podman's official channels.
* Reuses platform-native installers with proper code signing.
* Reduces our download size and legal/licensing footprint.

**Conclusion:** Triggering the official Podman Desktop/Engine installers is the
preferred approach. Shipping our own runtime should be considered only for fully
offline deployments and would require a dedicated maintenance plan.

## 2. Platform Prerequisites

| Platform | Virtualization | Container Runtime | Additional Requirements |
| --- | --- | --- | --- |
| Windows 11 / Windows 10 21H2+ | BIOS/UEFI virtualization (Intel VT-x/AMD-V), Hyper-V, Virtual Machine Platform, and WSL2 enabled. | Docker Desktop, Docker Engine (via WSL), or Podman Desktop/Engine. | Latest Windows updates, admin rights to install optional features. |
| macOS 12+ (Intel & Apple Silicon) | Apple Hypervisor framework enabled; Rosetta 2 for Apple Silicon when running x86_64 images. | Docker Desktop, Colima, Rancher Desktop, or Podman Desktop. | Xcode Command Line Tools recommended for virtualization drivers; internet access for Rosetta install. |
| Linux (Fedora, Ubuntu 22.04+, Arch, etc.) | Kernel with KVM modules, `/dev/kvm` accessible to the user, cgroups v2 enabled. | Podman 4+, Docker Engine 24+, or compatible OCI runtime. | User must belong to `docker`, `podman`, or `libvirt` groups depending on distribution. |

**General prerequisites:**

* 8 GB RAM minimum, 16 GB recommended for simultaneous IDE and container usage.
* 10 GB free disk space for base images and build cache.
* Stable internet connection for pulling container images and dependency updates.

## 3. Onboarding Wizard Prototype

A command-line prototype is provided at
[`python/tools/desktop_onboarding.py`](../../python/tools/desktop_onboarding.py)
that can be wrapped by the desktop UI. The wizard performs the following steps:

1. Detects virtualization support (Hyper-V/WSL2 on Windows, Hypervisor.framework on macOS, KVM on Linux).
2. Checks for Docker and Podman binaries on the `PATH`, reporting versions if present.
3. Validates runtime permissions by running `docker info` or `podman info` on the preferred runtime.
4. Outputs remediation guidance for any missing or warning conditions.

Run the prototype directly from the repository root:

```bash
python -m python.tools.desktop_onboarding --runtime podman
```

The exit code indicates readiness (`0` success, `1` warnings, `2` missing critical
components), making it suitable for automated diagnostics or CI gating.

## 4. Next Steps

* Integrate the CLI checks into the desktop application's onboarding flow with a
  guided UI (progress steps, contextual help, inline remediation links).
* Detect whether Podman Desktop or Docker Desktop is already running and offer to
  launch it for the user.
* Offer one-click commands (`winget`, `brew`, distro package managers) directly
  from the UI once the user approves elevated operations.
* Extend virtualization checks with richer telemetry (e.g., CPU compatibility,
  virtualization-based security conflicts) before provisioning local containers.

The findings above should inform future implementation work and any automated
installers we decide to ship.
