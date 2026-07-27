# Marketing Analytics Desktop Host

Native WPF host for the local Marketing Analytics desktop application.

The packaged application starts the bundled analytics backend and frontend as child processes, renders the UI through a bundled Microsoft WebView2 Fixed Version runtime, and cleans up child processes when the window closes.

`MarketingAnalytics.exe` is built as a self-contained Windows x64 executable. End users do not need Python, Node.js, .NET, or WebView2 installed.

For a full desktop package, run `scripts\publish-desktop.ps1` from the repository root.
