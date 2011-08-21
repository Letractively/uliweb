import os

def fix_filename(filename, suffix=''):
    """
    e.g.
        fix_filename('icon.png', '_40x40')
        
        return
    
            icon_40x40.png
    """
    if suffix:
        f, ext = os.path.splitext(filename)
        return f+suffix+ext
    else:
        return filename
        
def resize_image(fobj, size=(50, 50)):
    import Image
    from StringIO import StringIO
    
    image = Image.open(fobj)
    if image.mode not in ('L', 'RGB'):
        image = image.convert('RGB')
    image = image.resize(size, Image.ANTIALIAS)
    o = StringIO()
    image.save(o, "JPEG")
    o.seek(0)
    return o

def thumbnail_image(infile, size=(200, 75)):
    import Image

    file, ext = os.path.splitext(infile)
    im = Image.open(infile)
    im.thumbnail(size, Image.ANTIALIAS)
    ofile = file + ".thumbnail" + '.jpg'
    im.save(ofile, "JPEG")
    return ofile

def resize_image_string(buf, size=(50, 50)):
    from StringIO import StringIO
    f = StringIO(buf)
    return resize_image(f, size).getvalue()
    
def image_size(filename):
    import Image

    image = Image.open(filename)
    return image.size

def crop_resize(fobj, outfile, x, y, w, h, size=(50, 50)):
    import Image

    image = Image.open(fobj)
    if image.mode not in ('L', 'RGB'):
        image = image.convert('RGB')
    r = image.crop((x, y, x+w, y+h))
    if size:
        rm = r.resize(size, Image.ANTIALIAS)
    rm.save(outfile, "JPEG")
    