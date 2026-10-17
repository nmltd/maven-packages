"""Upload a validated distribution and advance the public registry manifest."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import xml.etree.ElementTree as E
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument("--artifact", choices=["algoquant", "nmdev"], required=True)
parser.add_argument("--jar", required=True)
parser.add_argument("--javadoc", required=True)
parser.add_argument("--pom", required=True)
args = parser.parse_args()
repo = "nmltd/maven-packages"
ns = "{http://maven.apache.org/POM/4.0.0}"
root = E.parse(args.pom).getroot()
version = root.findtext(ns + "version")
group = root.findtext(ns + "groupId")
assert root.findtext(ns + "artifactId") == args.artifact
assert group == {"algoquant": "tech.nmfin", "nmdev": "dev.nm"}[args.artifact]
assert root.find(ns + "parent") is None and root.find(ns + "dependencies") is None
assert version and all(c.isalnum() or c in ".-_" for c in version)
for name in [args.jar, args.javadoc]:
    with zipfile.ZipFile(name) as jar:
        assert jar.testzip() is None
        assert not any(n.endswith((".lic", ".key")) for n in jar.namelist())
        assert not any(n.endswith(".java") and not n.startswith(("org/teneighty/heap/", "java/org/teneighty/heap/")) for n in jar.namelist())

def call(*params, data=None):
    return subprocess.check_output(["gh", *params], input=data, text=True)

def api(path):
    return json.loads(call("api", path))

assert api("repos/" + repo)["private"] is False
source_sha = os.environ["GITHUB_SHA"]
tag = args.artifact + "-" + version.lower() + "-" + source_sha[:12]
with tempfile.TemporaryDirectory() as temporary:
    folder = Path(temporary)
    for source, suffix in [(args.jar, ".jar"), (args.javadoc, "-javadoc.jar"), (args.pom, ".pom")]:
        shutil.copyfile(source, folder / (args.artifact + "-" + version + suffix))
    (folder / "SHA256SUMS").write_text("".join(
        hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.name + "\n"
        for p in sorted(folder.iterdir())))
    assets = [str(p) for p in sorted(folder.iterdir())]
    exists = subprocess.run(["gh", "release", "view", tag, "--repo", repo],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    if exists:
        subprocess.run(["gh", "release", "upload", tag, "--repo", repo, "--clobber", *assets], check=True)
    else:
        subprocess.run(["gh", "release", "create", tag, "--repo", repo, "--target", "main",
            "--title", args.artifact + " " + version, "--prerelease", "--notes",
            "Validated obfuscated customer distribution and matching API documentation.", *assets], check=True)
entry = dict(artifact=args.artifact + "-dist", source_artifact=args.artifact, group=group, version=version, tag=tag)
for attempt in range(5):
    current = api("repos/" + repo + "/contents/distributions.json")
    entries = json.loads(base64.b64decode(current["content"]))
    entries = [entry if item["source_artifact"] == args.artifact else item for item in entries]
    payload = dict(message="Publish validated " + args.artifact + " " + version,
        content=base64.b64encode((json.dumps(entries, indent=2) + "\n").encode()).decode(),
        sha=current["sha"], branch="main")
    try:
        result = json.loads(call("api", "--method", "PUT", "repos/" + repo + "/contents/distributions.json",
            "--input", "-", data=json.dumps(payload)))
        commit = result["commit"]["sha"]
        break
    except subprocess.CalledProcessError:
        if attempt == 4: raise
        time.sleep(2)
for attempt in range(30):
    runs = api("repos/" + repo + "/actions/runs?head_sha=" + commit)["workflow_runs"]
    if runs: break
    time.sleep(2)
assert runs, "Public publishing workflow did not start"
subprocess.run(["gh", "run", "watch", str(runs[0]["id"]), "--repo", repo, "--exit-status"], check=True)
print("Public package publication verified:", entry["group"], entry["artifact"], entry["version"])
