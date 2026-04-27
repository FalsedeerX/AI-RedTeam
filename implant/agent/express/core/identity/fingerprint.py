import os
import uuid
import psutil
import socket
import hashlib
import platform


def get_fingerprint() -> dict:
    """Return normalized, cross-platform fingerprint"""
    return {
        "os": platform.system().lower().strip(),
        "os_version": _normalize_os_version(),
        "arch": _normalize_arch(),
        "cpu_threads": os.cpu_count(),
        "ram_gb": round(psutil.virtual_memory().total / (1024**3)),
        "machine_id": _get_machine_id(),
        "hostname": socket.gethostname().lower().strip(),
    }


def fingerprint_hash(fp: dict) -> str:
    """Stable, OS-agnostic fingerprint hash"""
    keys = ["machine_id", "arch", "os"]
    normalized = "|".join(
        (fp.get(k) or "").lower().strip()
        for k in keys
    )

    return hashlib.sha256(normalized.encode()).hexdigest()


def _normalize_os_version() -> str:
    """
    Unified OS version:
    - Windows → version (build number)
    - Linux   → release (kernel version)
    """
    system = platform.system()

    if system == "Windows":
        return platform.version().lower().strip()

    return platform.release().lower().strip()


def _normalize_arch() -> str:
    arch = platform.machine().lower()
    if arch in ("x86_64", "amd64"):
        return "x64"
    if arch in ("i386", "i686", "x86"):
        return "x86"

    return arch


def _get_machine_id() -> str:
    # --- Linux ---
    try:
        if os.path.exists("/etc/machine-id"):
            with open("/etc/machine-id", "r") as f:
                return f.read().strip()
    except Exception:
        pass

    # --- Windows ---
    try:
        if platform.system() == "Windows":
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography"
            )
            value, _ = winreg.QueryValueEx(key, "MachineGuid")
            return value
    except Exception:
        pass

    # --- Fallback (least stable) ---
    return str(uuid.getnode())


# =========================
# TEST ENTRYPOINT
# =========================

if __name__ == "__main__":
    print("=== Fingerprint Test ===")

    fp = get_fingerprint()
    fp_hash = fingerprint_hash(fp)

    print("\n[Fingerprint]")
    for k, v in fp.items():
        print(f"{k}: {v}")

    print("\n[Hash]")
    print(fp_hash)

    print("\n[Sanity Checks]")
    print(f"machine_id present: {bool(fp.get('machine_id'))}")
    print(f"os: {fp['os']} {fp['os_version']}")
    print(f"arch: {fp['arch']}")

