# Publication and reaction pilot

The existing six-hour commercial workflow now also captures the official LEGO
press-release listing and the Brickset and Toys N Bricks RSS feeds. Manufacturer
statements and specialist-media publications retain separate source roles.

Every capture appends announcements.json, raw source evidence and reactions.json
to the isolated commercial history branch. The manifest covers these files and
the updated market report. Existing snapshots remain unchanged.

Each publication has a stable source-plus-canonical-URL ID, title, bounded summary,
source publication time, first detection time, content hash and source evidence
hash. The first successful capture of each source imports a baseline; existing
articles are not new alerts. Later first sightings are marked new since the prior
capture, without asserting that the publication itself is recent. Detection lag
is explicit. No notification is sent. Revisions keep the same publication ID and
their content hashes are preserved in successive snapshots.

A publication is not automatically a verified launch, reprint or withdrawal.
All items, including reviews and deal articles, retain type PUBLICATION. A media
article does not become a manufacturer statement. Product links require an exact
SKU mention in the title or extracted summary. No semantic or brand-only match
is silently promoted. Feed coverage is bounded to what the sources expose; a
page becoming inaccessible does not imply that its publications were withdrawn.

Reaction windows use source publication time, never first detection time. For
each linked retail price series, the pre-event baseline must be no more than
24 hours old. A J+1/J+3/J+7 observation must occur within the six hours after its
target time. Missing baselines or missed windows remain missing. Products not
yet tracked remain explicitly unmeasured. Previously seen articles remain
available for reaction calculations even after leaving a rolling feed.

Changes are descriptive asking-price and declared-stock observations. They do
not establish causal impact, resale volume, liquidity, prediction quality, or an
advantage before consensus. No automatic buying or purchase recommendation is
introduced. Costs and capital do not filter observation or publication discovery.

Tests cover parsing, stable identity, source hosts, DTD rejection, timestamps,
baseline import, deduplication, SKU boundaries, reaction timing, missing data and
future-dated publications. Real network captures are validated separately.
