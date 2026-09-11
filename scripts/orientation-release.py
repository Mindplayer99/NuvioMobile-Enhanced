#!/usr/bin/env python3
"""Strict verification and publication for the two pinned Orientation builds."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile

REPO = "Mindplayer99/NuvioMobile-Enhanced"
CERT = "99e3d93e7600c178e71bf80ded2b1d97664e3ef14058c473c4617cb27fd04e35"
BUILDS = {
    "0.4.14": ("fd7577e141b8647a2a26963d5f4157be76cc45bd", 118, "0.4.14-orientation-final"),
    "0.4.15": ("800abba8c44559946b05fcefc3d62474f0cb3752", 120, "0.4.15-orientation"),
}


def run(*args, cwd=None, env=None):
    return subprocess.check_output(args, cwd=cwd, env=env, text=True, stderr=subprocess.STDOUT)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def configure(source):
    # Decode only in the runner; never print configuration or credentials.
    missing = [name for name in ("NUVIO_RELEASE_KEYSTORE_BASE64", "NUVIO_LOCAL_PROPERTIES_BASE64")
               if not os.environ.get(name)]
    require(not missing, "Missing Actions secrets: " + ", ".join(missing))
    key = Path(os.environ["RUNNER_TEMP"]) / "orientation-release.jks"
    key.write_bytes(base64.b64decode(os.environ["NUVIO_RELEASE_KEYSTORE_BASE64"], validate=True))
    key.chmod(0o600)
    raw = base64.b64decode(os.environ["NUVIO_LOCAL_PROPERTIES_BASE64"], validate=True).decode()
    lines = [line for line in raw.splitlines()
             if not re.match(r"\s*(sdk\.dir|NUVIO_RELEASE_STORE_FILE)\s*=", line)]
    props = source / "local.properties"
    props.write_text("\n".join(lines) + f"\nNUVIO_RELEASE_STORE_FILE={key}\n")
    props.chmod(0o600)
    required = ("NUVIO_RELEASE_STORE_PASSWORD", "NUVIO_RELEASE_KEY_ALIAS", "NUVIO_RELEASE_KEY_PASSWORD")
    require(all(re.search(r"^" + name + r"=.+", props.read_text(), re.M) for name in required),
            "Signing configuration is incomplete")
    print("Secure signing configuration installed; values withheld.")


def verify(source, version, apk):
    commit, code, _ = BUILDS[version]
    require(run("git", "rev-parse", "HEAD", cwd=source).strip() == commit, "Unexpected source commit")
    require(not run("git", "status", "--porcelain", "--untracked-files=no", cwd=source).strip(),
            "Tracked source was modified")
    sdk = Path(os.environ.get("ANDROID_HOME") or os.environ["ANDROID_SDK_ROOT"])
    candidates = [p for p in (sdk / "build-tools").iterdir()
                  if re.fullmatch(r"\d+\.\d+\.\d+", p.name)]
    tools = max(candidates, key=lambda p: tuple(map(int, p.name.split("."))))
    certificates = run(str(tools / "apksigner"), "verify", "--print-certs", str(apk))
    digests = re.findall(r"certificate SHA-256 digest:\s*([0-9a-fA-F]+)", certificates)
    require(digests == [CERT], "APK signer does not match the installed app")
    badging = run(str(tools / "aapt2"), "dump", "badging", str(apk))
    require(re.search(r"package: name='com\.nuvio\.media' versionCode='" + str(code)
                      + r"' versionName='" + re.escape(version) + r"'", badging),
            "Wrong APK package/version/versionCode")
    require("application-debuggable" not in badging, "Debuggable APK is not a release build")
    with zipfile.ZipFile(apk) as archive:
        require(archive.testzip() is None, "Corrupt APK archive")
        names = archive.namelist()
        abis = {name.split("/")[1] for name in names if name.startswith("lib/") and name.endswith(".so")}
        require(abis == {"arm64-v8a"}, "APK must contain only ARM64 native libraries")
        for name in ("libmpv.so", "libquickjs.so", "libnuvio_engine.so", "libass.so"):
            require("lib/arm64-v8a/" + name in names, "Missing Full native library: " + name)
    return {"commit": commit, "package": "com.nuvio.media", "versionName": version,
            "versionCode": code, "abi": "arm64-v8a", "signer_sha256": CERT,
            "apk_sha256": hashlib.sha256(apk.read_bytes()).hexdigest()}


def api(path, *args, optional=False):
    result = subprocess.run(["gh", "api", f"repos/{REPO}/{path}", *args], capture_output=True, text=True)
    if optional and result.returncode and "HTTP 404" in result.stderr:
        return None
    require(result.returncode == 0, "GitHub API failed for " + path)
    return json.loads(result.stdout) if result.stdout.strip() else None


def publish(source, version, apk):
    record = verify(source, version, apk)
    commit, _, tag = BUILDS[version]
    require(os.environ.get("GITHUB_REPOSITORY") == REPO, "Publication restricted to the owner's repository")
    name = f"Nuvio-Enhanced-{version}-Orientation-Full-arm64-v8a.apk"
    ref = api(f"git/ref/tags/{tag}", optional=True)
    if ref is None:
        api("git/refs", "--method", "POST", "-f", f"ref=refs/tags/{tag}", "-f", f"sha={commit}")
    else:
        require(ref["object"]["type"] == "commit" and ref["object"]["sha"] == commit,
                "Existing tag does not point to the exact required source")
    release = api(f"releases/tags/{tag}", optional=True)
    if release and not release["draft"]:
        # A retry must never overwrite an already published release.
        assets = [a for a in release["assets"] if a["name"] == name and a["state"] == "uploaded"]
        require(not release["prerelease"] and len(assets) == 1, "Existing release is incomplete")
        with tempfile.TemporaryDirectory() as temporary:
            run("gh", "release", "download", tag, "--repo", REPO, "--pattern", name, "--dir", temporary)
            verify(source, version, Path(temporary) / name)
        print("Already published and verified: " + assets[0]["browser_download_url"])
        return
    if release is None:
        release = api("releases", "--method", "POST", "-f", f"tag_name={tag}",
                      "-f", f"name=Nuvio Enhanced {version} Orientation", "-F", "draft=true",
                      "-F", "prerelease=false", "-f", "body=" +
                      "Built from the exact preserved source. Full ARM64 release; installed-app signer verified. "
                      "Automated tests and build passed. Real-device smoke testing remains required.\n\n" +
                      "Verification:\n```json\n" + json.dumps(record, indent=2) + "\n```")
    with tempfile.TemporaryDirectory() as temporary:
        target = Path(temporary) / name
        target.write_bytes(apk.read_bytes())
        run("gh", "release", "upload", tag, str(target), "--repo", REPO, "--clobber")
    uploaded = api(f"releases/{release['id']}")
    assets = [a for a in uploaded["assets"] if a["name"] == name and a["state"] == "uploaded"]
    require(len(assets) == 1 and assets[0]["size"] == apk.stat().st_size, "Uploaded asset is missing or truncated")
    # Verify the actual remote bytes before making the draft visible to the updater.
    with tempfile.TemporaryDirectory() as temporary:
        run("gh", "release", "download", tag, "--repo", REPO, "--pattern", name, "--dir", temporary)
        remote = Path(temporary) / name
        require(hashlib.sha256(remote.read_bytes()).hexdigest() == record["apk_sha256"],
                "Uploaded asset digest mismatch")
        verify(source, version, remote)
    api(f"releases/{release['id']}", "--method", "PATCH", "-F", "draft=false",
        "-f", "make_latest=" + ("false" if version == "0.4.14" else "true"))
    published = api(f"releases/{release['id']}")
    require(not published["draft"], "Release is still a draft")
    print(next(a["browser_download_url"] for a in published["assets"] if a["name"] == name))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("configure", "verify", "publish"))
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--version", choices=BUILDS)
    parser.add_argument("--apk", type=Path)
    args = parser.parse_args()
    if args.action == "configure":
        configure(args.source)
    else:
        require(args.version is not None and args.apk is not None, "Version and APK are required")
        if args.action == "verify":
            print(json.dumps(verify(args.source, args.version, args.apk), indent=2))
        else:
            publish(args.source, args.version, args.apk)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError:
        raise SystemExit("External verification/publication command failed; no unverified APK is published.")
    except (RuntimeError, ValueError) as error:
        raise SystemExit(str(error))
