"""
Recipe photo cropping (fork): the user frames the photo in the browser, the server cuts it. Done on the server because an
imported photo usually comes from another site, whose pixels the browser may not read (cross-origin canvas).
"""
import io
import uuid

from PIL import Image, ImageOps

from cookbook.helper.HelperFunctions import safe_request

MAX_WIDTH = 1600  # wide enough for a desktop hero, light on a phone
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:86.0) Gecko/20100101 Firefox/86.0'  # same as upstream


class CropError(ValueError):
    pass


def parse_crop(data):
    """{x, y, w, h} as fractions of the image (0..1) -> a checked tuple"""
    try:
        x, y, w, h = (float(data[k]) for k in ('x', 'y', 'w', 'h'))
    except (KeyError, TypeError, ValueError):
        raise CropError('crop must be {x, y, w, h} between 0 and 1')
    if not (0 <= x < 1 and 0 <= y < 1 and 0 < w <= 1 and 0 < h <= 1 and x + w <= 1.0001 and y + h <= 1.0001):
        raise CropError('crop out of the image')
    return x, y, min(w, 1 - x), min(h, 1 - y)


def source_image(recipe, image_url=None):
    """the photo to crop: the one at `image_url` (an import), else the recipe's current photo"""
    if image_url:
        response = safe_request('GET', image_url, headers={'User-Agent': USER_AGENT})
        return io.BytesIO(response.content)
    if not recipe.image:
        raise CropError('the recipe has no photo')
    recipe.image.open('rb')
    try:
        return io.BytesIO(recipe.image.read())
    finally:
        recipe.image.close()


def crop_image(raw, crop):
    """crop (fractions of the upright image), cap the width, return JPEG bytes"""
    try:
        img = Image.open(raw)
        img = ImageOps.exif_transpose(img)  # phone photos: crop what the user saw
    except Exception:
        raise CropError('not an image')
    x, y, w, h = crop
    box = (round(x * img.width), round(y * img.height), round((x + w) * img.width), round((y + h) * img.height))
    if box[2] - box[0] < 1 or box[3] - box[1] < 1:
        raise CropError('crop too small')
    img = img.crop(box)
    if img.width > MAX_WIDTH:
        img = img.resize((MAX_WIDTH, round(img.height * MAX_WIDTH / img.width)), Image.LANCZOS)
    out = io.BytesIO()
    img.convert('RGB').save(out, 'JPEG', quality=85, optimize=True)  # re-encoding also drops the metadata
    return out.getvalue()


def save_cropped(recipe, image_url, crop):
    from django.core.files.base import ContentFile
    data = crop_image(source_image(recipe, image_url), crop)
    recipe.image.save(f'{uuid.uuid4()}_{recipe.pk}.jpeg', ContentFile(data), save=True)
    return recipe.image.url
