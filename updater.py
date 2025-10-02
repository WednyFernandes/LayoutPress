import os
import sys
import time
import shutil
import subprocess

"""
Simple updater helper script.
Usage: python updater.py <target_path> <new_file_path>
It will wait for the target to be writable, replace it with the new file and relaunch.
"""

def replace_and_restart(target_path, new_path, retries=60, wait=0.5):
    for i in range(retries):
        try:
            # make a backup
            bak = target_path + ".bak"
            if os.path.exists(bak):
                try:
                    os.remove(bak)
                except Exception:
                    pass
            if os.path.exists(target_path):
                try:
                    os.replace(target_path, bak)
                except Exception:
                    # file may be locked
                    time.sleep(wait)
                    continue
            # move new file into place
            os.replace(new_path, target_path)
            # remove backup
            if os.path.exists(bak):
                try:
                    os.remove(bak)
                except Exception:
                    pass
            return True
        except Exception:
            time.sleep(wait)
    return False


def main():
    if len(sys.argv) < 3:
        print("Usage: updater.py <target_path> <new_file_path>")
        return 2
    target = sys.argv[1]
    newf = sys.argv[2]

    # wait until target is not locked
    for _ in range(120):
        if not os.path.exists(target) or os.access(target, os.W_OK):
            break
        time.sleep(0.5)

    ok = replace_and_restart(target, newf)
    if not ok:
        print("Update failed")
        return 1

    # relaunch
    try:
        subprocess.Popen([target], close_fds=True)
    except Exception:
        pass
    return 0

if __name__ == '__main__':
    sys.exit(main())
