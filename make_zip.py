import shutil
import os

def make_zip():
    dist_dir = os.path.abspath("dist")
    suite_dir = os.path.join(dist_dir, "ITMQ-GD-Suite")
    zip_path = os.path.join(dist_dir, "ITMQ-GD") # shutil adds .zip

    # 1. Create Updater ZIP
    updater_dist = os.path.join(dist_dir, "ITMQ-Updater")
    updater_zip = os.path.join(dist_dir, "ITMQ-Updater")
    if os.path.exists(updater_dist):
        print(f"Zipping Updater to {updater_zip}.zip...")
        shutil.make_archive(updater_zip, 'zip', root_dir=updater_dist)
        
    # 2. Include Installer Script in Suite
    installer_src = os.path.join("build_config", "installer.iss")
    if os.path.exists(installer_src):
        shutil.copy(installer_src, suite_dir)
        print(f"Included {installer_src}")

    # 3. Create Main Suite ZIP
    print(f"Zipping Suite to {zip_path}.zip...")
    shutil.make_archive(zip_path, 'zip', root_dir=dist_dir, base_dir="ITMQ-GD-Suite")
    print("Done!")

if __name__ == "__main__":
    make_zip()
