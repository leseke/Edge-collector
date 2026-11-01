# EDGE — Explicit Pages publication

GitHub Pages uses the repository's `EDGE Pages publication` workflow, with source set to GitHub Actions. It builds the existing root/Jekyll public site using official GitHub actions, validates both HTML entry points and their public JSON data, then deploys the verified artifact.

A single `pages` concurrency group serializes publication runs with `cancel-in-progress: false`. Backend collector changes alone do not trigger site deployment. Main-branch public HTML/data/assets/docs and the publishing workflow do trigger publication; manual dispatch remains available. The market-history collector and its data branch remain independent.

`deployment.json` exposes the published source commit and run ID for end-to-end verification. These are public repository metadata. They do not establish market-data freshness; source observation timestamps and collection status remain the authority for that.

The prior branch-based automatic publisher repeatedly reported a completed deployment as blocking later attempts. The migration removes that legacy publication path; successful deployment and served revision must be checked rather than inferring a fixed GitHub service root cause.

## Verified publication and separate data limitation

The first successful explicit publication is run 41298097028, source revision 99ad20ea9915ccee131b28a6ce6cd6eeb08f9641. Its live deployment.json returned HTTP 200 with that exact revision/run, and the root page, radar.json and mri/data/mri_public.json loaded successfully.

The root dashboard still reads the legacy radar.json generated on 12 October 2026. The MRI page is still the isolated baseline preview. Publication health is therefore verified separately from application data freshness. Connecting the current commercial-history snapshots and observed MRI cases to the public interface remains necessary before presenting that interface as the live research feed.
