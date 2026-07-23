# hdr-glow-logo

Make a logo **glow** in the LinkedIn / Slack / social feed on HDR screens — the
trick behind that Wiz logo that "burned" brighter than the white UI around it.

It's not a filter, not an animation, not a glow effect. It's a flat image with
one unusual thing inside it: a **Rec.2020 + PQ (HDR) colour profile**. Under PQ,
the white pixels get decoded at up to ~4,000 nits — many times brighter than the
~200-nit white of the page — so the logo physically emits more light than
everything around it. Your eye can't not go there.

On a normal (SDR) screen it just looks flat/normal, and in a screenshot the
magic disappears entirely. The effect only exists live, on HDR hardware (every
modern iPhone / MacBook).

> **Credit where it's due:** this is *reverse-engineered, not invented.* Port.io,
> Slack and others shipped it first; it circulated on Reddit for months. Prior
> art and better cross-screen handling: [dtinth/superwhite](https://github.com/dtinth/superwhite)
> and [hdr-shnitz.vercel.app](https://hdr-shnitz.vercel.app/). This repo is a
> tiny, tweakable CLI + an installable Claude skill so you can do it to your own
> logo in one command.

## Install

```bash
git clone https://github.com/tatarco/hdr-glow-logo
cd hdr-glow-logo
pip install pillow   # only dependency (used for the brightness knob)
```

## Use

**For LinkedIn (or anywhere the platform re-encodes your upload) → output `.jpg`:**

```bash
python3 hdr_glow.py your-logo.png your-logo-hdr.jpg
```

This embeds a real **Rec.2020 + PQ ICC profile** — the same mechanism Wiz uses.
Upload the JPEG as a **company/brand page logo** (personal profile photos get
re-encoded harder). View on an HDR display to see it burn.

**For a page you host yourself (e.g. an `<img>` on your own site) → `.png`:**

```bash
python3 hdr_glow.py your-logo.png your-logo-hdr.png --nits 4000
```

- `--nits` — *PNG only* — peak brightness of the white pixels. Default `1000`
  (visible, not eye-searing). Wiz ~`4000`. `10000` = raw superwhite. The JPEG
  path uses the ICC profile as-is (white stays 255).
- `--demo` — run the built-in self-check (PQ math + cICP tag + remap + JPEG/ICC).

### Why two formats — the gotcha that makes it *actually* work

The magic is a colour tag that says "interpret this as HDR." There are two ways
to attach it, and they survive very differently:

| Carrier | Where it works | Survives a platform re-encode? |
|---|---|---|
| PNG `cICP` chunk | pages **you** serve | ❌ **No** — LinkedIn converts PNG→JPEG and drops the chunk → flat |
| **ICC profile in a JPEG** | anywhere, incl. LinkedIn | ✅ **Yes** — ICC profiles are copied through |

So a PNG+cICP looks great on your own site but goes **flat after you upload it to
LinkedIn**. The JPEG+ICC path is what glows in the feed. (Verified by pulling the
live Wiz logo off LinkedIn: it's a JPEG carrying a `...PQ Transfer` ICC profile.)

## How it works

1. Tag the PNG with a `cICP` chunk: BT.2020 primaries, PQ (SMPTE ST 2084)
   transfer. Conflicting colour chunks (`iCCP`/`sRGB`/`gAMA`/`cHRM`) are stripped
   so the HDR tag wins.
2. Under PQ, code value 255 decodes to 10,000 nits. To land white on a chosen
   brightness we rescale code values by the PQ inverse-EOTF of your `--nits`
   target — that's the calibration knob real panels need.
3. A happy side effect: mid-tones reinterpreted through PQ come out darker, so
   the background stays dim (~tens of nits) while the whites burn — exactly the
   "dark card, glowing letters" look.

Verify the tag on any output:

```bash
ffprobe -show_entries stream=color_transfer,color_primaries your-logo-hdr.png
# color_transfer=smpte2084   color_primaries=bt2020
```

## The catch (read this before you ship it)

On screens that **don't** support HDR — many Windows/Dell monitors, ~half of a
typical feed — the same file can look *broken*: smeared, dirty, low-res, "like a
malfunction." It's a genuine trade-off, not a free win. Use it knowing part of
your audience sees the inverse effect. And platforms close it: Slack already
patched theirs.

## License

MIT
