"""Publish and verify a checksum-validated customer distribution from a public release."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as E
import zipfile

artifact = os.environ["ARTIFACT"]
version = os.environ["VERSION"]
group = os.environ["GROUP"]
tag = os.environ["RELEASE_TAG"]
repo = "nmltd/maven-packages"
folder = Path("release") / artifact
folder.mkdir(parents=True, exist_ok=True)
subprocess.run(["gh", "release", "download", tag, "--repo", repo, "--dir", str(folder),
    "--pattern", "*.jar", "--pattern", "*.pom", "--pattern", "SHA256SUMS"], check=True)
expected_files = {artifact + "-" + version + ext for ext in [".jar", "-javadoc.jar", ".pom"]} | {"SHA256SUMS"}
assert {p.name for p in folder.iterdir()} == expected_files, "Unexpected release files"
subprocess.run(["sha256sum", "--check", "SHA256SUMS"], cwd=folder, check=True)
pom = folder / (artifact + "-" + version + ".pom")
root = E.parse(pom).getroot()
ns = "{http://maven.apache.org/POM/4.0.0}"
for name, expected in [("groupId", group), ("artifactId", artifact), ("version", version)]:
    assert root.findtext(ns + name) == expected, name
assert root.find(ns + "parent") is None
assert root.find(ns + "dependencies") is None
for path in folder.glob("*.jar"):
    with zipfile.ZipFile(path) as jar:
        assert jar.testzip() is None
        assert not any(n.endswith((".lic", ".key")) for n in jar.namelist())
        assert not any(n.endswith(".java") and not n.startswith(("org/teneighty/heap/", "java/org/teneighty/heap/")) for n in jar.namelist())
jar = folder / (artifact + "-" + version + ".jar")
docs = folder / (artifact + "-" + version + "-javadoc.jar")
subprocess.run(["mvn", "-B", "-ntp", "org.apache.maven.plugins:maven-deploy-plugin:3.1.4:deploy-file",
    "-DrepositoryId=github-public", "-Durl=https://maven.pkg.github.com/" + repo,
    "-Dfile=" + str(jar), "-Djavadoc=" + str(docs), "-DpomFile=" + str(pom), "-DgeneratePom=false"], check=True)
cache = Path(os.environ["RUNNER_TEMP"]) / ("fresh-maven-" + artifact)
output = Path(os.environ["RUNNER_TEMP"]) / ("downloaded-" + artifact)
consumer = Path("verification-pom.xml")
consumer.write_text('<project xmlns="http://maven.apache.org/POM/4.0.0"><modelVersion>4.0.0</modelVersion>'
    '<groupId>tech.nmfin.check</groupId><artifactId>public-download-check</artifactId><version>1</version>'
    '<repositories><repository><id>github-public</id><url>https://maven.pkg.github.com/' + repo + '</url>'
    '<snapshots><enabled>true</enabled></snapshots></repository></repositories></project>')
for suffix, original in [("jar", jar), ("jar:javadoc", docs), ("pom", pom)]:
    target = output / suffix.replace(":", "-")
    subprocess.run(["mvn", "-B", "-ntp", "-U", "-Dmaven.repo.local=" + str(cache), "-f", str(consumer),
        "org.apache.maven.plugins:maven-dependency-plugin:3.8.1:copy",
        "-Dartifact=" + group + ":" + artifact + ":" + version + ":" + suffix,
        "-DremoteRepositories=github-public::default::https://maven.pkg.github.com/" + repo,
        "-DoutputDirectory=" + str(target)], check=True)
    files = list(target.iterdir())
    assert len(files) == 1
    assert files[0].read_bytes() == original.read_bytes(), "Downloaded artifact differs"
print("Published and verified public Maven distribution:", group + ":" + artifact + ":" + version)
