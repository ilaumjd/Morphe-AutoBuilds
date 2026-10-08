# Morphe AutoBuilds

Personal, curated Android patch builds using [Morphe](https://github.com/MorpheApp).
A local runner builds every entry in `patch-config.json` daily and publishes the
signed APKs to the `latest` release when a patch bundle changes. The GitHub
Actions workflow is disabled (`.github/workflows/patch.yml.disabled`); rename it
back to `patch.yml` to re-enable it. Rebuild on demand with
`docker-compose run --rm -e FORCE_BUILD=1 builder once`.

## Available builds

<!-- available-builds:start -->
| App | Patches | Architecture | Obtainium |
| --- | --- | --- | --- |
| Brave | [Kveld](https://github.com/kveld9/kveld-morphe-patches) | arm64-v8a | [Add to Obtainium](https://apps.obtainium.imranr.dev/redirect?r=obtainium%3A%2F%2Fapp%2F%257B%2522id%2522%253A%2522com.brave.browser%2522%252C%2522url%2522%253A%2522https%253A%252F%252Fgithub.com%252Filaumjd%252FMorphe-AutoBuilds%2522%252C%2522author%2522%253A%2522ilaumjd%2522%252C%2522name%2522%253A%2522Brave%2520%2528Kveld%2529%2522%252C%2522additionalSettings%2522%253A%2522%257B%255C%2522apkFilterRegEx%255C%2522%253A%255C%2522%255Ebrave-%255C%2522%252C%255C%2522versionDetection%255C%2522%253Afalse%257D%2522%257D) |
| CapCut | [Riky](https://github.com/riky-dev/morphe-patches) | arm64-v8a | [Add to Obtainium](https://apps.obtainium.imranr.dev/redirect?r=obtainium%3A%2F%2Fapp%2F%257B%2522id%2522%253A%2522com.lemon.lvoverseas%2522%252C%2522url%2522%253A%2522https%253A%252F%252Fgithub.com%252Filaumjd%252FMorphe-AutoBuilds%2522%252C%2522author%2522%253A%2522ilaumjd%2522%252C%2522name%2522%253A%2522CapCut%2520%2528Riky%2529%2522%252C%2522additionalSettings%2522%253A%2522%257B%255C%2522apkFilterRegEx%255C%2522%253A%255C%2522%255Ecapcut-%255C%2522%252C%255C%2522versionDetection%255C%2522%253Afalse%257D%2522%257D) |
| Chess.com | [Prathxm](https://github.com/PrathxmOp/Prathxm-Patches) | arm64-v8a | [Add to Obtainium](https://apps.obtainium.imranr.dev/redirect?r=obtainium%3A%2F%2Fapp%2F%257B%2522id%2522%253A%2522com.chess%2522%252C%2522url%2522%253A%2522https%253A%252F%252Fgithub.com%252Filaumjd%252FMorphe-AutoBuilds%2522%252C%2522author%2522%253A%2522ilaumjd%2522%252C%2522name%2522%253A%2522Chess.com%2520%2528Prathxm%2529%2522%252C%2522additionalSettings%2522%253A%2522%257B%255C%2522apkFilterRegEx%255C%2522%253A%255C%2522%255Echess-%255C%2522%252C%255C%2522versionDetection%255C%2522%253Afalse%257D%2522%257D) |
| Gboard | [JasonWu](https://github.com/jasonwu1994/Gboard-patches) | arm64-v8a | [Add to Obtainium](https://apps.obtainium.imranr.dev/redirect?r=obtainium%3A%2F%2Fapp%2F%257B%2522id%2522%253A%2522dev.jason.com.google.android.inputmethod.latin%2522%252C%2522url%2522%253A%2522https%253A%252F%252Fgithub.com%252Filaumjd%252FMorphe-AutoBuilds%2522%252C%2522author%2522%253A%2522ilaumjd%2522%252C%2522name%2522%253A%2522Gboard%2520%2528JasonWu%2529%2522%252C%2522additionalSettings%2522%253A%2522%257B%255C%2522apkFilterRegEx%255C%2522%253A%255C%2522%255Egboard-%255C%2522%252C%255C%2522versionDetection%255C%2522%253Afalse%257D%2522%257D) |
| Google Maps | [BearInMindCat](https://github.com/bearinmindcat/morphe-patches) | arm64-v8a | [Add to Obtainium](https://apps.obtainium.imranr.dev/redirect?r=obtainium%3A%2F%2Fapp%2F%257B%2522id%2522%253A%2522org.ungoogled.android.apps.maps%2522%252C%2522url%2522%253A%2522https%253A%252F%252Fgithub.com%252Filaumjd%252FMorphe-AutoBuilds%2522%252C%2522author%2522%253A%2522ilaumjd%2522%252C%2522name%2522%253A%2522Google%2520Maps%2520%2528BearInMindCat%2529%2522%252C%2522additionalSettings%2522%253A%2522%257B%255C%2522apkFilterRegEx%255C%2522%253A%255C%2522%255Emaps-%255C%2522%252C%255C%2522versionDetection%255C%2522%253Afalse%257D%2522%257D) |
| Home Workout | [Rushiranpise](https://github.com/rushiranpise/morphe-patches) | arm64-v8a | [Add to Obtainium](https://apps.obtainium.imranr.dev/redirect?r=obtainium%3A%2F%2Fapp%2F%257B%2522id%2522%253A%2522homeworkout.homeworkouts.noequipment%2522%252C%2522url%2522%253A%2522https%253A%252F%252Fgithub.com%252Filaumjd%252FMorphe-AutoBuilds%2522%252C%2522author%2522%253A%2522ilaumjd%2522%252C%2522name%2522%253A%2522Home%2520Workout%2520%2528Rushiranpise%2529%2522%252C%2522additionalSettings%2522%253A%2522%257B%255C%2522apkFilterRegEx%255C%2522%253A%255C%2522%255Ehomeworkout-%255C%2522%252C%255C%2522versionDetection%255C%2522%253Afalse%257D%2522%257D) |
| JellyWatch TV | [FranticG33k](https://github.com/franticg33k/morphe-patches) | arm64-v8a | [Add to Obtainium](https://apps.obtainium.imranr.dev/redirect?r=obtainium%3A%2F%2Fapp%2F%257B%2522id%2522%253A%2522com.jellywatch.tv%2522%252C%2522url%2522%253A%2522https%253A%252F%252Fgithub.com%252Filaumjd%252FMorphe-AutoBuilds%2522%252C%2522author%2522%253A%2522ilaumjd%2522%252C%2522name%2522%253A%2522JellyWatch%2520TV%2520%2528FranticG33k%2529%2522%252C%2522additionalSettings%2522%253A%2522%257B%255C%2522apkFilterRegEx%255C%2522%253A%255C%2522%255Ejellywatchtv-%255C%2522%252C%255C%2522versionDetection%255C%2522%253Afalse%257D%2522%257D) |
| LinkedIn | [Michii](https://github.com/heyymichii/michii-patches) | universal | [Add to Obtainium](https://apps.obtainium.imranr.dev/redirect?r=obtainium%3A%2F%2Fapp%2F%257B%2522id%2522%253A%2522com.linkedin.android%2522%252C%2522url%2522%253A%2522https%253A%252F%252Fgithub.com%252Filaumjd%252FMorphe-AutoBuilds%2522%252C%2522author%2522%253A%2522ilaumjd%2522%252C%2522name%2522%253A%2522LinkedIn%2520%2528Michii%2529%2522%252C%2522additionalSettings%2522%253A%2522%257B%255C%2522apkFilterRegEx%255C%2522%253A%255C%2522%255Elinkedin-%255C%2522%252C%255C%2522versionDetection%255C%2522%253Afalse%257D%2522%257D) |
| Quranify | [HxReborn](https://github.com/hxreborn/morphe-patches) | arm64-v8a | [Add to Obtainium](https://apps.obtainium.imranr.dev/redirect?r=obtainium%3A%2F%2Fapp%2F%257B%2522id%2522%253A%2522com.mchutov.Quranify%2522%252C%2522url%2522%253A%2522https%253A%252F%252Fgithub.com%252Filaumjd%252FMorphe-AutoBuilds%2522%252C%2522author%2522%253A%2522ilaumjd%2522%252C%2522name%2522%253A%2522Quranify%2520%2528HxReborn%2529%2522%252C%2522additionalSettings%2522%253A%2522%257B%255C%2522apkFilterRegEx%255C%2522%253A%255C%2522%255Equranify-%255C%2522%252C%255C%2522versionDetection%255C%2522%253Afalse%257D%2522%257D) |
| Reddit | [Adobo](https://github.com/jkennethcarino/adobo) | arm64-v8a | [Add to Obtainium](https://apps.obtainium.imranr.dev/redirect?r=obtainium%3A%2F%2Fapp%2F%257B%2522id%2522%253A%2522com.reddit.frontpage%2522%252C%2522url%2522%253A%2522https%253A%252F%252Fgithub.com%252Filaumjd%252FMorphe-AutoBuilds%2522%252C%2522author%2522%253A%2522ilaumjd%2522%252C%2522name%2522%253A%2522Reddit%2520%2528Adobo%2529%2522%252C%2522additionalSettings%2522%253A%2522%257B%255C%2522apkFilterRegEx%255C%2522%253A%255C%2522%255Ereddit-%255C%2522%252C%255C%2522versionDetection%255C%2522%253Afalse%257D%2522%257D) |
| Sticker.ly | [Rushiranpise](https://github.com/rushiranpise/morphe-patches) | arm64-v8a | [Add to Obtainium](https://apps.obtainium.imranr.dev/redirect?r=obtainium%3A%2F%2Fapp%2F%257B%2522id%2522%253A%2522com.snowcorp.stickerly.android%2522%252C%2522url%2522%253A%2522https%253A%252F%252Fgithub.com%252Filaumjd%252FMorphe-AutoBuilds%2522%252C%2522author%2522%253A%2522ilaumjd%2522%252C%2522name%2522%253A%2522Sticker.ly%2520%2528Rushiranpise%2529%2522%252C%2522additionalSettings%2522%253A%2522%257B%255C%2522apkFilterRegEx%255C%2522%253A%255C%2522%255Estickerly-%255C%2522%252C%255C%2522versionDetection%255C%2522%253Afalse%257D%2522%257D) |
| SwiftKey | [Hoomans](https://github.com/arandomhooman/hoomans-morphe-patches) | arm64-v8a | [Add to Obtainium](https://apps.obtainium.imranr.dev/redirect?r=obtainium%3A%2F%2Fapp%2F%257B%2522id%2522%253A%2522com.touchtype.swiftkey%2522%252C%2522url%2522%253A%2522https%253A%252F%252Fgithub.com%252Filaumjd%252FMorphe-AutoBuilds%2522%252C%2522author%2522%253A%2522ilaumjd%2522%252C%2522name%2522%253A%2522SwiftKey%2520%2528Hoomans%2529%2522%252C%2522additionalSettings%2522%253A%2522%257B%255C%2522apkFilterRegEx%255C%2522%253A%255C%2522%255Eswiftkey-%255C%2522%252C%255C%2522versionDetection%255C%2522%253Afalse%257D%2522%257D) |
| Termius | [Rushiranpise](https://github.com/rushiranpise/morphe-patches) | arm64-v8a | [Add to Obtainium](https://apps.obtainium.imranr.dev/redirect?r=obtainium%3A%2F%2Fapp%2F%257B%2522id%2522%253A%2522com.server.auditor.ssh.client%2522%252C%2522url%2522%253A%2522https%253A%252F%252Fgithub.com%252Filaumjd%252FMorphe-AutoBuilds%2522%252C%2522author%2522%253A%2522ilaumjd%2522%252C%2522name%2522%253A%2522Termius%2520%2528Rushiranpise%2529%2522%252C%2522additionalSettings%2522%253A%2522%257B%255C%2522apkFilterRegEx%255C%2522%253A%255C%2522%255Etermius-%255C%2522%252C%255C%2522versionDetection%255C%2522%253Afalse%257D%2522%257D) |
| TikTok | [HushFeed](https://github.com/SysAdminDoc/hushfeed) | arm64-v8a | [Add to Obtainium](https://apps.obtainium.imranr.dev/redirect?r=obtainium%3A%2F%2Fapp%2F%257B%2522id%2522%253A%2522com.zhiliaoapp.musically%2522%252C%2522url%2522%253A%2522https%253A%252F%252Fgithub.com%252Filaumjd%252FMorphe-AutoBuilds%2522%252C%2522author%2522%253A%2522ilaumjd%2522%252C%2522name%2522%253A%2522TikTok%2520%2528HushFeed%2529%2522%252C%2522additionalSettings%2522%253A%2522%257B%255C%2522apkFilterRegEx%255C%2522%253A%255C%2522%255Etiktok-%255C%2522%252C%255C%2522versionDetection%255C%2522%253Afalse%257D%2522%257D) |

[Add all 14 apps to Obtainium at once](https://apps.obtainium.imranr.dev/redirect?r=obtainium%3A%2F%2Fapps%2F%255B%257B%2522id%2522%253A%2522com.brave.browser%2522%252C%2522url%2522%253A%2522https%253A%252F%252Fgithub.com%252Filaumjd%252FMorphe-AutoBuilds%2522%252C%2522author%2522%253A%2522ilaumjd%2522%252C%2522name%2522%253A%2522Brave%2520%2528Kveld%2529%2522%252C%2522additionalSettings%2522%253A%2522%257B%255C%2522apkFilterRegEx%255C%2522%253A%255C%2522%255Ebrave-%255C%2522%252C%255C%2522versionDetection%255C%2522%253Afalse%257D%2522%257D%252C%257B%2522id%2522%253A%2522com.lemon.lvoverseas%2522%252C%2522url%2522%253A%2522https%253A%252F%252Fgithub.com%252Filaumjd%252FMorphe-AutoBuilds%2522%252C%2522author%2522%253A%2522ilaumjd%2522%252C%2522name%2522%253A%2522CapCut%2520%2528Riky%2529%2522%252C%2522additionalSettings%2522%253A%2522%257B%255C%2522apkFilterRegEx%255C%2522%253A%255C%2522%255Ecapcut-%255C%2522%252C%255C%2522versionDetection%255C%2522%253Afalse%257D%2522%257D%252C%257B%2522id%2522%253A%2522com.chess%2522%252C%2522url%2522%253A%2522https%253A%252F%252Fgithub.com%252Filaumjd%252FMorphe-AutoBuilds%2522%252C%2522author%2522%253A%2522ilaumjd%2522%252C%2522name%2522%253A%2522Chess.com%2520%2528Prathxm%2529%2522%252C%2522additionalSettings%2522%253A%2522%257B%255C%2522apkFilterRegEx%255C%2522%253A%255C%2522%255Echess-%255C%2522%252C%255C%2522versionDetection%255C%2522%253Afalse%257D%2522%257D%252C%257B%2522id%2522%253A%2522dev.jason.com.google.android.inputmethod.latin%2522%252C%2522url%2522%253A%2522https%253A%252F%252Fgithub.com%252Filaumjd%252FMorphe-AutoBuilds%2522%252C%2522author%2522%253A%2522ilaumjd%2522%252C%2522name%2522%253A%2522Gboard%2520%2528JasonWu%2529%2522%252C%2522additionalSettings%2522%253A%2522%257B%255C%2522apkFilterRegEx%255C%2522%253A%255C%2522%255Egboard-%255C%2522%252C%255C%2522versionDetection%255C%2522%253Afalse%257D%2522%257D%252C%257B%2522id%2522%253A%2522org.ungoogled.android.apps.maps%2522%252C%2522url%2522%253A%2522https%253A%252F%252Fgithub.com%252Filaumjd%252FMorphe-AutoBuilds%2522%252C%2522author%2522%253A%2522ilaumjd%2522%252C%2522name%2522%253A%2522Google%2520Maps%2520%2528BearInMindCat%2529%2522%252C%2522additionalSettings%2522%253A%2522%257B%255C%2522apkFilterRegEx%255C%2522%253A%255C%2522%255Emaps-%255C%2522%252C%255C%2522versionDetection%255C%2522%253Afalse%257D%2522%257D%252C%257B%2522id%2522%253A%2522homeworkout.homeworkouts.noequipment%2522%252C%2522url%2522%253A%2522https%253A%252F%252Fgithub.com%252Filaumjd%252FMorphe-AutoBuilds%2522%252C%2522author%2522%253A%2522ilaumjd%2522%252C%2522name%2522%253A%2522Home%2520Workout%2520%2528Rushiranpise%2529%2522%252C%2522additionalSettings%2522%253A%2522%257B%255C%2522apkFilterRegEx%255C%2522%253A%255C%2522%255Ehomeworkout-%255C%2522%252C%255C%2522versionDetection%255C%2522%253Afalse%257D%2522%257D%252C%257B%2522id%2522%253A%2522com.jellywatch.tv%2522%252C%2522url%2522%253A%2522https%253A%252F%252Fgithub.com%252Filaumjd%252FMorphe-AutoBuilds%2522%252C%2522author%2522%253A%2522ilaumjd%2522%252C%2522name%2522%253A%2522JellyWatch%2520TV%2520%2528FranticG33k%2529%2522%252C%2522additionalSettings%2522%253A%2522%257B%255C%2522apkFilterRegEx%255C%2522%253A%255C%2522%255Ejellywatchtv-%255C%2522%252C%255C%2522versionDetection%255C%2522%253Afalse%257D%2522%257D%252C%257B%2522id%2522%253A%2522com.linkedin.android%2522%252C%2522url%2522%253A%2522https%253A%252F%252Fgithub.com%252Filaumjd%252FMorphe-AutoBuilds%2522%252C%2522author%2522%253A%2522ilaumjd%2522%252C%2522name%2522%253A%2522LinkedIn%2520%2528Michii%2529%2522%252C%2522additionalSettings%2522%253A%2522%257B%255C%2522apkFilterRegEx%255C%2522%253A%255C%2522%255Elinkedin-%255C%2522%252C%255C%2522versionDetection%255C%2522%253Afalse%257D%2522%257D%252C%257B%2522id%2522%253A%2522com.mchutov.Quranify%2522%252C%2522url%2522%253A%2522https%253A%252F%252Fgithub.com%252Filaumjd%252FMorphe-AutoBuilds%2522%252C%2522author%2522%253A%2522ilaumjd%2522%252C%2522name%2522%253A%2522Quranify%2520%2528HxReborn%2529%2522%252C%2522additionalSettings%2522%253A%2522%257B%255C%2522apkFilterRegEx%255C%2522%253A%255C%2522%255Equranify-%255C%2522%252C%255C%2522versionDetection%255C%2522%253Afalse%257D%2522%257D%252C%257B%2522id%2522%253A%2522com.reddit.frontpage%2522%252C%2522url%2522%253A%2522https%253A%252F%252Fgithub.com%252Filaumjd%252FMorphe-AutoBuilds%2522%252C%2522author%2522%253A%2522ilaumjd%2522%252C%2522name%2522%253A%2522Reddit%2520%2528Adobo%2529%2522%252C%2522additionalSettings%2522%253A%2522%257B%255C%2522apkFilterRegEx%255C%2522%253A%255C%2522%255Ereddit-%255C%2522%252C%255C%2522versionDetection%255C%2522%253Afalse%257D%2522%257D%252C%257B%2522id%2522%253A%2522com.snowcorp.stickerly.android%2522%252C%2522url%2522%253A%2522https%253A%252F%252Fgithub.com%252Filaumjd%252FMorphe-AutoBuilds%2522%252C%2522author%2522%253A%2522ilaumjd%2522%252C%2522name%2522%253A%2522Sticker.ly%2520%2528Rushiranpise%2529%2522%252C%2522additionalSettings%2522%253A%2522%257B%255C%2522apkFilterRegEx%255C%2522%253A%255C%2522%255Estickerly-%255C%2522%252C%255C%2522versionDetection%255C%2522%253Afalse%257D%2522%257D%252C%257B%2522id%2522%253A%2522com.touchtype.swiftkey%2522%252C%2522url%2522%253A%2522https%253A%252F%252Fgithub.com%252Filaumjd%252FMorphe-AutoBuilds%2522%252C%2522author%2522%253A%2522ilaumjd%2522%252C%2522name%2522%253A%2522SwiftKey%2520%2528Hoomans%2529%2522%252C%2522additionalSettings%2522%253A%2522%257B%255C%2522apkFilterRegEx%255C%2522%253A%255C%2522%255Eswiftkey-%255C%2522%252C%255C%2522versionDetection%255C%2522%253Afalse%257D%2522%257D%252C%257B%2522id%2522%253A%2522com.server.auditor.ssh.client%2522%252C%2522url%2522%253A%2522https%253A%252F%252Fgithub.com%252Filaumjd%252FMorphe-AutoBuilds%2522%252C%2522author%2522%253A%2522ilaumjd%2522%252C%2522name%2522%253A%2522Termius%2520%2528Rushiranpise%2529%2522%252C%2522additionalSettings%2522%253A%2522%257B%255C%2522apkFilterRegEx%255C%2522%253A%255C%2522%255Etermius-%255C%2522%252C%255C%2522versionDetection%255C%2522%253Afalse%257D%2522%257D%252C%257B%2522id%2522%253A%2522com.zhiliaoapp.musically%2522%252C%2522url%2522%253A%2522https%253A%252F%252Fgithub.com%252Filaumjd%252FMorphe-AutoBuilds%2522%252C%2522author%2522%253A%2522ilaumjd%2522%252C%2522name%2522%253A%2522TikTok%2520%2528HushFeed%2529%2522%252C%2522additionalSettings%2522%253A%2522%257B%255C%2522apkFilterRegEx%255C%2522%253A%255C%2522%255Etiktok-%255C%2522%252C%255C%2522versionDetection%255C%2522%253Afalse%257D%2522%257D%255D)
<!-- available-builds:end -->

All builds are published to the single [`latest` release](https://github.com/ilaumjd/Morphe-AutoBuilds/releases/tag/latest),
which keeps only the newest build of each app. Each Obtainium link opens
Obtainium with this release source prefilled and an APK filter (`^<app>-`) so it
offers only that app's file; confirm the import to add it. Version detection is
off and no pseudo-version is used, so Obtainium just offers whatever APK is on the
release; it does not prompt for updates on its own.

ARM64 builds are preferred; an app is published as `universal` only when no ARM64
original could be obtained. The Google Maps build is
installed as `org.ungoogled.android.apps.maps`, next to the stock app.

## Add an app

1. **Add a build entry** in `patch-config.json`:

   ```json
   {
     "patch_list": [
       { "app_name": "your-app", "source": "your-source", "title": "Your App", "arches": ["arm64-v8a"] }
     ]
   }
   ```

   `arches` accepts `arm64-v8a`, `armeabi-v7a`, and `universal`. An
   `arm64-v8a` entry automatically retries as universal only when its ARM64
   build cannot be produced.

   `title` is the display name used in the README table. Add `"package"` only when
   the patched app installs under a different package id than the store app.

2. **Describe where to download the app** in `apps/<store>/<app_name>.json`.
   Stores are tried in order: APKMirror, Aptoide, Uptodown, APKPure; an app with an
   `apps/github/<app>.json` uses GitHub only. A store without its own file reuses
   the `package`/`version` from another store's file. Example:

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
   - **GitHub** (`apps/github/<app>.json`) is for apps whose vendor publishes APKs on
     GitHub releases: `{ "package": "com.brave.browser", "repo": "brave/brave-browser",
     "tag": "v{version}", "assets": { "arm64-v8a": "BraveMonoarm64.apk" } }`. `tag` is the
     release tag of a version and `assets` maps an architecture to the asset name; an
     architecture without an asset is not served instead of falling back to another ABI.
     A published `<asset>.sha256` is verified before the APK is stored.
   - **APKMirror** `release_prefix` is the release slug without the version, e.g.
     `microsoft-swiftkey-ai-keyboard` for `…-9-13-13-5-release`. Set
     `"match_version_code": true` when the app has many same-version builds (e.g.
     Instagram) to pick the build whose version code the patches list.

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

_The "Available builds" table above is generated: after changing `patch-config.json` or
publishing a build, run `docker-compose run --rm --no-deps --entrypoint python builder scripts/generate_readme_table.py`
(add `--check` to only verify) and commit the result._

The local runner (see below) builds daily at 06:00 UTC. Successful builds replace
the `latest` release; the run fails if any entry could not be built.
The release only keeps the newest build of each app: after an upload, older
builds of the same app and source are removed from it (`scripts/prune_release_assets.py`;
run it with `--dry-run` to preview). Local copies in `apks/patched/` are never deleted.

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
