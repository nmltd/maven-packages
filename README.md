# NM public Maven distributions

Public binary distributions of **AlgoQuant** and **NM Dev**. Implementation sources remain in private repositories. Customer JARs are combined distributions; matching Javadoc and standalone consumer POMs are published with them.

## Maven repository

```xml
<repository>
    <id>github-nm-packages</id>
    <url>https://maven.pkg.github.com/nmltd/maven-packages</url>
    <snapshots><enabled>true</enabled></snapshots>
</repository>
```

Choose the library your application needs:

| Library | Group ID | Artifact ID | Version |
|---|---|---|---|
| AlgoQuant | tech.nmfin | algoquant-dist | 3.3.0-SNAPSHOT |
| NM Dev | dev.nm | nmdev-dist | 1.2.6-SNAPSHOT |

AlgoQuant already includes NM Dev. Avoid adding both combined JARs to the same application.

## Authentication

GitHub's Maven registry requires authentication even for public packages. Use **your own GitHub username and personal access token (classic) with read:packages** in `~/.m2/settings.xml`:

```xml
<settings>
    <servers>
        <server>
            <id>github-nm-packages</id>
            <username>YOUR_GITHUB_USERNAME</username>
            <password>YOUR_GITHUB_TOKEN</password>
        </server>
    </servers>
</settings>
```

Public consumers do not need access to the private source repositories or an NM internal build token. A valid NM license is still required for licensed functionality.

## Downloads and verification

Validated JARs, POMs, Javadoc JARs and SHA-256 checksums are also available under [Releases](https://github.com/nmltd/maven-packages/releases). See the publication workflow for current package publication results.

Publication checks release checksums, rejects implementation source and license files, deploys with this repository's built-in GitHub Actions token, then downloads the JAR, POM and Javadoc into a fresh Maven cache and compares their bytes.

- [AlgoQuant Javadoc](https://nmltd.github.io/algoquant/)
- [NM Dev Javadoc](https://nmltd.github.io/nmdev/)
- [AlgoQuant starter](https://github.com/nmltd/new-algoquant-project)
- [NM Dev starter](https://github.com/nmltd/numerical-methods-java/tree/main/samples/new-nmdev-project)

Public artifact IDs end in `-dist` because GitHub does not allow the existing private package names to be associated with a second repository. Java package names and the validated JAR bytes are unchanged. The NM Dev JAR retains its original bundled third-party `org.teneighty.heap` source files; no NM implementation source is included.
