# Smart Irrigation V2

Intégration Home Assistant pour gérer des zones d'irrigation avec plusieurs pompes et trois modes d'activation automatique.

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![HA Version](https://img.shields.io/badge/Home%20Assistant-%3E%3D2025.8.0-blue)](https://www.home-assistant.io/)

---

## Fonctionnalités

- **Zones d'irrigation** — créez autant de zones que nécessaire (une intégration par zone)
- **Jusqu'à 3 pompes par zone** — chaque pompe a son propre interrupteur HA et son débit en ml
- **3 modes d'activation** :
  - **Manuel** — bouton de déclenchement dans l'interface
  - **Planification** — déclenchement automatique à une heure et des jours configurés
  - **Capteur d'humidité** — déclenchement automatique quand l'humidité du sol passe sous un seuil
- **Arrêt automatique** — les pompes s'éteignent après la durée configurée
- **Suivi du volume** — capteur qui totalise l'eau consommée par zone (ml)
- **Prochain arrosage** — capteur affichant la prochaine irrigation planifiée
- **Paramètres modifiables** — tout peut être reconfiguré via Paramètres → Configurer sans supprimer la zone

---

## Installation via HACS

1. Dans HACS, ouvrir le menu ⋮ → **Dépôts personnalisés**
2. Ajouter l'URL `https://github.com/Hugo22000/smart-irriga-V2` (catégorie : **Intégration**)
3. Rechercher **Smart Irrigation V2** dans HACS et installer
4. Redémarrer Home Assistant

---

## Configuration

La configuration se fait entièrement via l'interface graphique en 4 à 5 étapes :

| Étape | Champs |
|---|---|
| **Zone** | Nom de la zone, nombre de pompes (1–3) |
| **Pompe N** (répété) | Entité switch HA, débit (5–300 ml) |
| **Mode d'activation** | Manuel / Planification / Capteur d'humidité + durée (10–3600 s) |
| **Planification** *(si mode Schedule)* | Heure de déclenchement, jours de la semaine |
| **Capteur d'humidité** *(si mode Humidity)* | Entité capteur HA, seuil d'humidité (0–100 %) |

Pour modifier une zone existante : **Paramètres → Appareils et services → Smart Irrigation V2 → Configurer**

---

## Entités créées par zone

| Type | Nom | Description |
|---|---|---|
| `button` | `[Zone] Start Irrigation` | Déclenche l'arrosage immédiatement (passe outre le mode) |
| `switch` | `[Zone] Pump 1/2/3` | Miroir de l'état de chaque pompe |
| `sensor` | `[Zone] Water Volume` | Volume total d'eau consommée (ml) |
| `sensor` | `[Zone] Next Irrigation` | Prochain arrosage planifié (timestamp) |

Le capteur **Next Irrigation** expose également ces attributs :

| Attribut | Mode |
|---|---|
| `activation_mode` | Tous |
| `schedule_time`, `schedule_days` | Planification |
| `humidity_sensor`, `humidity_threshold` | Capteur d'humidité |

---

## Structure des fichiers

```
custom_components/smart_irriga_v2/
├── __init__.py          # Setup, start_irrigation(), _setup_schedule(), _setup_humidity()
├── config_flow.py       # Wizard de création (ConfigFlow) + modification (PumpOptionsFlow)
├── const.py             # Toutes les constantes (modes, clés de config, valeurs par défaut)
├── sensor.py            # WaterVolumeSensor + IrrigationScheduleSensor
├── switch.py            # IrrigationPumpSwitch (miroir des switchs physiques)
├── button.py            # StartIrrigationButton
├── manifest.json        # Métadonnées de l'intégration
├── strings.json         # Traductions anglaises (base)
└── translations/
    └── fr.json          # Traductions françaises
```

---

## Dépannage

**L'intégration ne charge pas** — vérifier les logs HA (Paramètres → Journaux) et s'assurer que la version HA est ≥ 2025.8.0.

**Les pompes ne s'activent pas** — vérifier que l'entité switch renseignée existe et répond dans HA.

**La planification ne se déclenche pas** — l'heure est vérifiée au second 0 exact ; vérifier que le bon fuseau horaire est configuré dans HA.

**Mise à jour HACS** — après chaque mise à jour, redémarrer HA et recharger l'intégration.

---

## Licence

MIT — voir [LICENSE](LICENSE)
