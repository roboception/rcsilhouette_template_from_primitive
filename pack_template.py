#!/usr/bin/env python3

"""
This tool packs a folder into an .rcsmt SilhouetteMatch template. Useful if you
edited the template yourself and want to pack it again.
"""

import os
import sys
import shutil
import tarfile
import argparse
import tempfile

optional_files = ["model.glb", "collision_model.ply", "grasps.json"]
required_files = ["template.png", "meta.yaml", "gradients.png"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", help="The folder to be packed.")
    parser.add_argument(
        "--out-file",
        help="Path to the desired .rcsmt template. Defaults to current working dir.",
    )
    args = parser.parse_args()

    if not args.out_file:
        args.out_file = args.folder + ".rcsmt"

    if not os.path.isdir(args.folder):
        print(
            f"Source folder '{args.folder}' does not exist."
            " Please check if path correct."
        )
        sys.exit(1)

    if os.path.isfile(args.out_file):
        print(
            f"Target template '{os.path.abspath(args.out_file)}' already exists."
            " Please remove or rename."
        )
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmpfolder:
        all_files = required_files + optional_files
        tmparchive = os.path.join(tmpfolder, "archive.tar.gz")

        with tarfile.open(tmparchive, "w") as archive:
            for file in all_files:
                filepath = os.path.join(args.folder, file)
                
                if os.path.isfile(filepath):
                    archive.add(filepath, recursive=False, arcname=file)
                elif file in required_files:
                    print(
                        f"Required file '{filepath}' missing from template folder. Can't continue."
                    )
                    sys.exit(1)

        shutil.move(tmparchive, args.out_file)


if __name__ == "__main__":
    main()
