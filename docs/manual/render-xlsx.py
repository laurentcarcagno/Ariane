"""PDF pages rendered by render-xlsx.ps1 -> trimmed PNG files named as the figures of the manual."""
import pathlib
import fitz  # PyMuPDF

here = pathlib.Path(__file__).parent
names = {"Page_de_garde": "xl-page-de-garde", "From-To": "xl-from-to", "Connecteurs": "xl-connecteurs", "Segments": "xl-segments",
         "Nomenclature": "xl-nomenclature", "Rapport": "xl-rapport"}
for src, dst in names.items():
    page = fitz.open(here / "img" / "pdf" / f"{src}.pdf")[0]
    pix = page.get_pixmap(matrix=fitz.Matrix(2.2, 2.2), alpha=False)
    box = pix.irect
    # trim the white margins
    s = pix.samples
    w, h, n = pix.width, pix.height, pix.n
    def dark(x, y):
        i = (y * w + x) * n
        return min(s[i:i + 3]) < 245
    xs = [x for x in range(0, w, 2) if any(dark(x, y) for y in range(0, h, 6))]
    ys = [y for y in range(0, h, 2) if any(dark(x, y) for x in range(0, w, 6))]
    clip = fitz.IRect(max(min(xs) - 8, 0), max(min(ys) - 8, 0), min(max(xs) + 8, w), min(max(ys) + 8, h))
    pix2 = fitz.Pixmap(pix, 0) if False else pix
    cropped = fitz.Pixmap(pix.colorspace, clip, pix.alpha)
    cropped.copy(pix, clip)
    cropped.save(here / "img" / f"{dst}.png")
    print(dst, cropped.width, cropped.height)
