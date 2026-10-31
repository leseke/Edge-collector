# Secondary asks and conditional economics

The three priority references are now searched on public eBay Ireland result
pages every commercial run. This bounded pilot captures recognised listing cards,
not authenticated transaction history. It requires LEGO and the exact reference
in the title, a stable item ID and an unambiguous EUR price. Accessories,
incomplete sets and multiple-reference bundles remain labelled exclusions.
Presale claims remain separate from stock verification. Individual item pages
are not assumed verified merely because a result card is visible.

The parser does not treat seller feedback, asking prices, a sold badge or a
platform sold-count as confirmed settled transaction prices. It does not infer
France shipping from a fee shown in an Ireland/Spain search context. Asking
prices are excluded from the realized-sale series and investment valuations.
The output explicitly retains unknown France delivery, fees and net proceeds.
Interstitals, challenges and changed/unrecognised layouts are collection failures,
never evidence that no market or stock exists. No bypass or paid API is used.

Manually reviewed eBay pages are retained as dated historical evidence, not
refreshed by repeating the workflow. The 40889 ask of EUR 39.50 had shipping
displayed for Spain; the EUR 44.90 listing had a sold marker and a presale title.
Neither establishes a France delivered cost or settled transaction price. Generic
comparator copies of gift nominal values are not treated as executable offers.

`bundle_economics.json` separates real unknowns from explicit scenarios. For the
announced EUR 499.99 main-set price, hypothetical delivered alternatives at 5%,
10% and 15% discounts require EUR 25, 50 and 75 net gift proceeds respectively,
assuming zero incremental costs solely for these scenarios. Actual extra costs
raise the threshold; unknown costs are not silently filled with zero. No actual
best alternative, net proceeds, measured advantage or purchase signal is invented.
The unconfirmed 40889 gift stacking is excluded from bundle revenue.

The readable report includes public listing links, dated reviewed evidence and
clearly marked hypothetical thresholds. The assessments reference this evidence
without promoting result cards to valuation facts or changing the financial
watchlist. The existing final manifest covers all new files. Source selection
and observation remain independent of the capital allocation.

## Real GitHub validation
The first scheduled-environment execution returned HTTP 403 for all three eBay
queries. This is explicitly FAILED secondary collection within a PARTIAL overall
run. BrickLink public price-guide requests also returned 403 during research.
No bypass is used. A separate one-time research-environment baseline preserves
extracted listing cards and their original capture timestamps/source hashes.
It is labelled automatically_refreshed=false and never substitutes for current
GitHub observations. Full raw HTML for this baseline is not included in the Git
snapshot; only the extracted observations and hashes are retained there.
The live GitHub failure remains visible even when the dated baseline is shown.
