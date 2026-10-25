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

def computer_front(draw, image):
    draw.rectangle((0, 0, 15, 15), fill=(36, 48, 63, 255))
    draw.rectangle((1, 1, 14, 13), fill=(20, 31, 43, 255))
    draw.rectangle((2, 2, 13, 10), fill=(14, 65, 86, 255))
    draw.rectangle((3, 3, 12, 9), fill=(16, 91, 111, 255))
    draw.line((4, 5, 8, 5), fill=(100, 239, 255, 255), width=1)
    draw.line((4, 7, 11, 7), fill=(62, 194, 235, 255), width=1)
    draw.point((10, 5), fill=(255, 215, 108, 255))
    draw.rectangle((5, 11, 10, 12), fill=(97, 113, 133, 255))
    draw.point((12, 12), fill=(76, 235, 156, 255))

def computer_side(draw, image):
    draw.rectangle((0, 0, 15, 15), fill=(31, 43, 57, 255))
    draw.rectangle((2, 1, 13, 14), fill=(49, 67, 86, 255))
    draw.line((3, 3, 12, 3), fill=(88, 215, 236, 255), width=1)
    draw.rectangle((4, 5, 11, 10), fill=(24, 34, 46, 255))
    draw.point((6, 7), fill=(73, 218, 241, 255))
    draw.point((8, 8), fill=(73, 218, 241, 255))
    draw.line((3, 12, 12, 12), fill=(105, 130, 148, 255), width=1)

def computer_top(draw, image):
    draw.rectangle((0, 0, 15, 15), fill=(35, 47, 61, 255))
    draw.rectangle((2, 2, 13, 13), fill=(54, 76, 95, 255))
    draw.rectangle((4, 4, 11, 11), fill=(19, 70, 90, 255))
    draw.line((5, 5, 10, 10), fill=(95, 230, 248, 255), width=1)
    draw.line((10, 5, 5, 10), fill=(95, 230, 248, 255), width=1)

save_icon("items/reality_artifact.png", artifact)
save_icon("items/reality_sword.png", sword)
save_icon("items/reality_pickaxe.png", pickaxe)
save_icon("items/reality_food.png", food)
save_icon("blocks/reality_block.png", base_block)
save_icon("blocks/reality_crystal.png", crystal)
save_icon("blocks/computer_front.png", computer_front)
save_icon("blocks/computer_side.png", computer_side)
save_icon("blocks/computer_top.png", computer_top)

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
print("Generated nine custom 16x16 sprites and one 64x64 entity skin.")
