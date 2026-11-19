# csvcheck

Outil Python en cours de développement pour contrôler localement
des fichiers CSV de contacts avant leur import dans un autre outil.

## Objectif

Détecter les problèmes de structure et les anomalies de données,
sans modifier le fichier source.

Le projet privilégie des diagnostics explicites, des résultats
reproductibles et la préservation des valeurs d’origine.

## État du projet

Un lecteur CSV est implémenté et couvert par des tests automatisés.

Il vérifie la structure des fichiers, conserve les valeurs
et leurs références de lignes, et rejette les entrées invalides
couvertes par les tests.

Il contrôle la taille du fichier à l’ouverture ainsi que
la longueur des champs décodés. Le contrôle à l’ouverture
ne protège pas contre un fichier qui grossit pendant la lecture.

Le profil contacts-v1 vérifie les colonnes et valeurs obligatoires,
le format simplifié des e-mails et leurs doublons.

La validation produit des anomalies ordonnées et des compteurs.
Lorsque des colonnes obligatoires sont absentes, les valeurs
sont indiquées comme non évaluées.

Une couche applicative orchestre la lecture et la validation.
Elle distingue une analyse terminée, avec ou sans anomalies,
d’une analyse impossible. Seule l’erreur de syntaxe CSV est
convertie en résultat typé ; les autres erreurs du lecteur
restent des exceptions techniques.

La commande CLI et la génération des rapports ne sont pas
encore implémentées.

Aucune commande d’analyse destinée à l’utilisateur n’est
disponible à ce stade.

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

Les jeux de référence sont utilisés par les tests automatisés
du lecteur, de la validation métier et de la couche applicative.

Les anomalies, les statuts de validation et les compteurs
sont comparés aux résultats attendus.

Les codes de retour et les rapports ne sont pas encore
vérifiés par cette suite.

## Limites du périmètre

La version 0.1 ne prévoit ni lecture de fichiers Excel,
ni interface graphique, ni correction automatique.

Le contrôle des e-mails porte sur un format simplifié :
il ne vérifie pas l’existence des boîtes ou la délivrabilité.

Un diagnostic conforme au profil ne garantit pas l’acceptation
du fichier par tous les outils d’import.

## Licence

Aucune licence de réutilisation n’est définie à ce stade.