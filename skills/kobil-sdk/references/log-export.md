# SDK log export — Android and iOS

## Evidence and scope

Reviewed native Getting Started logging models and a Flutter mobile export
implementation. These implementations archive existing files; they do not send
an ExportLogsEvent. Do not invent an export event or assume every release has
the same logging API. Inspect the supplied native/wrapper API first.

[Official logging documentation](https://developer.kobil.com/docs/mcsdk-docs/digitanium/development/export-logs/)
describes encrypted SDK logging, severity and storage locations. INFO is the
normal baseline; TRACE is for controlled debugging only, not production, and
may change timing. Revert temporary verbosity after reproducing an issue.

Status: Android export button runtime-tested with MC 188.1.2937039 on a
physical Pixel 8. An app update preserved its data; tapping export produced
a ZIP with 23 files and opened the Android share chooser. A private local copy
passed ZIP CRC validation (4,205,396 archive bytes). This proves archive creation
and chooser launch, not receiver access, current-reproduction coverage or
decryption. No new authentication operation was needed to export existing logs.
iOS/Flutter remain source-reviewed only. Receiver opening, cancellation and
post-share cleanup still require verification.

## Collection contract

1. Set up logging early enough to capture initialization. Retain the separate
   Warning/RuntimeError/FatalError listener with errorType, errorCode and
   errorDescription; a log archive does not replace event diagnostics.
2. Resolve the active SDK log path and any early-start logging path. Custom
   logging destinations take precedence over example folder names.
3. Reproduce the issue and record time, app/SDK versions, OS and request/result
   sequence in a small sanitized manifest. Do not add JWTs, PINs, passwords,
   activation codes or full event objects.
4. Snapshot only the selected log files into a unique temporary staging folder.
   Preserve their encrypted bytes and relative filenames. Avoid copying the
   app sandbox, databases or assets. Keep the output ZIP outside source folders.
5. Treat missing logs, failed copies and archive errors as failures. Inspect ZIP
   entries and sizes before reporting success; an existing ZIP or header-only
   log does not establish that the reproduction was captured. Use a documented
   flush/snapshot API if available; do not invent one or reset app data to flush.
6. Let the user save/share the validated ZIP. Keep it until the receiving share
   operation finishes, then clean up the export copy according to retention
   policy. Preserve source logs and existing activation/device state.

## Kotlin / Android

The reviewed wrapper exposes SynchronousEventHandler.logsPath. Prefer that
runtime value. Its LoggingModel also exposes Log.StartEncryption(path) for an
explicit destination; resolve the actual path configured by the app.

Without a runtime path, look for logs_mPower in externalFilesDir, filesDir and
cacheDir, in that order. The reviewed sample additionally collects stageOneLogs
from the same parent for pre-initialization diagnostics. Probe that directory
independently when Start fails before a normal SDK path exists. Never archive
the entire parent merely to include both folders.

Create the archive off the UI thread in an app-owned export/cache directory.
Share application/zip through FileProvider with a content URI, ACTION_SEND,
EXTRA_STREAM and FLAG_GRANT_READ_URI_PERMISSION. Configure a narrow provider
path covering the export directory, then launch the chooser on the UI thread.
Do not copy the sample's public-Downloads preference or assume its share intent
already grants the receiver access. An app-owned directory needs no broad
storage permission for this workflow.

Development fallback: use Device Explorer or adb with an explicit device serial.
Pull the resolved external location if accessible. For a debuggable app, run-as
can read its private path; it is not a release-build export mechanism. Write
binary output directly to a restricted local file, never the terminal/chat.

## Swift / iOS

The reviewed app uses KSMasterControllerFactory.getLogSink() to configure
severity. It exports Documents/logs_mPower using NSFileCoordinator with
reading option .forUploading, then moves the produced archive into a temporary
item-replacement directory. Resolve any release-specific/custom path first.

Handle directory lookup, coordination and move errors explicitly. Validate the
result before presenting UIActivityViewController on the main thread. Supply
an appropriate popover anchor on iPad and retain the temporary file until share
completion. An empty or nil result must produce a visible export failure.

Development fallback: download the development app container through Xcode's
Devices and Simulators and extract Documents/logs_mPower from its AppData.
Inspect the real container layout; do not rely on a singular Document typo.

## Flutter — mobile only

The inspected mobile implementation uses path_provider to locate storage,
archive to ZIP files and share_plus to share an XFile. On iOS it searches the
Documents directory; on Android it begins with app external storage.

For a new integration, prefer a plugin/native bridge returning the actual SDK
log location, including Android internal files/cache fallback and early-start
logs. A Dart temporary-directory fallback alone can miss the SDK logs.
Inspect the installed package versions before choosing exact sharing APIs.
Select regular files beneath explicit SDK log roots, not substring matches on
FileSystemEntity.toString(). Handle null directories, partial copies and empty
archives; perform large archive work away from the UI isolate. Android content
URI access and iPad share anchors still need platform verification.

## Export is not decryption

Keep the bundle encrypted. Decryption is a separate, optionally configured
support capability using matching SDK-version tooling; never bundle keys or
internal decryption services into the customer app/skill. Decrypted output stays
restricted locally; share only sanitized findings through authorized channels.

## Verification checklist

Record each checkpoint separately: logging enabled before Start; a known
reproduction present; regular nonempty files archived; ZIP readable; intended
receiver can open it; cancellation and empty/missing logs handled; temporary
files cleaned after completion. Verify these on each requested mobile target.
Do not mark the export runtime-verified after source review or a build alone.
