from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path("src/main/resources/assets/realityengineai/textures")
(ROOT / "items").mkdir(parents=True, exist_ok=True)
(ROOT / "blocks").mkdir(parents=True, exist_ok=True)
(ROOT / "entity").mkdir(parents=True, exist_ok=True)

def save_icon(name, painter):
    image = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    painter(draw, image)
    image.save(ROOT / name)

def artifact(draw, image):
    draw.polygon([(8, 0), (12, 4), (15, 8), (11, 12), (8, 15), (4, 12), (0, 8), (4, 4)], fill=(24, 171, 208, 255))
    draw.polygon([(8, 2), (10, 5), (13, 8), (9, 10), (8, 13), (6, 10), (3, 8), (6, 5)], fill=(113, 239, 255, 255))
    draw.rectangle((7, 5, 8, 9), fill=(245, 255, 255, 255))
    draw.point((4, 3), fill=(230, 255, 255, 255))
    draw.point((12, 12), fill=(230, 255, 255, 255))

def sword(draw, image):
    draw.line((3, 13, 12, 2), fill=(48, 57, 81, 255), width=4)
    draw.line((4, 11, 12, 2), fill=(95, 229, 250, 255), width=3)
    draw.line((5, 10, 12, 2), fill=(222, 255, 255, 255), width=1)
    draw.line((2, 12, 6, 15), fill=(170, 91, 45, 255), width=3)
    draw.point((13, 1), fill=(255, 255, 255, 255))

def pickaxe(draw, image):
    draw.line((3, 12, 12, 3), fill=(53, 59, 83, 255), width=3)
    draw.line((3, 12, 12, 3), fill=(152, 241, 255, 255), width=1)
    draw.line((2, 5, 5, 2), fill=(37, 128, 168, 255), width=4)
    draw.line((5, 2, 12, 2), fill=(37, 128, 168, 255), width=4)
    draw.point((13, 2), fill=(225, 255, 255, 255))

def food(draw, image):
    draw.rounded_rectangle((2, 4, 13, 12), radius=2, fill=(153, 84, 38, 255))
    draw.rectangle((3, 5, 12, 10), fill=(217, 161, 78, 255))
    for point in [(5, 6), (9, 5), (7, 9), (11, 8)]:
        draw.point(point, fill=(255, 226, 140, 255))
    draw.line((3, 13, 12, 13), fill=(100, 54, 32, 255), width=1)

def base_block(draw, image):
    for y in range(16):
        for x in range(16):
            shade = 25 + ((x * 13 + y * 7) % 30)
            draw.point((x, y), fill=(shade, shade + 32, shade + 62, 255))
    draw.rectangle((1, 1, 14, 14), outline=(57, 204, 238, 255), width=1)
    draw.line((2, 5, 13, 5), fill=(47, 111, 153, 255), width=1)
    draw.line((2, 10, 13, 10), fill=(47, 111, 153, 255), width=1)
    draw.point((8, 8), fill=(155, 246, 255, 255))

def crystal(draw, image):
    base_block(draw, image)
    draw.polygon([(7, 1), (11, 6), (9, 13), (6, 10), (5, 5)], fill=(128, 88, 239, 255))
    draw.polygon([(7, 1), (8, 7), (5, 5)], fill=(225, 209, 255, 255))
    draw.polygon([(11, 6), (13, 9), (9, 13), (8, 7)], fill=(71, 219, 248, 255))

def staff(draw, image):
    draw.line((8, 2, 6, 14), fill=(75, 49, 35, 255), width=3)
    draw.polygon([(5, 0), (8, 1), (11, 0), (12, 3), (8, 6), (4, 3)], fill=(92, 67, 205, 255))
    draw.polygon([(7, 1), (8, 2), (9, 1), (8, 4)], fill=(219, 244, 255, 255))

def amulet(draw, image):
    draw.arc((3, 0, 12, 9), 185, 355, fill=(188, 205, 225, 255), width=2)
    draw.polygon([(8, 5), (13, 9), (10, 14), (6, 14), (3, 9)], fill=(33, 85, 134, 255))
    draw.polygon([(8, 6), (10, 9), (8, 12), (6, 9)], fill=(95, 236, 255, 255))
    draw.point((8, 9), fill=(255, 255, 255, 255))

def dagger(draw, image):
    draw.polygon([(11, 0), (14, 3), (7, 10), (5, 7)], fill=(64, 99, 131, 255))
    draw.line((10, 2, 6, 8), fill=(222, 249, 255, 255), width=1)
    draw.line((3, 8, 8, 13), fill=(176, 92, 49, 255), width=3)
    draw.line((2, 10, 6, 6), fill=(204, 210, 221, 255), width=2)

def tech_block(draw, image):
    for y in range(16):
        for x in range(16):
            shade = 25 + ((x * 13 + y * 7) % 30)
            draw.point((x, y), fill=(shade, shade + 32, shade + 62, 255))
    draw.rectangle((1, 1, 14, 14), outline=(57, 204, 238, 255), width=1)
    draw.rectangle((3, 3, 12, 12), outline=(82, 235, 255, 255), width=1)
    for y in (5, 8, 11):
        draw.line((5, y, 10, y), fill=(190, 255, 253, 255), width=1)
    draw.point((8, 8), fill=(255, 255, 255, 255))

