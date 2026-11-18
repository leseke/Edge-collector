# Collecte publique des enchères Graded Card Center

Le collecteur découvre des liens directs depuis la page publique des enchères. Les options examinées étaient une recherche web facturée et la lecture de la page publique. Retenir la seconde dans le cron existant. Le sitemap de lots est volumineux, la page publique fournit une liste bornée de candidats.

La file D1 `gcc_lot_queue` garde l'identifiant de lot, le premier jour de relevé, le prochain contrôle et la date de vente payée. Le collecteur prend jusqu'à quatre liens par jour dans la page et contrôle jusqu'à six candidats, avec une fenêtre de suivi de vingt-huit jours. Une vente retenue doit passer les contrôles existants de langue, référence, finition ou grade, prix et statut payé. Elle rejoint la table immuable `paid_market_sales` utilisée par le Radar. Une enchère active ne crée pas de vente. Le point HTTP existant conserve sa fonction.

Vérification : la page source fournit des liens, un lot actif reste en file, le même lot payé le lendemain est inséré une fois avec la bonne variante. Arrêter la nouvelle tâche programmée arrête les requêtes et conserve les données. Aucun service de recherche payant n'est nécessaire. La couverture est partielle et le déploiement réel du collecteur reste une étape distincte de la prévisualisation de l'interface.
