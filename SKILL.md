---
name: hdr-glow-logo
description: Make a logo "glow" on HDR screens (the Wiz/Port/Slack LinkedIn trick) by tagging a PNG with a Rec.2020 + PQ HDR colour profile so its white pixels burn brighter than the surrounding UI. Use when someone wants an HDR / glowing / "superwhite" logo, wants to reproduce the Wiz LinkedIn logo effect, or asks to make an image emit light in the feed.
---

# hdr-glow-logo

Turn any logo PNG into one that emits light on HDR displays. Not a filter or
animation — the file is tagged BT.2020 + PQ (SMPTE ST 2084), so its white pixels
decode at up to ~4,000 nits and outshine the ~200-nit white of the feed.

## When to use

- "Make my logo glow / burn / superwhite on LinkedIn"
- "Reproduce the Wiz (or Port.io / Slack) HDR logo effect"
- "Make this image emit light on iPhone/MacBook screens"

## How to run

The whole thing is one script, `hdr_glow.py` (needs Python 3 + `pillow`).

**For LinkedIn / social (platform re-encodes the upload) → output `.jpg`:**

```bash
python3 hdr_glow.py INPUT.png OUTPUT.jpg
```

This embeds a Rec.2020+PQ **ICC profile** (bundled at `assets/rec2020-pq.icc`),
which survives LinkedIn's JPEG re-encode. **A PNG `cICP` chunk does NOT survive
it** — it looks great on a self-hosted page but goes flat once uploaded. This is
the #1 mistake; default to JPEG for anything posted to a platform.

**For a self-hosted `<img>` → `.png`:**

```bash
python3 hdr_glow.py INPUT.png OUTPUT.png --nits 4000
```

- `--nits` (PNG only) sets peak white brightness. `4000` ~ matches Wiz.
- Verify a JPEG's profile: `python3 -c "from PIL import Image;print(bool(Image.open('OUT.jpg').info.get('icc_profile')))"` → `True`.
- Verify a PNG's tag: `ffprobe -show_entries stream=color_transfer,color_primaries OUT.png` → `smpte2084` / `bt2020`.
- Self-check the script: `python3 hdr_glow.py --demo`.

## What to tell the user afterwards

1. Upload as a **company/brand page logo** on LinkedIn — personal profile photos
   get re-encoded and lose the effect; page logos pass through untouched.
2. It only shows live on **HDR hardware**; screenshots and SDR screens see a
   flat image.
3. **Trade-off:** on non-HDR screens (many Windows/Dell monitors, roughly half a
   feed) it can look smeared/broken. Say so. Platforms also patch it over time.

## Credit

Reverse-engineered, not invented. Prior art: Port.io / Slack, and
[dtinth/superwhite](https://github.com/dtinth/superwhite),
[hdr-shnitz.vercel.app](https://hdr-shnitz.vercel.app/).
