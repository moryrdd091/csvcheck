# csvcheck

Outil Python en cours de développement pour contrôler localement
des fichiers CSV de contacts avant leur import dans un autre outil.

## Objectif

Détecter les problèmes de structure et les anomalies de données,
sans modifier le fichier source.

Le projet privilégie des diagnostics explicites, des résultats
reproductibles et la préservation des valeurs d’origine.

## État du projet

Le comportement attendu et les jeux de référence sont définis.
Le moteur d’analyse et l’interface en ligne de commande
ne sont pas encore implémentés.

Aucune commande d’installation ou d’utilisation n’est disponible
à ce stade.

## Périmètre de la version 0.1

Fonctionnalités prévues :

- Lecture de CSV UTF-8 avec séparateur explicite.
- Vérification des colonnes et des valeurs obligatoires.
- Contrôle simplifié du format des adresses e-mail.
- Détection des adresses e-mail dupliquées.
- Diagnostic distinct pour les anomalies de schéma
  et les erreurs bloquantes.
- Rapport HTML et CSV d’anomalies sans copie des valeurs
  des enregistrements sources.

Le traitement est prévu pour fonctionner localement,
sans appel réseau et sans correction automatique des données.

Les règles détaillées, les limites et les comportements
en cas d’échec sont décrits dans le document
[Comportement attendu de csvcheck](docs/comportement-attendu.md).

## Jeux de référence

Le dossier `tests/` contient des fichiers CSV fictifs
et leurs résultats attendus au format JSON.

| Cas | Résultat attendu |
|---|---|
| Contacts conformes | Aucune anomalie, code 0 |
| Anomalies de données | Quatre anomalies, code 1 |
| Colonne obligatoire absente | Anomalie de schéma, valeurs non évaluées, code 1 |
| CSV malformé | Erreur bloquante, code 2 |

Ces fichiers serviront de base aux tests automatisés.
Ils ne constituent pas encore une suite de tests exécutable.

## Limites du périmètre

La version 0.1 ne prévoit ni lecture de fichiers Excel,
ni interface graphique, ni correction automatique.

Le contrôle des e-mails porte sur un format simplifié :
il ne vérifie pas l’existence des boîtes ou la délivrabilité.

Un diagnostic conforme au profil ne garantit pas l’acceptation
du fichier par tous les outils d’import.

## Licence

Aucune licence de réutilisation n’est définie à ce stade.