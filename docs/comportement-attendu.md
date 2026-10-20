# Comportement attendu de csvcheck

Ce document décrit les entrées acceptées, les contrôles, les sorties et les comportements en cas d’échec prévus pour la version 0.1. Il sert de référence pour l’implémentation et les tests ; il ne décrit pas des fonctionnalités déjà disponibles.

## Objectif et périmètre

csvcheck doit analyser localement un fichier CSV de contacts avant son import dans un autre outil. Son diagnostic doit distinguer les anomalies de données, les anomalies de schéma et les erreurs empêchant une analyse complète.

La version 0.1 prévoit :

- Une utilisation en ligne de commande.
- Un seul profil de contrôle : `contacts-v1`.
- La vérification de la structure du CSV et des valeurs obligatoires.
- Un contrôle simplifié du format des adresses e-mail.
- La détection des adresses e-mail dupliquées.
- Un rapport HTML et un CSV d’anomalies.

L’interface graphique, les fichiers Excel, la correction automatique, la vérification de l’existence des boîtes e-mail et les fonctionnalités d’intelligence artificielle sont hors périmètre.

## Entrées acceptées

### Format et lecture

| Propriété | Comportement attendu |
|---|---|
| Format | CSV uniquement |
| Encodage | UTF-8, avec ou sans BOM initial |
| Séparateur | Point-virgule par défaut ; virgule sur choix explicite |
| Détection du séparateur | Aucune détection automatique ni nouvelle tentative silencieuse |
| En-tête | Obligatoire, au début du fichier |
| Délimiteur de texte | Guillemets doubles |
| Guillemets dans un champ délimité | Représentés par deux guillemets doubles |
| Fins de ligne | LF et CRLF acceptées |
| Champs multilignes | Acceptés à l’intérieur de guillemets doubles |
| Taille du fichier | Au maximum 50 Mio, soit 52 428 800 octets |
| Taille d’un champ | Au maximum 100 000 caractères décodés |

Les limites sont inclusives : atteindre une limite est accepté, la dépasser interrompt l’analyse. Elles délimitent les entrées prises en charge et ne garantissent pas une consommation mémoire constante.

### Colonnes du profil `contacts-v1`

Les colonnes `id`, `nom` et `email` sont obligatoires. Les colonnes `telephone`, `code_postal` et `notes` sont facultatives.

L’ordre des colonnes est libre. Les colonnes supplémentaires sont acceptées : leurs valeurs ne font l’objet d’aucun contrôle métier, mais restent soumises aux règles de structure et aux limites de lecture.

Les noms sont comparés exactement, sans suppression d’espaces ni conversion de casse. `Email` et ` email` ne correspondent pas à `email`.

Un nom vide ou composé uniquement de caractères d’espacement selon `str.strip()` est refusé. Ce test ne modifie pas le nom. Les noms dupliqués sont recherchés par comparaison exacte.

## Déroulement de l’analyse

Le programme doit vérifier l’en-tête, puis lire le fichier jusqu’à la fin en contrôlant sa structure et les limites de lecture.

Si toutes les colonnes obligatoires sont présentes, les contrôles des valeurs sont également exécutés. Si une colonne obligatoire manque, elle est signalée et aucun contrôle des valeurs n’est exécuté ; les vérifications de structure continuent.

Une erreur bloquante rencontrée à n’importe quel moment invalide l’analyse complète. Elle prévaut sur les anomalies déjà trouvées : aucun résultat partiel ne doit être présenté comme un diagnostic complet.

Un fichier contenant uniquement un en-tête valide avec les colonnes obligatoires est accepté : il contient zéro enregistrement et ne présente aucune anomalie de données.

### Références et compteurs

- L’en-tête n’est pas un enregistrement de données.
- Le premier enregistrement de données porte le numéro `1`.
- Les lignes physiques sont numérotées à partir de `1`, en-tête inclus.
- Chaque enregistrement possède une ligne de début et une ligne de fin, bornes incluses.
- Un champ multiligne appartient à un seul enregistrement.
- Un même enregistrement peut présenter plusieurs anomalies.

Pour une analyse complète, le nombre total d’enregistrements lus est distinct du nombre d’enregistrements évalués et du nombre d’enregistrements affectés.

Si une colonne obligatoire manque, le nombre total d’enregistrements peut être compté par la lecture complète, mais le nombre évalué est `0` et le nombre affecté par des anomalies de valeurs est indéterminé, pas égal à zéro. En cas d’erreur bloquante, aucun bilan final complet n’est publié.

## Contrôles

### Présence des colonnes

Chaque colonne obligatoire absente produit une anomalie `MISSING_COLUMN`. Cette anomalie concerne le schéma du fichier ; elle n’est associée à aucun enregistrement.

### Valeurs obligatoires

Pour chaque enregistrement évalué, `id`, `nom` et `email` doivent contenir une valeur.

Une valeur vide ou composée uniquement de caractères d’espacement selon `str.strip()` produit une anomalie `REQUIRED_VALUE`. Le test ne modifie jamais la valeur.

### Format des adresses e-mail

