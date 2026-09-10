# Contributing

## Documentation

`docs/guide.md` is the operator guide for this decoder. It is the single place
configuration is documented — the README deliberately stays short — and it is
aggregated into the central ADL documentation site.

**A pull request that changes what an operator sees or types must update
`docs/guide.md` in the same PR.** For this repository that means: the file
format the decoder accepts, the record keys it emits (the *File Variable
Names* an operator maps), the units it declares, which files it selects, and
any message it logs that the guide's feedback catalogue lists.

If the change is visible on screen, also update `docs/screenshots.yml` and
regenerate the images with the capture harness in the `adl` repo:

```bash
# from a checkout of wmo-raf/adl, with Docker running
scripts/capture-plugin-docs.sh ../adl-plugins/adl-kmd-kcsap-ftp-decoder
```

`--only <entry>` re-shoots a single entry, which is what to use for a crop fix:
a full run re-renders every image and the diagnostic shots carry live
timestamps, so fixing one crop otherwise lands as a diff in unrelated images.

The demo instance the images are taken against is seeded from
`docs/screenshots/fixture.json` and served by the harness's mock FTP source,
which runs this repo's `docs/screenshots/mock-ftp/generate.py` to produce
sample files in this decoder's own format. A change to the format the decoder
reads belongs in that generator too, or the screenshots stop matching the
decoder.

Images are code: never hand-edit a PNG in `docs/images/`; change the manifest
entry and regenerate. Keep images free of text (only numbered badges), since
the docs are translated.

Messages the plugin shows to operators are listed verbatim-shaped in the
guide's feedback catalogue — add a row when you add or change one.

## Development

See the README for the dev stack. Lint with `make lint` and format with
`make format` inside `plugins/adl_kmd_kcsap_ftp_decoder/`.

## Releases

Tag releases bare (`0.3.0`, never `v0.3.0`): `plugins.toml` entries pin the tag
verbatim. Use `gh release create 0.3.0`.
