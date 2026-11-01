# EDGE — Publication-linked multi-retailer dossiers

`mri_case_history.py` builds `mri_cases.json` and `mri_case_report.md` after coverage/source context and before dossier manifest generation. It includes only products with at least two currently verified EUR retail sources. Observed candidate publication references retain source roles, exact titles, stated publication dates, hashes and candidate discovery date. A reference in an article summary remains distinct from the title subject. Media reviews are not reclassified as manufacturer announcements.

Each current retailer is matched to the same product/seller/URL/currency historical series. First/latest observed asking price and declared stock, observation timestamps, raw hashes and de-duplicated successful-capture count are retained. Their price change describes only the collected span; it is not an attributed publication effect. Existing publication reaction windows are linked only by both publication ID and observation ID. No pre-publication baseline or mature target capture is invented. Products with multiple retailers but no discovery publication remain explicit retail controls.

Actual publication response, realised sales, volumes, delivered prices and net margin remain separate missing inputs. No purchase, causal claim or price forecast is emitted. Raw pages and JSON/Markdown reports are archived in the run snapshot and final manifest.

Two added JouéClub source plans target LEGO 11383 (EAN 5702018063644) and 42705 (EAN 5702018060629), both already discovered through real archived publications. Direct probes passed exact-reference/EUR structured-offer checks; the workflow independently verifies them. Their local success alone is not counted as autonomous coverage. Source URLs reside in commercial_targets.json.

The collector now checks LEGO identity against an explicit brand when present, or a LEGO name marker otherwise; a matching number from another brand is rejected. Research target capacity is bounded by both the nominal eight-target research cap and remaining capacity within sixteen total sources. Ten configured base sources therefore leave six research slots; this does not claim six currently monitored research sources.

## Pages recovery

Failed Pages logs repeatedly name deployment 8e44642dd3c3e03833fe159d0f403bfe613e3c3d as blocking, while its authenticated API status reports success. A targeted recovery workflow uses the documented Pages cancellation endpoint on that exact stale blocker, followed by a new deployment attempt. It does not delete/unpublish the Pages site or alter repository settings. The workflow is triggered only when its own file changes or by explicit manual dispatch. Pages success must be verified separately from collector success.
