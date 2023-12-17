import platform

if platform.system() == "Windows":
    from colorama import just_fix_windows_console

    just_fix_windows_console()


__version__ = "0.1.0"
