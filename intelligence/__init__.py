"""EDGE Intelligence Report v1 : standard de rapports d'analyse (AI-001).

Aucun agent actif, aucun appel reseau. Le validateur Python
(intelligence.validator) fait foi ; le JSON Schema publie
(intelligence/schema/) sert a l'interoperabilite et reste aligne par test.
"""
SCHEMA_ID = "edge.intelligence_report"
SCHEMA_VERSION = "1.3.0"  # 1.1 : verification_record ; 1.2 : interpretation, basis, computations ; 1.3 : source_claim_type (facultatifs)
