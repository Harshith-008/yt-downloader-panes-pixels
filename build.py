import PyInstaller.__main__
import os
import shutil

def run_build():
    
    dist_dir = os.path.join(os.getcwd(), 'dist')
    build_dir = os.path.join(os.getcwd(), 'build')
    
    # 1. Clean previous builds
    for folder in [dist_dir, build_dir]:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
            except Exception as e:
                print(f"Warning: could not clean {folder}: {e}")
                
    # 2. Build the main application (onedir mode)
    print("\n--- BUILDING MAIN APPLICATION ---")
    app_args = [
        'app_webview.py',
        '--name=YT Downloader by Panes & Pixels',
        '--onedir',
        '--noconsole',
        '--icon=icon.ico',
        f'--add-data=dist_web{os.pathsep}dist_web',
        f'--add-data=icon.ico{os.pathsep}.',
        '--clean',
    ]
    PyInstaller.__main__.run(app_args)
    
    # 3. Build the uninstaller (onefile mode)
    print("\n--- BUILDING UNINSTALLER ---")
    uninstaller_args = [
        'uninstaller.py',
        '--name=uninstall',
        '--onefile',
        '--noconsole',
        '--icon=icon.ico',
        '--clean',
    ]
    PyInstaller.__main__.run(uninstaller_args)
    
    # 4. Copy the uninstaller to the main application's dist folder
    app_dist_dir = os.path.join(dist_dir, 'YT Downloader by Panes & Pixels')
    uninstall_exe = os.path.join(dist_dir, 'uninstall.exe')
    target_uninstall = os.path.join(app_dist_dir, 'uninstall.exe')
    
    print(f"\nMoving uninstaller to application folder: {target_uninstall}")
    if os.path.exists(uninstall_exe) and os.path.exists(app_dist_dir):
        shutil.move(uninstall_exe, target_uninstall)
        
    # Copy icon to the main application folder just in case
    shutil.copy('icon.ico', os.path.join(app_dist_dir, 'icon.ico'))
    
    # 5. Zip the main application folder containing the uninstaller
    print("\nZipping application folder...")
    zip_path = os.path.join(dist_dir, 'YT Downloader by Panes & Pixels')
    shutil.make_archive(zip_path, 'zip', dist_dir, 'YT Downloader by Panes & Pixels')
    print(f"Zip archive created: {zip_path}.zip")
    
    # 6. Build the installer (onefile mode, embedding the zip file)
    print("\n--- BUILDING INSTALLER ---")
    zip_file_relative = os.path.join('dist', 'YT Downloader by Panes & Pixels.zip')
    installer_args = [
        'installer.py',
        '--name=YT_Downloader_Setup',
        '--onefile',
        '--noconsole',
        '--icon=icon.ico',
        f'--add-data={zip_file_relative}{os.pathsep}.',
        f'--add-data=icon.ico{os.pathsep}.',
        '--clean',
    ]
    PyInstaller.__main__.run(installer_args)
    
    print("\n=== BUILD PROCESS COMPLETE ===")
    print(f"Main Setup Executable: {os.path.join(dist_dir, 'YT_Downloader_Setup.exe')}")

if __name__ == '__main__':
    run_build()
