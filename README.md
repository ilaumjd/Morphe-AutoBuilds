# Morphe AutoBuilds

Personal, curated Android patch builds using [Morphe](https://github.com/MorpheApp).
GitHub Actions builds every entry in `patch-config.json` daily and publishes the
signed APKs to the `latest` release when a patch bundle changes. Run the workflow
with **force** enabled to rebuild on demand.

## Available builds

| App | Architecture | Obtainium |
| --- | --- | --- |
| TikTok (HushFeed) | universal | [Add to Obtainium](https://apps.obtainium.imranr.dev/redirect?r=obtainium%3A%2F%2Fapp%2F%257B%2522id%2522%253A%2522com.zhiliaoapp.musically%2522%252C%2522url%2522%253A%2522https%253A%252F%252Fgithub.com%252Filaumjd%252FMorphe-AutoBuilds%2522%252C%2522author%2522%253A%2522ilaumjd%2522%252C%2522name%2522%253A%2522TikTok%2520%2528HushFeed%2529%2522%257D) |

The link opens Obtainium with this release source prefilled; confirm the import
to track and update the build.

## Add an app

1. **Add a build entry** in `patch-config.json`:

   ```json
   {
     "patch_list": [
       { "app_name": "your-app", "source": "your-source", "arches": ["universal"] }
     ]
   }
   ```

   `arches` accepts `universal`, `arm64-v8a` and `armeabi-v7a`.

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

Run **Build curated APKs** from the Actions tab, or wait for the daily run at
06:00 UTC. Successful builds replace the `latest` release; the run is marked
failed if any entry could not be built.

Local build (needs Python 3.11+, Java 21 and Android build-tools for `apksigner`):

```bash
pip install -r requirements.txt
python -m src                                    # every entry
APP_NAME=your-app ARCH=arm64-v8a python -m src  # one app / arch
```

Signed APKs are written to `dist/`. Their filenames include the UTC build date,
for example `your-app-universal-your-source-v1.2.3-20261006.apk`.

## Signing

APKs are signed with `keystore/public.jks` by default. To use your own key, set
`KEYSTORE_PATH`, `KEYSTORE_PASSWORD` and `KEYSTORE_ALIAS`. Changing the key
means existing installs must be uninstalled before updating.
