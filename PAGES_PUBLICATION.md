# EDGE — Explicit Pages publication

GitHub Pages uses the repository's `EDGE Pages publication` workflow, with source set to GitHub Actions. It builds the existing root/Jekyll public site using official GitHub actions, validates both HTML entry points and their public JSON data, then deploys the verified artifact.

A single `pages` concurrency group serializes publication runs with `cancel-in-progress: false`. Backend collector changes alone do not trigger site deployment. Main-branch public HTML/data/assets/docs and the publishing workflow do trigger publication; manual dispatch remains available. The market-history collector and its data branch remain independent.

`deployment.json` exposes the published source commit and run ID for end-to-end verification. These are public repository metadata. They do not establish market-data freshness; source observation timestamps and collection status remain the authority for that.

The prior branch-based automatic publisher repeatedly reported a completed deployment as blocking later attempts. The migration removes that legacy publication path; successful deployment and served revision must be checked rather than inferring a fixed GitHub service root cause.
