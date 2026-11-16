"""Runtime configuration (all overridable from the environment / .env)."""
import os

from dotenv import load_dotenv

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(os.path.dirname(BACKEND_DIR), ".env"))
load_dotenv()

DATA_DIR = os.path.abspath(os.getenv("DATA_DIR", os.path.join(BACKEND_DIR, "data")))
os.makedirs(DATA_DIR, exist_ok=True)

# Default: a SQLite file, so the app runs with no services. docker-compose sets a PostgreSQL URL.
DATABASE_URL = os.getenv("DATABASE_URL") or f"sqlite:///{os.path.join(DATA_DIR, 'ski.db')}"
STORAGE_TYPE = os.getenv("STORAGE_TYPE", "local")            # local | minio | s3

HOST = os.getenv("API_HOST", "0.0.0.0")
PORT = int(os.getenv("API_PORT", "8003"))
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "5177"))

MAX_VIDEO_SIZE_MB = int(os.getenv("MAX_VIDEO_SIZE_MB", "500"))
MAX_IMAGE_SIZE_MB = int(os.getenv("MAX_IMAGE_SIZE_MB", "25"))
MAX_IMAGES = int(os.getenv("MAX_IMAGES", "40"))
ANALYSIS_FPS = float(os.getenv("ANALYSIS_FPS", "15"))
MAX_ANALYSIS_SECONDS = float(os.getenv("MAX_ANALYSIS_SECONDS", "90"))

DEFAULT_USER = "anonymous"


def lan_ips() -> list[str]:
    """Addresses other devices can reach this machine on, home-LAN ranges first, then Tailscale (100.64/10).
    No packets are sent."""
    import ipaddress
    import socket
    import subprocess
    import sys
    found: list[str] = []
    if sys.platform == "darwin":          # with a VPN/exit node up, routes point at the tunnel; ask the NICs directly
        for nic in ("en0", "en1", "en2", "en3"):
            try:
                ip = subprocess.run(["ipconfig", "getifaddr", nic], capture_output=True, text=True, timeout=2).stdout.strip()
            except (OSError, subprocess.SubprocessError):
                ip = ""
            if ip and ip not in found:
                found.append(ip)
    for probe in ("192.168.255.255", "10.255.255.255", "172.31.255.255", "8.8.8.8", "100.100.100.100"):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect((probe, 1))
            ip = s.getsockname()[0]
            if ip not in found and not ip.startswith("127."):
                found.append(ip)
        except OSError:
            pass
        finally:
            s.close()
    tailscale = ipaddress.ip_network("100.64.0.0/10")
    return sorted(found, key=lambda ip: ipaddress.ip_address(ip) in tailscale) or ["127.0.0.1"]
