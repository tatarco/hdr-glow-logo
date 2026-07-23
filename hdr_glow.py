#!/usr/bin/env python3
"""Make a logo 'glow' on HDR screens by tagging it Rec.2020 + PQ.

This reproduces the HDR-logo trick seen on Wiz / Port.io / Slack in the LinkedIn
feed: a flat, normal-looking image whose *white* pixels are decoded at up to
`--nits` cd/m2 on an HDR display, so the logo literally emits more light than the
surrounding white UI. On SDR screens it just looks like a normal (slightly flat)
image. No glow filter, no animation -- only a colour profile.

Mechanism: we tag the PNG as BT.2020 primaries + PQ (SMPTE ST 2084) transfer via
a `cICP` chunk. Under PQ, code value 255 decodes to 10,000 nits, so plain white
"burns". We optionally rescale code values so the brightest pixel lands on a
chosen nit level (the calibration knob -- real panels clip and 10,000 nits is
eye-searing, so the default is a saner 1,000).

Same idea as github.com/dtinth/superwhite and hdr-shnitz.vercel.app; this is a
dependency-light, tweakable CLI version. Reverse-engineered, not invented.
"""
import argparse
import io
import os
import struct
import sys
import zlib

# --- SMPTE ST 2084 (PQ) constants ---
_M1 = 2610 / 16384
_M2 = 2523 / 4096 * 128
_C1 = 3424 / 4096
_C2 = 2413 / 4096 * 32
_C3 = 2392 / 4096 * 32


def pq_oetf(y: float) -> float:
    """PQ inverse-EOTF: normalized luminance [0,1] -> code [0,1]."""
    y = max(0.0, min(1.0, y))
    p = y ** _M1
    return ((_C1 + _C2 * p) / (1 + _C3 * p)) ** _M2


# --- PNG chunk surgery (pure stdlib, no pixel decode) ---
_SIG = b"\x89PNG\r\n\x1a\n"
# cICP data: colour primaries 9 (BT.2020), transfer 16 (PQ), matrix 0 (RGB),
# video full-range flag 1.
_CICP = bytes([9, 16, 0, 1])
# Colour chunks that would contradict cICP -- drop them so the HDR tag wins.
_DROP = {b"iCCP", b"sRGB", b"gAMA", b"cHRM"}


def _make_chunk(typ: bytes, data: bytes) -> bytes:
    return (struct.pack(">I", len(data)) + typ + data
            + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF))


def _iter_chunks(png: bytes):
    i = 8
    while i < len(png):
        length = struct.unpack(">I", png[i:i + 4])[0]
        yield png[i + 4:i + 8], png[i:i + 12 + length]
        i += 12 + length


def tag_hdr(png_bytes: bytes) -> bytes:
    """Insert a cICP (BT.2020/PQ) chunk after IHDR and strip conflicting tags."""
    out = [_SIG]
    cicp = _make_chunk(b"cICP", _CICP)
    for typ, raw in _iter_chunks(png_bytes):
        if typ in _DROP:
            continue
        out.append(raw)
        if typ == b"IHDR":
            out.append(cicp)
    return b"".join(out)


_ICC_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "assets", "rec2020-pq.icc")


def convert(inp: str, outp: str, nits: int = 1000) -> str:
    from PIL import Image  # only needed for pixel work
    im = Image.open(inp).convert("RGBA")
    ext = os.path.splitext(outp)[1].lower()

    if ext in (".jpg", ".jpeg"):
        # LinkedIn-robust path. LinkedIn re-encodes uploads to JPEG, which DROPS
        # a PNG cICP chunk but PRESERVES an embedded ICC profile. So we tag the
        # image with a real Rec.2020 + PQ ICC profile (the same mechanism Wiz
        # uses) and save JPEG. White stays ~255 and the profile makes it burn.
        with open(_ICC_PATH, "rb") as f:
            icc = f.read()
        bg = Image.new("RGB", im.size, (0, 0, 0))
        bg.paste(im, mask=im.split()[3])           # flatten alpha onto black
        bg.save(outp, "JPEG", quality=95, subsampling=0, icc_profile=icc)
        return outp

    # PNG path: cICP tag + optional brightness remap (for self-hosted web use,
    # e.g. an <img> you serve yourself, where the chunk is never stripped).
    if nits < 10000:
        k = pq_oetf(nits / 10000.0)  # brightest code -> `nits` on PQ curve
        lut = [round(v * k) for v in range(256)]
        r, g, b, a = im.split()
        im = Image.merge("RGBA", (r.point(lut), g.point(lut), b.point(lut), a))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    with open(outp, "wb") as f:
        f.write(tag_hdr(buf.getvalue()))
    return outp


def demo() -> None:
    """Self-check: PQ math + cICP tagging + brightness remap round-trip."""
    from PIL import Image
    assert abs(pq_oetf(1.0) - 1.0) < 1e-9
    assert pq_oetf(0.0) < 1e-5  # PQ(0) ~ 7e-7, effectively black
    assert abs(pq_oetf(0.1) - 0.7518) < 1e-3  # 1000 nits -> ~0.752 code
    assert abs(pq_oetf(0.4) - 0.9026) < 1e-3  # 4000 nits -> ~0.903 code

    # white+black test image -> convert at 1000 nits -> reopen and verify.
    src = "/tmp/_hdrglow_src.png"
    dst = "/tmp/_hdrglow_dst.png"
    Image.new("RGBA", (2, 1), (0, 0, 0, 255)).load()
    im = Image.new("RGBA", (2, 1))
    im.putpixel((0, 0), (255, 255, 255, 255))
    im.putpixel((1, 0), (0, 0, 0, 255))
    im.save(src)
    convert(src, dst, nits=1000)

    data = open(dst, "rb").read()
    types = [t for t, _ in _iter_chunks(data)]
    assert b"cICP" in types, "cICP chunk missing"
    assert types.index(b"cICP") == types.index(b"IHDR") + 1, "cICP not after IHDR"
    assert not (_DROP & set(types)), "conflicting colour chunk survived"

    out = Image.open(dst).convert("RGBA")
    white = out.getpixel((0, 0))
    assert white[0] == round(255 * pq_oetf(0.1)) == 192, f"white remap wrong: {white}"
    assert out.getpixel((1, 0))[:3] == (0, 0, 0), "black should stay black"

    # JPEG path must embed the ICC profile (the bit LinkedIn preserves).
    jpg = "/tmp/_hdrglow_dst.jpg"
    convert(src, jpg)
    jdata = open(jpg, "rb").read()
    assert b"ICC_PROFILE" in jdata, "JPEG output is missing its ICC profile"
    assert Image.open(jpg).info.get("icc_profile"), "ICC profile not readable back"
    print("demo OK: PQ math, cICP tag, remap, and JPEG+ICC all verified")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input", nargs="?", help="input logo PNG")
    p.add_argument("output", nargs="?",
                   help="output file. Use .jpg for LinkedIn (embeds a PQ ICC "
                        "profile that survives re-encoding); .png for self-hosted web")
    p.add_argument("--nits", type=int, default=1000,
                   help="PNG only: peak brightness of white (default 1000; "
                        "Wiz ~4000; 10000 = max). JPEG uses the ICC profile as-is")
    p.add_argument("--demo", action="store_true", help="run self-check and exit")
    args = p.parse_args()

    if args.demo:
        demo()
        return
    if not args.input or not args.output:
        p.error("input and output are required (or use --demo)")
    convert(args.input, args.output, args.nits)
    print(f"wrote {args.output}  (white -> {args.nits} nits on HDR displays)")


if __name__ == "__main__":
    main()
