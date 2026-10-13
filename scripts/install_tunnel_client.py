"""Install the official OpenAI tunnel binary, verifying GitHub's asset SHA-256."""
import hashlib
import json
import os
from pathlib import Path
import platform
import tempfile
from urllib.request import Request, urlopen
from zipfile import ZipFile

RELEASE_API = "https://api.github.com/repos/openai/tunnel-client/releases/latest"


def platform_asset_suffix() -> str:
    system = {"Darwin": "darwin", "Linux": "linux"}.get(platform.system())
    machine = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "amd64", "AMD64": "amd64"}.get(platform.machine())
    if not system or not machine:
        raise RuntimeError("This installer supports macOS and Linux on arm64/amd64")
    return f"-{system}-{machine}.zip"


def main():
    target = Path(__file__).resolve().parents[1] / ".bin" / "tunnel-client"
    request = Request(RELEASE_API, headers={"User-Agent": "garmin-mcp-web-installer"})
    with urlopen(request, timeout=30) as response:
        release = json.load(response)
    suffix = platform_asset_suffix()
    matches = [a for a in release["assets"] if a["name"].startswith("tunnel-client-v") and a["name"].endswith(suffix)]
    if len(matches) != 1:
        raise RuntimeError("Could not identify exactly one official tunnel-client binary")
    asset = matches[0]
    digest = asset.get("digest", "")
    if not digest.startswith("sha256:"):
        raise RuntimeError("The official release asset has no SHA-256 digest")
    download = asset["browser_download_url"]
    if not download.startswith("https://github.com/openai/tunnel-client/releases/download/"):
        raise RuntimeError("Unexpected release download URL")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="garmin-tunnel-install-") as temporary:
        archive = Path(temporary) / "client.zip"
        with urlopen(download, timeout=120) as response, archive.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
        with archive.open("rb") as source:
            actual = hashlib.file_digest(source, "sha256").hexdigest()
        if actual != digest.removeprefix("sha256:"):
            raise RuntimeError("Release checksum mismatch; installation stopped")
        with ZipFile(archive) as zipped:
            names = [n for n in zipped.namelist() if Path(n).name == "tunnel-client"]
            if len(names) != 1:
                raise RuntimeError("Could not identify the binary inside the verified archive")
            payload = zipped.read(names[0])
        # Extract only the binary to a fixed path; never extract archive paths.
        temporary_binary = target.with_name(".tunnel-client-installing")
        with temporary_binary.open("wb") as output:
            output.write(payload)
        temporary_binary.chmod(0o755)
        os.replace(temporary_binary, target)
    print(f"Installed official tunnel-client {release['tag_name']} at {target}")


if __name__ == "__main__":
    main()
