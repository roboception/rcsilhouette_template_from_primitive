#!/usr/bin/env python3

# Roboception GmbH
# Munich, Germany
# www.roboception.com
#
# Copyright (c) 2019 Roboception GmbH
# All rights reserved
#
# Author: Raphael Schaller

"""
Generates templates for rc_reason SilhouetteMatch from primitives. Writes to .rcsmt
file by default, can also write to output folder.
"""

import abc
import math
import os
import shutil
import tarfile
import uuid
import tempfile
from datetime import datetime
from typing import List, Tuple
from functools import reduce
import argparse

import yaml
from PIL import Image, ImageDraw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("object_id", help="ID of the object")
    parser.add_argument(
        "--object-height", type=float, help="Height of the object (meters), measured from the base plane", required=True
    )
    parser.add_argument(
        "--circle",
        type=float,
        action="append",
        help="Draw circle with this diameter (in meters, e.g. --circle 0.1)",
    )
    parser.add_argument(
        "--rect",
        type=str,
        action="append",
        help="Draw a rectangle with this width and height (in meters, e.g. --rect 0.4,0.3)",
    )
    hex_group = parser.add_argument_group()
    hex_group.add_argument(
        "--hex-diameter",
        type=str,
        action="append",
        help="Draw a hexagon with this diameter (in meters, corner to corner)."
        " Pointy-orientation hex by default, can be changed by specifying a rotation in degrees (e.g. --hex-diameter 0.1,30)",
    )
    hex_group.add_argument(
        "--hex-parallel-sides",
        type=str,
        action="append",
        help="Draw a hexagon with this size (in meters, distance between parallel sides)."
        " Pointy-orientation hex by default, can be changed by specifying a rotation in degrees (e.g. --hex-parallel-sides 0.1,30)",
    )
    parser.add_argument(
        "--write-folder",
        help="Write folder instead of .rcsmt template file.",
        action="store_true",
    )
    parser.add_argument("--origin", choices=["center", "corner"], default="center")
    parser.add_argument(
        "--focal-length", type=float, default=1100, help="Virtual focal length"
    )
    parser.add_argument(
        "--plane-distance", type=float, default=0.5, help="Virtual plane distance"
    )
    args = parser.parse_args()

    object_id = replace_invalid_characters(args.object_id)

    circles = [Circle(diameter) for diameter in (args.circle or [])]
    rects = [Rectangle(*map(float, rect.split(","))) for rect in (args.rect or [])]
    hexes = [("diameter", hexi) for hexi in (args.hex_diameter or [])]
    hexes += [("parallel_sides", hexi) for hexi in (args.hex_parallel_sides or [])]

    hexagons = []
    for size_type, hex_entry in hexes:
        if "," in hex_entry:
            size, angle_deg = hex_entry.split(",")
        else:
            size = hex_entry
            angle_deg = 0

        size = float(size)
        angle_deg = float(angle_deg)
        diameter = size if size_type == "diameter" else 2 / math.sqrt(3) * size

        hexagons.append(Hexagon(diameter, angle_deg))

    generate_template(
        object_id,
        circles + rects + hexagons,
        args.focal_length,
        args.plane_distance,
        args.object_height,
        args.origin,
        args.write_folder,
    )


class Shape(abc.ABC):
    @abc.abstractmethod
    def draw(
        self,
        edges: Image,
        edge_orientations: Image,
        pos: Tuple[float, float],
        focal_length: float,
        distance: float,
    ) -> None:
        pass

    @abc.abstractmethod
    def get_bb(self) -> Tuple[float, float]:
        pass

    @property
    @abc.abstractmethod
    def rotational_symmetry(self) -> int:
        pass


