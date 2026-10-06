# Morphe AutoBuilds

Personal, configuration-driven Android patch builds. GitHub Actions builds the
entries you define each day and publishes them to the `latest` release.

## Configure a build

Each entry appears once in `patch-config.json`:

```json
{
  "patch_list": [
    { "app_name": "your-app", "source": "your-source" }
  ]
}
```

Choose one or more target architectures in `arch-config.json`:

```json
[
  {
    "app_name": "your-app",
    "source": "your-source",
    "arches": ["universal"]
  }
]
```

Add store definitions under `apps/` for the download providers you want to use.
The builder tries APKMirror, Aptoide, GitHub, Codeberg, Uptodown, APKPure, and
APKCombo in that order when the corresponding definition is available.

Add one source definition at `sources/your-source.json`. A Morphe source needs
the Morphe CLI and the patch bundle release:

```json
[
  { "name": "your-source" },
  { "user": "MorpheApp", "repo": "morphe-cli", "tag": "latest" },
  { "user": "owner", "repo": "patch-bundle", "tag": "latest" }
]
```

To explicitly enable or disable patches, add
`patches/your-app-your-source.txt`. Prefix a patch name with `+` to enable it
or `-` to disable it. Options can be included as `{key=value}` after an enabled
patch name.

## Build and release

Run **Build curated APKs** from the Actions tab to build immediately. The same
workflow runs daily at 06:00 UTC and replaces the `latest` release with the
newest successful build artifacts.

For a local build, install Python 3.11+, Java, `zip`, and Android `apksigner`.
Then install dependencies and run:

```bash
pip install -r requirements.txt
APP_NAME="your-app" SOURCE="your-source" ARCH="universal" python -m src
```

## Project layout

```text
apps/          Store download definitions
sources/       Patch tool and bundle definitions
patches/       Optional per-entry patch rules
src/           Build implementation
.github/       Scheduled GitHub Actions workflow
```
