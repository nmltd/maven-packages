"""Publish validated binary copies under distinct public Maven artifact names."""
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as E
import zipfile

artifact = os.environ["ARTIFACT"]
source = os.environ["SOURCE_ARTIFACT"]
version = os.environ["VERSION"]
group = os.environ["GROUP"]
repo = "nmltd/maven-packages"
folder = Path("release") / source
folder.mkdir(parents=True, exist_ok=True)
subprocess.run(["gh", "release", "download", os.environ["RELEASE_TAG"], "--repo", repo, "--dir", str(folder),
    "--pattern", "*.jar", "--pattern", "*.pom", "--pattern", "SHA256SUMS"], check=True)
expected_files = {source + "-" + version + ext for ext in [".jar", "-javadoc.jar", ".pom"]} | {"SHA256SUMS"}
assert {p.name for p in folder.iterdir()} == expected_files, "Unexpected release files"
subprocess.run(["sha256sum", "--check", "SHA256SUMS"], cwd=folder, check=True)
ns = "{http://maven.apache.org/POM/4.0.0}"
E.register_namespace("", "http://maven.apache.org/POM/4.0.0")
tree = E.parse(folder / (source + "-" + version + ".pom"))
root = tree.getroot()
for name, expected in [("groupId", group), ("artifactId", source), ("version", version)]:
    assert root.findtext(ns + name) == expected, name
assert root.find(ns + "parent") is None
assert root.find(ns + "dependencies") is None
for path in folder.glob("*.jar"):
    with zipfile.ZipFile(path) as jar:
        assert jar.testzip() is None
        assert not any(n.endswith((".lic", ".key")) for n in jar.namelist())
        # Retain the original bundled third-party heap sources, never NM sources.
        assert not any(n.endswith(".java") and not n.startswith(("org/teneighty/heap/", "java/org/teneighty/heap/")) for n in jar.namelist())
root.find(ns + "artifactId").text = artifact
pom = Path("public-" + artifact + ".pom")
tree.write(pom, encoding="utf-8", xml_declaration=True)
jar = folder / (source + "-" + version + ".jar")
docs = folder / (source + "-" + version + "-javadoc.jar")
subprocess.run(["mvn", "-B", "-ntp", "org.apache.maven.plugins:maven-deploy-plugin:3.1.4:deploy-file",
    "-DrepositoryId=github-public", "-Durl=https://maven.pkg.github.com/" + repo,
    "-Dfile=" + str(jar), "-Djavadoc=" + str(docs), "-DpomFile=" + str(pom), "-DgeneratePom=false"], check=True)
cache = Path(os.environ["RUNNER_TEMP"]) / ("fresh-maven-" + artifact)
output = Path(os.environ["RUNNER_TEMP"]) / ("downloaded-" + artifact)
consumer = Path("verification-" + artifact + ".xml")
consumer.write_text('<project xmlns="http://maven.apache.org/POM/4.0.0"><modelVersion>4.0.0</modelVersion>'
    '<groupId>tech.nmfin.check</groupId><artifactId>public-download-check</artifactId><version>1</version>'
    '<repositories><repository><id>github-public</id><url>https://maven.pkg.github.com/' + repo + '</url>'
    '<snapshots><enabled>true</enabled></snapshots></repository></repositories></project>')
for suffix, original in [("jar", jar), ("jar:javadoc", docs), ("pom", pom)]:
    target = output / suffix.replace(":", "-")
    subprocess.run(["mvn", "-B", "-ntp", "-U", "-Dmaven.repo.local=" + str(cache), "-f", str(consumer),
        "org.apache.maven.plugins:maven-dependency-plugin:3.8.1:copy",
        "-Dartifact=" + group + ":" + artifact + ":" + version + ":" + suffix,
        "-DoutputDirectory=" + str(target)], check=True)
    files = list(target.iterdir())
    assert len(files) == 1
    assert files[0].read_bytes() == original.read_bytes(), "Downloaded artifact differs"
print("Published and verified public Maven distribution:", group + ":" + artifact + ":" + version)