Une adresse non manquante doit correspondre entièrement à cette expression :

```text
[^@\s]+@[^@\s]+\.[^@\s]+
```

Une valeur refusée produit `EMAIL_FORMAT`. Une valeur manquante produit uniquement `REQUIRED_VALUE`, sans anomalie de format supplémentaire.

Ce contrôle est volontairement simplifié : il n’est pas une validation exhaustive des normes d’e-mail et ne vérifie ni l’existence du domaine, ni celle de la boîte, ni la délivrabilité.

### Doublons d’adresses e-mail

Seules les adresses non manquantes dont le format est accepté participent à la recherche de doublons.

Les valeurs sont comparées exactement, sans suppression d’espaces ni conversion de casse. Ainsi, `alice@example.com` et `Alice@example.com` sont distinctes pour ce profil.

Chaque enregistrement d’un groupe dupliqué produit une anomalie `DUPLICATE_EMAIL`, y compris la première occurrence.

### Ordre des anomalies

Les anomalies de données sont ordonnées par numéro d’enregistrement croissant, puis par position de colonne croissante, puis par code d’anomalie alphabétique.

Les anomalies de schéma suivent l’ordre des colonnes obligatoires : `id`, `nom`, `email`. Pour un même fichier et les mêmes options, la liste et l’ordre des anomalies doivent être identiques.

## Erreurs bloquantes et codes de retour

Les situations suivantes interrompent l’analyse :

- Fichier vide ou sans en-tête exploitable.
- Nom de colonne vide, composé uniquement d’espacement ou dupliqué.
- Encodage UTF-8 invalide.
- Champ entre guillemets non refermé.
- Nombre de champs différent de celui de l’en-tête.
- Ligne physique vide en dehors d’un champ entre guillemets.
- Dépassement d’une limite de lecture.
- Impossibilité de lire l’entrée ou de produire les sorties.

| Code de retour | Signification |
|---|---|
| `0` | Analyse complète sans anomalie |
| `1` | Analyse complète avec anomalies de données ou de schéma |
| `2` | Analyse impossible ou échec de génération des rapports |

Une erreur bloquante doit produire un message explicite sur la sortie d’erreur du terminal, sans recopier de valeur de cellule de données. Aucun nouveau dossier de rapports définitifs ne doit être publié.

## Rapports

### Rapport HTML

Le rapport doit présenter le statut, le profil, l’encodage et le séparateur utilisés, les compteurs applicables, les anomalies et leurs références. Il doit identifier les colonnes obligatoires absentes et préciser lorsque les valeurs n’ont pas été évaluées.

Aucune valeur de cellule des enregistrements de données n’est recopiée. Les noms de colonnes de l’en-tête peuvent être affichés pour expliquer le diagnostic.

Tout texte issu de l’entrée, notamment un nom de fichier ou de colonne, doit être échappé avant insertion dans le HTML. Le rapport ne contient aucun script et ne charge aucune ressource distante.

### CSV d’anomalies

Le fichier utilise UTF-8, le séparateur point-virgule et les fins de ligne LF. Son en-tête est :

```text
record_number;line_start;line_end;column_index;rule
```

Les quatre premières colonnes contiennent des entiers positifs ou des cellules vides. Les indices d’enregistrement et de colonne commencent à `1` ; les bornes de lignes physiques sont inclusives.

`rule` contient uniquement un code d’anomalie défini par le programme. Aucune valeur source, aucun nom de colonne et aucun message libre ne sont recopiés.

Pour `MISSING_COLUMN`, les quatre références sont vides. Le rapport HTML identifie la colonne absente. Sans anomalie, le CSV contient uniquement son en-tête.

### Publication des rapports

Chaque analyse utilise un nouveau dossier de rapports. Aucun fichier existant ne doit être écrasé, et le fichier source ne doit jamais servir de destination.

Les rapports ne deviennent définitifs qu’après la lecture complète et la réussite de leur génération. Les temporaires éventuels sont placés dans l’emplacement de sortie choisi et nettoyés après utilisation ou échec, dans la mesure du possible.

Un échec de nettoyage est signalé sans valeur de cellule source. Il ne doit pas transformer une analyse incomplète en succès.

## Préservation des données et confidentialité

- Le fichier source n’est jamais ouvert en écriture.
- Les valeurs restent des chaînes ; les zéros initiaux sont conservés.
- Aucune valeur n’est corrigée, supprimée ou normalisée automatiquement.
- L’analyse ne réalise aucun appel réseau et ne collecte aucune télémétrie.
- Le contenu des cellules n’est jamais exécuté comme du code ou une commande.
- Les journaux et diagnostics ne recopient aucune valeur de cellule de données.
- Les exemples et données de test du dépôt sont fictifs.
- Aucun fichier client, secret ou identifiant d’accès ne doit être ajouté au dépôt.
- Les dépendances sont limitées au nécessaire, leurs versions maîtrisées et leurs vulnérabilités connues vérifiées avant livraison.

Ces exigences doivent être démontrées par les tests. Elles ne garantissent ni la sécurité d’une machine déjà compromise, ni l’acceptation du fichier par tous les outils d’import.
