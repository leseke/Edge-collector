# EDGE — Publication-linked multi-retailer dossiers

`mri_case_history.py` builds `mri_cases.json` and `mri_case_report.md` after coverage/source context and before dossier manifest generation. It includes only products with at least two currently verified EUR retail sources. Observed candidate publication references retain source roles, exact titles, stated publication dates, hashes and candidate discovery date. A reference in an article summary remains distinct from the title subject. Media reviews are not reclassified as manufacturer announcements.

Each current retailer is matched to the same product/seller/URL/currency historical series. First/latest observed asking price and declared stock, observation timestamps, raw hashes and de-duplicated successful-capture count are retained. A single captured price has null variation, not a measured 0% change. Their price change describes only the collected span; it is not an attributed publication effect. Existing publication reaction windows are linked only by both publication ID and observation ID. No pre-publication baseline or mature target capture is invented. Products with multiple retailers but no discovery publication remain explicit retail controls.

Actual publication response, realised sales, volumes, delivered prices and net margin remain separate missing inputs. No purchase, causal claim or price forecast is emitted. Raw pages and JSON/Markdown reports are archived in the run snapshot and final manifest.

Two added JouéClub source plans target LEGO 11383 (EAN 5702018063644) and 42705 (EAN 5702018060629), both already discovered through real archived publications. Direct probes passed exact-reference/EUR structured-offer checks; the workflow independently verifies them. Their local success alone is not counted as autonomous coverage. Source URLs reside in commercial_targets.json.

The collector now checks LEGO identity against an explicit brand when present, or a LEGO name marker otherwise; a matching number from another brand is rejected. Research target capacity is bounded by both the nominal eight-target research cap and remaining capacity within sixteen total sources. Ten configured base sources therefore leave six research slots; this does not claim six currently monitored research sources.

## Pages publication verification

Pages deployment run 41290451212 successfully published commit c451d8ca9a6c019a17b4c64aaee1b303c54446ff after previous runs reported a stale blocking deployment. The old deployment was already terminal; its cancellation request was rejected without changing it. The temporary recovery workflow has been retired. No permanent scheduler/service root cause is claimed; Pages publication is verified separately from collection success.

Later cleanup publication retries again encountered the Pages deployment lock. The public site returned HTTP 200 and the c451d8c publication is verified, but permanent publication reliability is not established. Collector/data-branch results remain separately validated.
