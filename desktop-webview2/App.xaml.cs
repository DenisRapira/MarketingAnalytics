using System.IO;
using System.Windows;
using System.Windows.Threading;

namespace SocialMetrics.Desktop;

public partial class App : Application
{
    protected override void OnStartup(StartupEventArgs e)
    {
        DispatcherUnhandledException += OnDispatcherUnhandledException;
        try
        {
            base.OnStartup(e);
        }
        catch (Exception ex)
        {
            ShowStartupError(ex);
            Shutdown(1);
        }
    }

    private void OnDispatcherUnhandledException(object sender, DispatcherUnhandledExceptionEventArgs e)
    {
        e.Handled = true;
        ShowStartupError(e.Exception);
        Shutdown(1);
    }

    private static void ShowStartupError(Exception error)
    {
        var dataDir = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "MarketingAnalytics");
        Directory.CreateDirectory(dataDir);
        var logPath = Path.Combine(dataDir, "startup-error.log");
        File.WriteAllText(logPath, $"{DateTime.Now:O}{Environment.NewLine}{error}");
        MessageBox.Show(
            $"Не удалось запустить Marketing Analytics.\n\nПодробности сохранены в:\n{logPath}",
            "Ошибка запуска",
            MessageBoxButton.OK,
            MessageBoxImage.Error);
    }
}