def metal_block(draw, image):
    for y in range(16):
        for x in range(16):
            shade = 88 + ((x * 17 + y * 9) % 46)
            draw.point((x, y), fill=(shade, shade + 5, min(255, shade + 15), 255))
    draw.rectangle((1, 1, 14, 14), outline=(188, 202, 220, 255), width=1)
    for y in (4, 11):
        draw.line((2, y, 13, y), fill=(64, 81, 103, 255), width=1)
    for point in ((3, 3), (12, 3), (3, 12), (12, 12)):
        draw.point(point, fill=(232, 238, 249, 255))

def corrupted_block(draw, image):
    for y in range(16):
        for x in range(16):
            color = (59, 26, 87, 255) if (x * 3 + y * 5) % 7 < 3 else (30, 25, 42, 255)
            draw.point((x, y), fill=color)
    draw.line((2, 2, 6, 6, 4, 10, 8, 14), fill=(180, 70, 255, 255), width=2)
    draw.line((13, 1, 10, 5, 13, 8, 9, 12), fill=(95, 231, 255, 255), width=1)
    draw.point((8, 7), fill=(245, 215, 255, 255))

save_icon("items/reality_artifact.png", artifact)
save_icon("items/reality_sword.png", sword)
save_icon("items/reality_pickaxe.png", pickaxe)
save_icon("items/reality_food.png", food)
save_icon("items/reality_staff.png", staff)
save_icon("items/reality_amulet.png", amulet)
save_icon("items/reality_dagger.png", dagger)
save_icon("blocks/reality_block.png", base_block)
save_icon("blocks/reality_crystal.png", crystal)
save_icon("blocks/reality_tech.png", tech_block)
save_icon("blocks/reality_metal.png", metal_block)
save_icon("blocks/reality_corrupted.png", corrupted_block)

skin = Image.new("RGBA", (64, 64), (19, 35, 52, 255))
d = ImageDraw.Draw(skin)

def rect(box, color):
    d.rectangle(box, fill=color)

dark = (19, 35, 52, 255)
blue = (36, 118, 157, 255)
light = (95, 226, 244, 255)
metal = (88, 112, 142, 255)
white = (224, 250, 255, 255)
violet = (103, 74, 202, 255)
rect((0, 0, 7, 7), blue)
rect((8, 0, 15, 7), blue)
rect((0, 8, 7, 15), blue)
rect((8, 8, 15, 15), dark)
rect((8, 8, 15, 9), light)
rect((9, 11, 10, 12), white)
rect((13, 11, 14, 12), white)
rect((10, 13, 13, 13), violet)
rect((16, 8, 23, 15), blue)
rect((24, 8, 31, 15), blue)
rect((8, 16, 15, 23), metal)
rect((16, 16, 23, 23), blue)
rect((24, 16, 31, 23), blue)
rect((32, 8, 39, 15), blue)
rect((40, 8, 47, 15), blue)
rect((20, 20, 27, 31), dark)
rect((21, 21, 26, 30), blue)
rect((23, 21, 24, 29), light)
rect((20, 32, 27, 43), metal)
rect((28, 20, 35, 31), blue)
rect((16, 20, 19, 31), dark)
rect((28, 32, 35, 43), blue)
rect((44, 20, 47, 31), dark)
rect((44, 20, 45, 30), blue)
rect((36, 20, 39, 31), metal)
rect((40, 20, 43, 31), blue)
rect((48, 20, 51, 31), dark)
rect((52, 20, 55, 31), blue)
rect((44, 32, 47, 43), metal)
rect((36, 32, 39, 43), blue)
rect((4, 20, 7, 31), dark)
rect((4, 20, 5, 30), violet)
rect((0, 20, 3, 31), metal)
rect((8, 20, 11, 31), blue)
rect((12, 20, 15, 31), dark)
rect((16, 52, 19, 63), blue)
rect((20, 52, 23, 63), metal)
rect((0, 52, 3, 63), dark)
rect((4, 52, 7, 63), violet)
rect((8, 52, 11, 63), blue)
rect((12, 52, 15, 63), dark)
for x in (20, 22, 24, 26):
    d.point((x, 23), fill=light)
for y in (22, 25, 28):
    d.point((45, y), fill=light)
skin.save(ROOT / "entity" / "reality_creature.png")

def recolor_skin(source, path, dark_color, base_color, accent_color, glow_color):
    target = Image.new("RGBA", source.size, dark_color)
    source_pixels = source.load()
    target_pixels = target.load()
    for y in range(source.height):
        for x in range(source.width):
            r, g, b, a = source_pixels[x, y]
            brightness = (r + g + b) / 3
            if a == 0:
                target_pixels[x, y] = (0, 0, 0, 0)
            elif brightness < 55:
                target_pixels[x, y] = dark_color
            elif brightness < 105:
                target_pixels[x, y] = base_color
            elif brightness < 175:
                target_pixels[x, y] = accent_color
            else:
                target_pixels[x, y] = glow_color
    target.save(path)

recolor_skin(skin, ROOT / "entity" / "reality_dragon.png", (26, 15, 48, 255), (80, 42, 142, 255), (136, 81, 229, 255), (196, 247, 255, 255))
recolor_skin(skin, ROOT / "entity" / "reality_hostile.png", (28, 15, 24, 255), (112, 31, 46, 255), (214, 59, 83, 255), (255, 192, 98, 255))
recolor_skin(skin, ROOT / "entity" / "reality_robot.png", (20, 31, 43, 255), (67, 88, 111, 255), (61, 184, 204, 255), (223, 250, 255, 255))
print("Generated 7 item sprites, 5 block textures and 4 entity skins.")
