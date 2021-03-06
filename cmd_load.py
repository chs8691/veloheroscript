import glob
from os import path

import config
from load import create_load, read_load
from strava import load_strava_activity
from utility import log, exit_on_error


def print_info():

    dir = config.get_download_dir()

    if dir is None:
        print("No load directory configured. To set,  use 'heroscript config --load_directory PATH'.")
        return

    if not path.exists(dir):
        exit_on_error("Not a valid directory: '{}'. "
                      "To change,  use 'heroscript config --load_directory PATH'.".format(dir))

    types = ('*.TCX', '*.tcx')
    files_grabbed = []

    for files in types:
        files_grabbed.extend(glob.glob(path.join(dir, files)))

    files_grabbed.sort()

    if len(files_grabbed) == 0:
        print("No track file found in {}".format(dir))
        return

    load = read_load()

    print(f"Found {len(files_grabbed)} track file(s) in '{dir}':")
    for file in files_grabbed:
        if load and file == load.file_name:
            status = "*"
        else:
            status = " "

        print(f"  {status} {path.basename(file)}")


def process_load(args):
    log("process_load", "start")

    if args.info:
        print_info()
        return

    if args.file:
        create_load(args.file)

    elif args.directory:
        create_load(get_next_track_file(args.directory))

    else:
        dir = config.get_download_dir()
        if dir is None:
            exit_on_error("No load directory configured. Use 'heroscript config --load_directory PATH' or use "
                          "an optional argument '--file FILE' or '--directory DIRECTORY'.")
        else:
            create_load(get_next_track_file(dir))

    if args.strava:
        load_strava_activity()

    log("process_load", "end")


def get_next_track_file(directory):
    """
    Get apth of the name track file
    :param directory: String with directorz=y
    :return: String with path or None
    """
    if not path.exists(directory):
        exit_on_error("Not a valid directory: '{}'".format(directory))

    types = ('*.TCX', '*.tcx')
    files_grabbed = []

    for files in types:
        files_grabbed.extend(glob.glob(path.join(directory, files)))

    files_grabbed.sort()
    log("files_grabbed", files_grabbed)

    if len(files_grabbed) == 0:
        exit_on_error("No track file found in {}".format(directory))
    else:
        return files_grabbed[0]
