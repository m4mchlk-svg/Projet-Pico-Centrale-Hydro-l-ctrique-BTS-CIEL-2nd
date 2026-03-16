# ******************************************************************
#   PROJET BTS CIEL 2026 - Pico-centrale hydroélectrique
#   Module LoRa E32-900T30D / barrage sur ESP32 VROOM 32U  
#   By OH  - Mars / 2026   -    Version 1.0
# ******************************************************************

Ce fichier contient la classe `LoRaE32` qui permet d'instancier des objets permettant de programmer le module LoRa E32-900T30D. Il doit être stocké dans la mémoire de l'ESP32. Les versions pour le pupitre et pour le barrage sont identiques. Il n'y a que l'adresse initiale du module qui change.

### Adresses des modules
* **LoRaE32-Barage.py** : adresse module LoRa `0x0000`
* **LoRaE32-pupitre.py** : adresse module LoRa `0x0001`

---

### Configuration par défaut
* **HEAD** : 0xC0
* **ADDR_H** : 0x00
* **ADDR_L** : 0x01 (adresse du pupitre)
* **SPED** : 0x1F (9600bps 8N1)
* **CHANNEL** : 6 (fréquence 868 MHz)
* **OPTION** : 0xC0 (Puissance max, mode fixe point à point)

---

### Méthodes de la classe LoRaE32

| Méthode | Description |
| :--- | :--- |
| `begin()` | Initialise le module en mode normal (M0=0, M1=0). |
| `send_data(addr_h, addr_l, chan, data)` | Envoie un paquet (adresse destination + canal + données) en mode normal. |
| `get_data()` | Récupère les données reçues sur l'UART si disponibles. |
| `set_config(save=True)` | Applique la configuration actuelle au module. Option de sauvegarde en Flash. |
| `get_configuration()` | Interroge le module pour lire sa configuration actuelle. |
| `send_command(command)` | Envoie une commande spécifique en forçant le mode CONFIG (Mode 3). |

---

### Matériel (Pins)
Le pilotage nécessite la configuration des broches suivantes :
* **UART** : Communication série.
* **M0 / M1** : Gestion matérielle des modes (Normal, Config, etc.).
* **AUX** : Monitoring de l'état (prêt / occupé).

**By OH - Mars / 2026 - Version 1.0**