class Circle(Shape):
    def __init__(self, diameter: float):
        self.diameter = diameter

    def draw(
        self,
        edges: Image,
        edge_orientations: Image,
        pos: Tuple[float, float],
        focal_length: float,
        distance: float,
    ):
        diameter_pixels = self.diameter * focal_length / distance
        offset_x = pos[0] - 0.5 * diameter_pixels
        offset_y = pos[1] - 0.5 * diameter_pixels

        edges_draw = ImageDraw.ImageDraw(edges)
        edges_draw.ellipse(
            (
                offset_x,
                offset_y,
                diameter_pixels + offset_x,
                diameter_pixels + offset_y,
            ),
            outline=255,
            width=1,
        )

        for x in range(edges.size[0]):
            for y in range(edges.size[1]):
                v = edges.getpixel((x, y))
                if v == 255:
                    angle = math.atan2(y - pos[0], x - pos[1])
                    edge_orientations.putpixel(
                        (x, y), edge_orientation_val_for_angle(angle)
                    )

    def get_bb(self) -> Tuple[float, float]:
        return self.diameter, self.diameter

    @property
    def rotational_symmetry(self) -> int:
        return 360


class Hexagon(Shape):
    def __init__(self, corner_diameter: float, base_angle: float = 0):
        self.corner_diameter = corner_diameter
        self.base_angle = base_angle

    def draw(
        self,
        edges: Image,
        edge_orientations: Image,
        pos: Tuple[float, float],
        focal_length: float,
        distance: float,
    ):
        diameter_pixels = self.corner_diameter * focal_length / distance
        radius_pixels = diameter_pixels // 2

        edges_draw = ImageDraw.ImageDraw(edges)
        edge_orient_draw = ImageDraw.ImageDraw(edge_orientations)

        step_deg = 60
        prev_pt = None
        for angle_deg in range(0, 360 + step_deg, step_deg):
            angle_deg += self.base_angle

            pt = [
                pos[0] + radius_pixels * math.sin(rad(angle_deg)),
                pos[1] + radius_pixels * math.cos(rad(angle_deg)),
            ]

            if prev_pt:
                edges_draw.line((*prev_pt, *pt), fill=255)
                edge_angle_deg = angle_deg - step_deg / 2

                edge_orient_draw.line(
                    (*prev_pt, *pt),
                    fill=edge_orientation_val_for_angle(rad(90 - edge_angle_deg)),
                )

            prev_pt = pt

    def get_bb(self) -> Tuple[float, float]:
        return self.corner_diameter, self.corner_diameter

    @property
    def rotational_symmetry(self) -> int:
        return 6


class Rectangle(Shape):
    def __init__(self, width: float, height: float):
        self.width = width
        self.height = height

    def draw(
        self,
        edges: Image,
        edge_orientations: Image,
        pos: Tuple[float, float],
        focal_length: float,
        distance: float,
    ):
        width_pixels = self.width * focal_length / distance
        height_pixels = self.height * focal_length / distance
        offset_x = pos[0] - 0.5 * width_pixels
        offset_y = pos[1] - 0.5 * height_pixels

        edges_draw = ImageDraw.ImageDraw(edges)
        edge_orient_draw = ImageDraw.ImageDraw(edge_orientations)

        edges_draw.line(
            [(offset_x, offset_y), (offset_x, offset_y + height_pixels)],
            fill=255,
            width=1,
        )
        edge_orient_draw.line(
            [(offset_x, offset_y), (offset_x, offset_y + height_pixels)],
            fill=edge_orientation_val_for_angle(0),
            width=1,
        )

        edges_draw.line(
            [(offset_x, offset_y), (offset_x + width_pixels, offset_y)],
            fill=255,
            width=1,
        )
        edge_orient_draw.line(
            [(offset_x, offset_y), (offset_x + width_pixels, offset_y)],
            fill=edge_orientation_val_for_angle(0.5 * math.pi),
            width=1,
        )

        edges_draw.line(
            [
                (offset_x + width_pixels, offset_y),
                (offset_x + width_pixels, offset_y + height_pixels),
            ],
            fill=255,
            width=1,
        )
        edge_orient_draw.line(
            [
                (offset_x + width_pixels, offset_y),
                (offset_x + width_pixels, offset_y + height_pixels),
            ],
            fill=edge_orientation_val_for_angle(0),
            width=1,
        )

        edges_draw.line(
            [
                (offset_x, offset_y + height_pixels),
                (offset_x + width_pixels, offset_y + height_pixels),
            ],
            fill=255,
            width=1,
        )
        edge_orient_draw.line(
            [
                (offset_x, offset_y + height_pixels),
                (offset_x + width_pixels, offset_y + height_pixels),
            ],
            fill=edge_orientation_val_for_angle(0.5 * math.pi),
            width=1,
        )

    def get_bb(self) -> Tuple[float, float]:
        return self.width, self.height

    @property
    def rotational_symmetry(self) -> int:
        return 4 if abs(self.width - self.height) < 1e-6 else 2


