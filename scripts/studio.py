"""Matte turntable of a nanoparticle about [001], for compose.py.

blender -b -P studio.py -- <csv> <out> [frames]
<csv> needs x, y, z columns. Writes transparent PNG frames to <out>. Only
geometry is shown, with facets in lavender and edges and corners in blue.
"""
import csv
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree

SIZE = int(os.environ.get("STUDIO_SIZE", 640))
SAMPLES = int(os.environ.get("STUDIO_SAMPLES", 96))
RADIUS = 1.25
AZIMUTH, ELEVATION = math.radians(45.0), math.radians(18.0)


def linear(h):
    rgb = tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb)


LAVENDER, BLUE = linear("b4befe"), linear("89b4fa")


#==============================================================================#
# Scene, matte material, camera and lights                                     #
#==============================================================================#

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    sc.render.resolution_x = sc.render.resolution_y = SIZE
    sc.render.film_transparent = True
    sc.view_settings.view_transform = "Standard"
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    world = bpy.data.worlds.new("world")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.25
    sc.world = world
    return sc


def matte():
    """Rough, low-specular base in the object's colour, darkened by ambient
    occlusion as 0.42 + 0.55 AO so crevices read without going black."""
    mat = bpy.data.materials.new("matte")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.65
    bsdf.inputs["Specular IOR Level"].default_value = 0.15
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = 2.0
    shade = nt.nodes.new("ShaderNodeMath")
    shade.operation = "MULTIPLY_ADD"
    shade.inputs[1].default_value = 0.55
    shade.inputs[2].default_value = 0.42
    tint = nt.nodes.new("ShaderNodeMix")
    tint.data_type = "RGBA"
    tint.blend_type = "MULTIPLY"
    tint.inputs["Factor"].default_value = 1.0
    info = nt.nodes.new("ShaderNodeObjectInfo")
    nt.links.new(info.outputs["Color"], tint.inputs["A"])
    nt.links.new(ao.outputs["AO"], shade.inputs[0])
    nt.links.new(shade.outputs["Value"], tint.inputs["B"])
    nt.links.new(tint.outputs["Result"], bsdf.inputs["Base Color"])
    return mat


def camera(sc, ortho):
    ez = Vector((math.cos(AZIMUTH) * math.cos(ELEVATION),
                 math.sin(AZIMUTH) * math.cos(ELEVATION), math.sin(ELEVATION)))
    ex = Vector((0.0, 0.0, 1.0)).cross(ez).normalized()
    up = ez.cross(ex)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = ortho
    cam.data.clip_end = 1000.0
    cam.location = ez * 4 * ortho
    cam.rotation_euler = Matrix((ex, up, ez)).transposed().to_euler()
    sc.collection.objects.link(cam)
    sc.camera = cam
    for name, (a, b, c), power, size in (
        ("key", (-0.9, 1.0, 0.9), 2.4, 1.4),
        ("fill", (1.2, 0.0, 0.8), 0.8, 1.8),
        ("rim", (0.2, 0.8, -1.0), 2.2, 1.0),
        ("bounce", (0.0, -1.0, 0.7), 0.7, 2.0),
    ):
        pos = (ex * a + up * b + ez * c).normalized() * 2.5 * ortho
        light = bpy.data.lights.new(name, "AREA")
        light.shape = "DISK"
        light.size = size * ortho
        light.energy = power * ortho ** 2 * 40
        obj = bpy.data.objects.new(name, light)
        obj.location = pos
        obj.rotation_euler = (-pos).to_track_quat("-Z", "Y").to_euler()
        sc.collection.objects.link(obj)


#==============================================================================#
# Particle                                                                     #
#==============================================================================#

def read(path):
    rows = list(csv.DictReader(open(path)))
    pts = [Vector((float(r["x"]), float(r["y"]), float(r["z"]))) for r in rows]
    centre = sum(pts, Vector()) / len(pts)
    return [p - centre for p in pts]


def colours(pts, cutoff=4.0):
    """Counts the first two bcc shells, 14 in the bulk, 9 or 10 on facets and
    8 or fewer on edges and corners."""
    tree = KDTree(len(pts))
    for i, p in enumerate(pts):
        tree.insert(p, i)
    tree.balance()
    return [BLUE if len(tree.find_range(p, cutoff)) - 1 <= 8 else LAVENDER for p in pts]


def main(path, out, frames=36):
    """A cubic particle repeats every 90 degrees, so the loop is seamless."""
    pts = read(path)
    sc = reset()
    pivot = bpy.data.objects.new("pivot", None)
    sc.collection.objects.link(pivot)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=RADIUS)
    proto = bpy.context.active_object
    proto.data.materials.append(matte())
    bpy.ops.object.shade_smooth()
    for p, c in zip(pts, colours(pts)):
        o = proto.copy()
        o.location = p
        o.color = (*c, 1.0)
        o.parent = pivot
        sc.collection.objects.link(o)
    bpy.data.objects.remove(proto)
    camera(sc, 2.6 * max(p.length for p in pts))
    for f in range(frames):
        pivot.rotation_euler = (0.0, 0.0, 0.5 * math.pi * f / frames)
        sc.render.filepath = f"{out}/frame_{f:03d}.png"
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:]
    os.makedirs(argv[1], exist_ok=True)
    main(argv[0], argv[1], *map(int, argv[2:]))
