import os
import sys
import subprocess
import re
import glob


class enter_dir(object):
    # Taken from https://pythonadventures.wordpress.com/
    #    2013/12/15/chdir-a-context-manager-for-switching-working-directories/
    def __init__(self, path):
        self.old_dir = os.getcwd()
        self.new_dir = path

    def __enter__(self):
        os.chdir(self.new_dir)

    def __exit__(self, *args):
        os.chdir(self.old_dir)


def _run_setup_py():
    python = sys.executable
    subprocess.call([python, "setup.py", "windows", "--sanitize-version"])


def _replace_pythonw():
    launch_script = os.path.join("windows", "content", "app", "eyegrade-script.pyw")
    with open(launch_script) as f:
        lines = [line for line in f]
    lines[0] = re.sub(r"python\.exe", "pythonw.exe", lines[0], count=1)
    with open(launch_script, mode="w") as f:
        for line in lines:
            f.write(line)


def _run_candle(wix_dir):
    with enter_dir("windows"):
        wxs_file = "briefcase.wxs"
        candle_exe = os.path.join(wix_dir, "bin", "candle.exe")
        subprocess.call([candle_exe, wxs_file])


def _run_light(wix_dir):
    with enter_dir("windows"):
        wixobj_file = "briefcase.wixobj"
        light_exe = os.path.join(wix_dir, "bin", "light.exe")
        subprocess.call([light_exe, "-ext", "WixUIExtension", wixobj_file])


def _rename_installer(version):
    with enter_dir("windows"):
        os.rename("briefcase.msi", "eyegrade-{}.msi".format(version))


def _locate_wix():
    candidates = glob.glob(
        os.path.join("C:\\", "Program Files (x86)", "WiX Toolset v3.*")
    )
    if len(candidates) == 0:
        raise ValueError("WiX toolset 3.x needs to be installed")
    else:
        return candidates[0]


def _eyegrade_version():
    with open("setup.py") as f:
        data = f.read()
    match = re.search(r'version=(("([^"]*)")|(\'([^\']*)\'))', data)
    groups = match.groups()
    if groups[2] is not None:
        return groups[2]
    else:
        return groups[4]


def main():
    eyegrade_dir = os.path.abspath(
        os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..")
    )
    with enter_dir(eyegrade_dir):
        _run_setup_py()
        _replace_pythonw()
        wix_dir = _locate_wix()
        _run_candle(wix_dir)
        _run_light(wix_dir)
        _rename_installer(_eyegrade_version())


if __name__ == "__main__":
    main()