def generate_template(
    out_filename: str,
    shapes: List[Shape],
    focal_length: float,
    plane_distance: float,
    object_height: float,
    origin: str,
    write_folder: bool,
):
    img, img_gradient, img_center, template_distance = render_shape(
        shapes,
        focal_length,
        plane_distance,
        object_height,
    )

    data = {
        "object-uuid": str(uuid.uuid4()),
        "date": datetime.now().isoformat(timespec="seconds"),
        "plane-distance": plane_distance,
        "object-height": object_height,
        "focal-length": focal_length,
        "rotational-symmetry": reduce(math.gcd, [shape.rotational_symmetry for shape in shapes]),
        "symmetry-center": dict(zip(["x", "y"], img_center)),
        "pose-offset": {
            "rotation": {"w": 1, "x": 0, "y": 0, "z": 0},
            "translation": {"x": 0, "y": 0, "z": 0},
        },
    }

    if origin == "corner":
        pass
    elif origin == "center":
        data["pose-offset"]["translation"]["x"] = (
            img_center[0] / focal_length * template_distance
        )
        data["pose-offset"]["translation"]["y"] = (
            img_center[1] / focal_length * template_distance
        )
    elif origin:
        raise Exception(f'Origin "{origin}" invalid')
    
    with tempfile.TemporaryDirectory() as folder:
        img_file = "template.png"
        gradients_file = "gradients.png"
        meta_file = "meta.yaml"
        img_path = os.path.join(folder, "template.png")
        gradients_path = os.path.join(folder, "gradients.png")
        meta_path = os.path.join(folder, "meta.yaml")

        img.save(img_path)
        img_gradient.save(gradients_path)
        with open(meta_path, "w") as outfile:
            yaml.safe_dump(data, outfile, default_flow_style=False)
        
        if write_folder:
            if os.path.exists(out_filename):
                print(f"The target folder '{out_filename}' exists already. Please delete or rename.")
                exit(1)
            shutil.copytree(folder, out_filename)
            return

        archive_name = out_filename + ".rcsmt"
        if os.path.isfile(archive_name):
            print(f"The target '{archive_name}' exists already. Please delete or rename.")
            exit(1)

        tar_tmp_file = os.path.join(folder, archive_name)
        with tarfile.open(tar_tmp_file, "w") as archive:
            archive.add(img_path, recursive=False, arcname=img_file)
            archive.add(gradients_path, recursive=False, arcname=gradients_file)
            archive.add(meta_path, recursive=False, arcname=meta_file)

        shutil.move(tar_tmp_file, archive_name)


def render_shape(
    shapes: List[Shape],
    focal_length: float,
    plane_distance: float,
    object_height: float,
):
    template_distance = plane_distance - object_height

    max_size = max(max(shape.get_bb()) for shape in shapes)
    max_size_pixels = max_size * focal_length / template_distance
    image_size = math.ceil(max_size_pixels)

    img = Image.new("L", (image_size, image_size), color=0)
    img_gradient = Image.new("L", (image_size, image_size), color=0)

    img_center = 0.5 * max_size_pixels, 0.5 * max_size_pixels

    for shape in shapes:
        shape.draw(img, img_gradient, img_center, focal_length, template_distance)

    return img, img_gradient, img_center, template_distance


def rad(deg):
    return deg / 180 * 3.1415


def replace_invalid_characters(s):
    r = ""
    for c in s:
        if (
            "a" <= c <= "z"
            or "A" <= c <= "Z"
            or "0" <= c <= "9"
            or c == "_"
            or c == "-"
        ):
            r += c
        else:
            r += "_"
    return r


def edge_orientation_val_for_angle(angle_rad: float):
    if angle_rad < 0.0:
        angle_rad = 2.0 * math.pi + angle_rad
    angle_rad = int(angle_rad / (2.0 * math.pi) * 255)
    return angle_rad


if __name__ == "__main__":
    main()
