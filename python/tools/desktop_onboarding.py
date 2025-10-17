"""CLI prototype for desktop onboarding checks.

This script walks users through the prerequisites for running Agent Zero's
containerized runtime, validating the host environment for Docker or Podman.
It is intentionally conservative and designed to be extended by the desktop
application later.
"""
from __future__ import annotations

import argparse
import dataclasses
import os
import platform
import shutil
import subprocess
import sys
from typing import Iterable, Optional


@dataclasses.dataclass
class CheckResult:
    """Outcome of a wizard check step."""

    title: str
    status: str
    details: str
    remediation: Optional[str] = None

    def format(self) -> str:
        lines = [f"- {self.title}: {self.status}"]
        if self.details:
            lines.append(f"    {self.details}")
        if self.remediation:
            lines.append(f"    👉 {self.remediation}")
        return "\n".join(lines)


def run_command(command: Iterable[str]) -> subprocess.CompletedProcess[str]:
    """Run a command and capture stdout, returning a completed process.

    The function never raises and instead returns the completed process. If the
    command cannot be executed an artificial result with return code 127 is
    returned.
    """

    try:
        return subprocess.run(
            list(command),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except FileNotFoundError as exc:  # pragma: no cover - platform dependent
        return subprocess.CompletedProcess(  # type: ignore[arg-type]
            args=list(command),
            returncode=127,
            stdout=str(exc),
        )


def check_for_cli(binary: str, friendly_name: str) -> CheckResult:
    """Check whether the given CLI exists and report version information."""

    path = shutil.which(binary)
    if not path:
        return CheckResult(
            title=f"{friendly_name} availability",
            status="missing",
            details=f"`{binary}` was not found on PATH.",
            remediation=f"Install {friendly_name} and ensure `{binary}` is available on PATH.",
        )

    proc = run_command([binary, "--version"])
    version = proc.stdout.strip() or "unknown version"
    status = "ok" if proc.returncode == 0 else "warning"
    details = f"Found at {path}: {version}."
    remediation = None
    if proc.returncode != 0:
        remediation = f"Running `{binary} --version` returned exit code {proc.returncode}."
    return CheckResult(
        title=f"{friendly_name} availability",
        status=status,
        details=details,
        remediation=remediation,
    )


def _check_virtualization_windows() -> CheckResult:
    """Check virtualization prerequisites for Windows."""

    hv_proc = run_command([
        "powershell",
        "-NoProfile",
        "-Command",
        "(Get-CimInstance -ClassName Win32_ComputerSystem).HypervisorPresent",
    ])
    if hv_proc.returncode == 0 and "True" in hv_proc.stdout:
        hv_status = "enabled"
    elif hv_proc.returncode == 0:
        hv_status = "disabled"
    else:
        hv_status = "unknown"

    wsl_proc = run_command(["wsl.exe", "--status"])
    wsl_ok = wsl_proc.returncode == 0 and "Default Version: 2" in wsl_proc.stdout
    details = [
        f"Hyper-V virtualization: {hv_status}.",
        "WSL status: available" if wsl_proc.returncode == 0 else "WSL status: unavailable",
    ]
    if wsl_proc.returncode == 0 and not wsl_ok:
        details.append("Default WSL version is not 2. Run `wsl --set-default-version 2`.")

    remediation = None
    if hv_status != "enabled":
        remediation = (
            "Enable virtualization in BIOS/UEFI and ensure Hyper-V, Virtual Machine Platform, "
            "and Windows Subsystem for Linux optional features are enabled."
        )
    return CheckResult(
        title="Windows virtualization stack",
        status="ok" if hv_status == "enabled" and wsl_proc.returncode == 0 else "warning",
        details=" ".join(details),
        remediation=remediation,
    )


def _check_virtualization_macos() -> CheckResult:
    """Check virtualization prerequisites for macOS."""

    hv_proc = run_command(["sysctl", "-n", "kern.hv_support"])
    hv_enabled = hv_proc.returncode == 0 and hv_proc.stdout.strip() == "1"

    architecture = platform.processor() or platform.machine()
    rosetta_proc = None
    if architecture and architecture.lower().startswith("arm"):
        rosetta_proc = run_command([
            "pkgutil",
            "--files",
            "com.apple.pkg.RosettaUpdateAuto",
        ])
    details_parts = [
        f"Hardware virtualization framework: {'available' if hv_enabled else 'unavailable'}.",
    ]
    remediation = None
    if not hv_enabled:
        remediation = "Rosetta/Intel virtualization not detected. Ensure hardware virtualization is enabled."

    if rosetta_proc is not None:
        if rosetta_proc.returncode == 0:
            details_parts.append("Rosetta 2: installed.")
        else:
            details_parts.append("Rosetta 2: not detected. Install via `softwareupdate --install-rosetta`.")
            remediation = (
                remediation
                or "Install Rosetta 2 to allow running Intel-based container images on Apple Silicon."
            )

    return CheckResult(
        title="macOS virtualization stack",
        status="ok" if hv_enabled else "warning",
        details=" ".join(details_parts),
        remediation=remediation,
    )


def _check_virtualization_linux() -> CheckResult:
    """Check virtualization prerequisites for Linux hosts."""

    cpuinfo_flags = ""
    try:
        with open("/proc/cpuinfo", "r", encoding="utf-8") as handle:
            cpuinfo_flags = handle.read()
    except OSError:
        cpuinfo_flags = ""

    hv_capable = "vmx" in cpuinfo_flags or "svm" in cpuinfo_flags
    kvm_access = os.path.exists("/dev/kvm") and os.access("/dev/kvm", os.R_OK | os.W_OK)
    details = [
        f"CPU virtualization extensions: {'present' if hv_capable else 'absent'}.",
        f"/dev/kvm access: {'ok' if kvm_access else 'restricted'}.",
    ]
    remediation_parts = []
    if not hv_capable:
        remediation_parts.append("Enable virtualization extensions (Intel VT-x/AMD-V) in BIOS/UEFI.")
    if not kvm_access:
        remediation_parts.append("Ensure the current user belongs to the `kvm` group and that the module is loaded.")
    remediation = " ".join(remediation_parts) if remediation_parts else None
    return CheckResult(
        title="Linux virtualization stack",
        status="ok" if hv_capable and kvm_access else "warning",
        details=" ".join(details),
        remediation=remediation,
    )


def check_virtualization() -> CheckResult:
    system = platform.system()
    if system == "Windows":
        return _check_virtualization_windows()
    if system == "Darwin":
        return _check_virtualization_macos()
    return _check_virtualization_linux()


def check_user_permissions(cli_name: str) -> CheckResult:
    """Attempt to run an info command to detect permission issues."""

    info_command = [cli_name, "info"]
    proc = run_command(info_command)
    if proc.returncode == 0:
        return CheckResult(
            title=f"{cli_name} permissions",
            status="ok",
            details=f"`{cli_name} info` executed successfully.",
        )

    remediation = (
        "The command failed. Ensure the service is running and the current user has permissions."
    )
    if platform.system() == "Linux":
        remediation += " Add the user to the `docker` or `podman` group and relogin."

    return CheckResult(
        title=f"{cli_name} permissions",
        status="warning",
        details=proc.stdout.strip() or "Command returned a non-zero exit code.",
        remediation=remediation,
    )


def run_wizard(preferred_runtime: Optional[str] = None) -> int:
    """Run the onboarding wizard and print the collected results."""

    checks = []
    virtualization = check_virtualization()
    checks.append(virtualization)

    docker = check_for_cli("docker", "Docker")
    podman = check_for_cli("podman", "Podman")
    checks.extend([docker, podman])

    runtime = preferred_runtime
    if runtime not in {"docker", "podman"}:
        runtime = "podman" if podman.status == "ok" else "docker"
        if preferred_runtime and runtime != preferred_runtime:
            print(
                f"Preferred runtime `{preferred_runtime}` unavailable, falling back to `{runtime}`.",
                file=sys.stderr,
            )

    if runtime == "docker" and docker.status != "missing":
        checks.append(check_user_permissions("docker"))
    elif runtime == "podman" and podman.status != "missing":
        checks.append(check_user_permissions("podman"))

    print("Agent Zero Desktop environment report:\n")
    for check in checks:
        print(check.format())
        print()

    failing = [c for c in checks if c.status == "missing"]
    warnings = [c for c in checks if c.status == "warning"]

    if failing:
        print("Some critical components are missing. Follow the remediation guidance above.")
        return 2
    if warnings:
        print("Environment has warnings. Address them for the best experience.")
        return 1
    print("All checks passed. You're ready to run the desktop runtime!")
    return 0


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Agent Zero desktop onboarding checks")
    parser.add_argument(
        "--runtime",
        choices=["docker", "podman"],
        help="Preferred container runtime to validate first.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    return run_wizard(preferred_runtime=args.runtime)


if __name__ == "__main__":
    sys.exit(main())
