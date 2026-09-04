/* Rasterise the theme's SVGs through the ES's own renderer.
 *
 * The ES draws SVG with nanosvg, which silently ignores anything it does
 * not implement - a logo whose fill lives in a CSS class parses fine,
 * rasterises fine, and comes out solid black on a near-black tile. The
 * only way to catch that is to run the same rasteriser and look at the
 * pixels, which is what this does: for each file it prints the size it
 * lands on in a 99px box, how much of that box has ink, and how bright
 * the ink is. lum=0 means invisible; lum=255 is the white set.
 *
 *   cp <es-source>/external/nanosvg/nanosvg*.h .
 *   cc -O2 -o check-logos check-logos.c -lm
 *   ./check-logos ../art/logos/*.svg
 *
 * nanosvg.h and nanosvgrast.h come from the ES source tree (zlib licence);
 * they are not vendored here. tools/host-preview/preview.sh leaves a copy
 * of that tree in ~/.cache/relicos/es-preview/es.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define NANOSVG_IMPLEMENTATION
#include "nanosvg.h"
#define NANOSVGRAST_IMPLEMENTATION
#include "nanosvgrast.h"

int main(int argc, char** argv) {
    NSVGrasterizer* rast = nsvgCreateRasterizer();
    for (int i = 1; i < argc; i++) {
        NSVGimage* img = nsvgParseFromFile(argv[i], "px", 96.0f);
        if (!img) { printf("%s\tPARSE-FAIL\n", argv[i]); continue; }
        if (img->width <= 0 || img->height <= 0) { printf("%s\tNO-SIZE\n", argv[i]); nsvgDelete(img); continue; }
        float scale = 99.0f / (img->width > img->height ? img->width : img->height);
        int w = (int)(img->width * scale), h = (int)(img->height * scale);
        if (w < 1) w = 1; if (h < 1) h = 1;
        unsigned char* px = malloc(w * h * 4);
        memset(px, 0, w * h * 4);
        nsvgRasterize(rast, img, 0, 0, scale, px, w, h, w * 4);
        long opaque = 0; double lum = 0;
        for (int p = 0; p < w * h; p++) {
            int a = px[p*4+3];
            if (a > 32) { opaque++; lum += (px[p*4]*0.299 + px[p*4+1]*0.587 + px[p*4+2]*0.114); }
        }
        printf("%s\t%dx%d\tink=%.1f%%\tlum=%.0f\n", argv[i], w, h,
               100.0 * opaque / (w * h), opaque ? lum / opaque : 0.0);
        free(px); nsvgDelete(img);
    }
    return 0;
}
