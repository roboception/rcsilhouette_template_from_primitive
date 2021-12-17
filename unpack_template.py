#!/usr/bin/env python3

"""
This tool unpacks an .rcsmt SilhouetteMatch template into a folder. Useful if you
want to edit the template directly.
"""

import os
import sys
import tarfile
import argparse


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("template", help="Path to the template to be unpacked.")
    parser.add_argument(
        "--out-folder",
        help="Path to desired output folder, will create it.",
    )
    args = parser.parse_args()

    if not os.path.exists(args.template):
        print(f"Template '{args.template}' does not exist. Please check path.")
        sys.exit(1)
    
    if not args.out_folder:
        args.out_folder, _ = os.path.splitext(args.template)
    
    if os.path.isdir(args.out_folder):
        print(f"Output folder '{args.out_folder}' exists already. Please rename or remove.")
        sys.exit(1)
    
    os.makedirs(args.out_folder)
    with tarfile.open(args.template, "r") as fh:
        fh.extractall(args.out_folder)


if __name__ == "__main__":
    main()
