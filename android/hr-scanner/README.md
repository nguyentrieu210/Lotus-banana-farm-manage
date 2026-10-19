# Lotus HR Android scanner (testing build)

Native Android shell for https://lotus.gpcds.site/hr-mobile. Login once in this standalone app.
The WebView never loads external hosts and the JS bridge is injected only on the allowlisted HTTPS origin.
Native scanner: CameraX back camera + ML Kit bundled barcode model, scan QR only; auto-zoom, torch.
Native result returns into the current form through a JavaScript event; it is not stored, shared, or put into URLs.

Build on GitHub Actions: HR Android APK workflow, download its artifact. Debug APK for internal testing only; release needs enterprise signing/versioning/device acceptance.
The original PWA still uses its browser QR scanner.
