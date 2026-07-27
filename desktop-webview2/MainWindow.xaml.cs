using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Windows;
using Microsoft.Web.WebView2.Core;

namespace SocialMetrics.Desktop;

public partial class MainWindow : Window
{
    private readonly List<Process> _children = new();
    private readonly string _rootDir;
    private readonly string _dataDir;
    private readonly string _reportsDir;

    public MainWindow()
    {
        InitializeComponent();
        _rootDir = FindProjectRoot();
        _dataDir = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "MarketingAnalytics");
        _reportsDir = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
            "Marketing Analytics",
            "Reports");
        Directory.CreateDirectory(_dataDir);
        Directory.CreateDirectory(_reportsDir);
        Loaded += OnLoaded;
        Closed += OnClosed;
    }

    private async void OnLoaded(object sender, RoutedEventArgs e)
    {
        var webViewRuntimeDir = GetBundledWebView2RuntimeDir();
        StartBackend();
        StartFrontend();
        await WaitForAsync("http://127.0.0.1:3000", TimeSpan.FromSeconds(45));
        var webViewData = Path.Combine(_dataDir, "WebView2");
        Directory.CreateDirectory(webViewData);
        var environment = await CoreWebView2Environment.CreateAsync(
            browserExecutableFolder: webViewRuntimeDir,
            userDataFolder: webViewData);
        await Browser.EnsureCoreWebView2Async(environment);
        Browser.Source = new Uri("http://127.0.0.1:3000");
    }

    private static void EnsureWebView2Runtime()
    {
        try
        {
            var version = CoreWebView2Environment.GetAvailableBrowserVersionString();
            if (string.IsNullOrWhiteSpace(version))
            {
                throw new InvalidOperationException("Microsoft Edge WebView2 Runtime is not installed.");
            }
        }
        catch (Exception exception)
        {
            throw new InvalidOperationException(
                "Для запуска приложения нужен Microsoft Edge WebView2 Runtime. " +
                "Установите его один раз через Microsoft Edge WebView2 Runtime Installer.",
                exception);
        }
    }

    private string GetBundledWebView2RuntimeDir()
    {
        var runtimeRoot = Path.Combine(_rootDir, "runtime", "webview2");
        if (Directory.Exists(runtimeRoot))
        {
            var bundledRuntime = Directory
                .EnumerateDirectories(runtimeRoot)
                .FirstOrDefault(path => File.Exists(Path.Combine(path, "msedgewebview2.exe")));
            if (bundledRuntime != null)
            {
                return bundledRuntime;
            }
        }

        throw new DirectoryNotFoundException("Bundled WebView2 runtime was not found: " + runtimeRoot);
    }

    private void StartBackend()
    {
        var backendDir = Path.Combine(_rootDir, "backend");
        var backendExe = Path.Combine(_rootDir, "runtime", "backend", "MarketingAnalyticsBackend.exe");
        if (!File.Exists(backendExe))
        {
            throw new FileNotFoundException("Не найден встроенный backend runtime.", backendExe);
        }
        StartProcess(
            backendExe,
            string.Empty,
            backendDir,
            ("MPLCONFIGDIR", Path.Combine(_dataDir, ".matplotlib")),
            ("TRACKDRIVE_DATA_DIR", _dataDir),
            ("TRACKDRIVE_UPLOADS_DIR", Path.Combine(_dataDir, "uploads")),
            ("TRACKDRIVE_CHARTS_DIR", Path.Combine(_dataDir, "charts")),
            ("TRACKDRIVE_REPORTS_DIR", _reportsDir));
    }

    private void StartFrontend()
    {
        var frontendDir = Path.Combine(_rootDir, "frontend");
        var nodeExe = Path.Combine(_rootDir, "runtime", "node.exe");
        if (!File.Exists(nodeExe))
        {
            throw new FileNotFoundException("Не найден встроенный Node.js runtime.", nodeExe);
        }
        var packagedServer = Path.Combine(frontendDir, "server.js");
        if (File.Exists(packagedServer))
        {
            StartProcess(nodeExe, "server.js", frontendDir, ("PORT", "3000"));
            return;
        }

        var standalone = Path.Combine(frontendDir, ".next", "standalone", "server.js");
        if (File.Exists(standalone))
        {
            StartProcess(nodeExe, "server.js", Path.GetDirectoryName(standalone)!, ("PORT", "3000"));
            return;
        }
        throw new FileNotFoundException("Не найден собранный frontend.", packagedServer);
    }

    private void StartProcess(string fileName, string arguments, string workingDirectory, params (string Key, string Value)[] env)
    {
        var psi = new ProcessStartInfo(fileName, arguments)
        {
            WorkingDirectory = workingDirectory,
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
        };
        foreach (var (key, value) in env)
        {
            psi.Environment[key] = value;
        }

        var process = Process.Start(psi);
        if (process != null)
        {
            _children.Add(process);
        }
    }

    private static async Task WaitForAsync(string url, TimeSpan timeout)
    {
        using var http = new HttpClient();
        var stopAt = DateTime.UtcNow + timeout;
        while (DateTime.UtcNow < stopAt)
        {
            try
            {
                using var response = await http.GetAsync(url);
                if ((int)response.StatusCode < 500) return;
            }
            catch
            {
                await Task.Delay(700);
            }
        }
    }

    private string FindProjectRoot()
    {
        var dir = AppContext.BaseDirectory;
        for (var i = 0; i < 8; i++)
        {
            if (Directory.Exists(Path.Combine(dir, "frontend")) && Directory.Exists(Path.Combine(dir, "backend")))
            {
                return dir;
            }
            dir = Path.GetFullPath(Path.Combine(dir, ".."));
        }
        return Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", ".."));
    }

    private void OnClosed(object? sender, EventArgs e)
    {
        foreach (var child in _children)
        {
            try
            {
                if (!child.HasExited)
                {
                    child.Kill(entireProcessTree: true);
                }
            }
            catch
            {
                // Best-effort cleanup on app exit.
            }
        }
    }
}
