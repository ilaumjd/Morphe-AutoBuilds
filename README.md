# Morphe AutoBuilds

Personal, curated Android patch builds using [Morphe](https://github.com/MorpheApp).
A local runner builds every entry in `patch-config.json` daily and publishes the
signed APKs to the `latest` release when a patch bundle changes. The GitHub
Actions workflow is disabled (`.github/workflows/patch.yml.disabled`); rename it
back to `patch.yml` to re-enable it. Rebuild on demand with
`docker-compose run --rm -e FORCE_BUILD=1 builder once`.

## Available builds

| App | Architecture | Obtainium |
| --- | --- | --- |
| TikTok (HushFeed) | arm64-v8a, universal fallback | [Add to Obtainium](https://apps.obtainium.imranr.dev/redirect?r=obtainium%3A%2F%2Fapp%2F%257B%2522id%2522%253A%2522com.zhiliaoapp.musically%2522%252C%2522url%2522%253A%2522https%253A%252F%252Fgithub.com%252Filaumjd%252FMorphe-AutoBuilds%2522%252C%2522author%2522%253A%2522ilaumjd%2522%252C%2522name%2522%253A%2522TikTok%2520%2528HushFeed%2529%2522%257D) |

The link opens Obtainium with this release source prefilled; confirm the import
to track and update the build.

## Add an app

1. **Add a build entry** in `patch-config.json`:

   ```json
   {
     "patch_list": [
       { "app_name": "your-app", "source": "your-source", "arches": ["arm64-v8a"] }
     ]
   }
   ```

   `arches` accepts `arm64-v8a`, `armeabi-v7a`, and `universal`. An
   `arm64-v8a` entry automatically retries as universal only when its ARM64
   build cannot be produced.

2. **Describe where to download the app** in `apps/<store>/<app_name>.json`.
   Stores are tried in order: APKMirror, Aptoide, Uptodown, APKPure. A store
   without its own file reuses the `package`/`version` from another store's
   file. Example:

   ```json
   {
     "org": "publisher",
     "name": "your-app",
     "type": "APK",
     "arch": "universal",
     "dpi": "nodpi",
     "package": "com.example.app",
     "version": ""
   }
   ```

   `version` pins the app version. Leave it out to build the newest version
   the patch bundle declares compatible.

   Store-specific notes:

   - **APKPure** (`apps/apkpure/<app>.json`) needs the app's slug and package from
     its `apkpure.com/<name>/<package>` URL: `{ "name": "<name>", "package": "<package>" }`.
     Pages are rendered through trawl.
   - **APKMirror** `release_prefix` is the release slug without the version, e.g.
     `microsoft-swiftkey-ai-keyboard` for `…-9-13-13-5-release`.

3. **Define the patch source** in `sources/<source>.json`: a display name
   (used in the APK filename), the Morphe CLI release and the patch bundle
   release. `tag` is `latest`, `prerelease` or an explicit tag.

   ```json
   [
     { "name": "your-source" },
     { "user": "MorpheApp", "repo": "morphe-cli", "tag": "latest" },
     { "user": "owner", "repo": "patch-bundle", "tag": "latest" }
   ]
   ```

4. **Optionally select patches** in `patches/<app_name>-<source>.txt`, one per
   line:

   ```text
   - Patch to disable
   + Patch to enable
   + Patch with options {key=value, other=value}
   ```

## Build and release

The local runner (see below) builds daily at 06:00 UTC. Successful builds replace
the `latest` release; the run fails if any entry could not be built.

Local build (needs Python 3.11+, Java 21 and Android build-tools for `apksigner`):

```bash
pip install -r requirements.txt
python -m src download                            # download/cache every original APK
python -m src patch                               # patch only APKs already in the cache
python -m src                                     # download and patch every entry
APP_NAME=your-app ARCH=arm64-v8a python -m src download  # one app / arch
```

## APK folders

All APKs live under `apks/` (ignored by Git):

```text
apks/
  original/   <app>-<arch>-original-v<version>.<ext>   (.apk, .apks, .apkm or .xapk)
  patched/    <app>-<arch>-<source>-v<version>-<UTC date>.apk
```

The pipeline never deletes anything in either folder. It finds an original purely
by its name (for example `tiktok-arm64-v8a-original-v47.1.4.apk`), so a stock APK
you place there by hand with the right name is used as-is. Originals are reused
by later builds of the same app, version, and architecture, and `python -m src
patch` never downloads a base APK; it only uses `apks/original/`. Patched
builds accumulate, and only the APKs built in the current run are published to
the release (a rebuild on the same day overwrites that day's file of the same
name). Override the locations with `APKS_DIR`, `ORIGINAL_APKS_DIR` or
`PATCHED_APKS_DIR`.

To fetch an original from a specific direct link instead of querying an app
store, add a pinned `version` and `download_url` to that app's store
configuration, or use a one-off `APK_URL` environment variable:

```bash
APP_NAME=your-app SOURCE=your-source ARCH=arm64-v8a \
APK_URL='https://example.com/your-app.apk' python -m src download
```

## Local Void Linux runner

`docker-compose.yml` runs the pipeline in a persistent container and keeps base
APK downloads and patched builds in the local `apks/` folder. It checks for patch updates on
startup and every day at 06:00 UTC, then publishes successful builds to the
`latest` GitHub release.

Create a `.env` file beside `docker-compose.yml` with a GitHub token that can
write repository releases:

```text
GH_TOKEN=github_pat_...
```

The runner runs as user 1000:1000 so the files it writes (`apks/`, downloaded
tools) belong to you. If your ids differ, add `PUID=` and `PGID=` lines to `.env`.

Start the runner with `docker-compose up -d --build`. To run it once manually,
use `docker-compose run --rm builder once`.

## Signing

APKs are signed with `keystore/public.jks` by default. To use your own key, set
`KEYSTORE_PATH`, `KEYSTORE_PASSWORD` and `KEYSTORE_ALIAS`. Changing the key
means existing installs must be uninstalled before updating.
