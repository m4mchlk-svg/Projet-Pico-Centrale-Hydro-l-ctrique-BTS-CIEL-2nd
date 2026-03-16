# PROJET BTS CIEL 2026 - Pico-centrale hydroélectrique
## Module LoRa E32-900T30D / pupitre sur ESP32 WROOM 32U

Ce projet contient la classe `LoRaE32` en **MicroPython** permettant d'instancier des objets pour programmer et utiliser le module LoRa E32-900T30D. Les versions pour le pupitre et pour le barrage sont identiques, seule l'adresse initiale change.

### Configuration des adresses
* **LoRaE32-Barage.py** : adresse module LoRa `0x0000`
* **LoRaE32-pupitre.py** : adresse module LoRa `0x0001`

---

### Caractéristiques de la classe
La classe gère la configuration matérielle et logicielle du module via l'UART et les broches de contrôle.

#### Paramètres par défaut (Config)
* **HEAD** : 0xC0
* **ADDR_H / ADDR_L** : Configuration de l'adresse (ex: 0x00 0x01)
* **SPED** : 9600bps 8N1 (0x1F)
* **CHANNEL** : 6 (Fréquence 868 MHz)
* **OPTION** : Puissance max, mode fixe point à point (0xC0)

---

### Méthodes disponibles

| Méthode | Description |
| :--- | :--- |
| `begin()` | Initialise le module en mode normal (M0=0, M1=0). |
| `send_data(addr_h, addr_l, chan, data)` | Envoi de paquets en mode adressé (Transmission fixe). |
| `get_data()` | Lecture des données reçues sur l'UART. |
| `set_config(save=True)` | Envoie les paramètres de configuration au module (Mode 3). |
| `get_configuration()` | Interroge le module pour récupérer ses paramètres actuels. |
| `send_command(command)` | Envoie une commande spécifique en mode configuration. |

---

### Contrôle Matériel (Pins)
Le programme utilise les broches suivantes pour piloter le module :
* **M0 & M1** : Gestion des modes de fonctionnement (Normal, Wake-up, Power-saving, Config).
* **AUX** : Monitoring de l'état du module (disponibilité et fin de transmission).
* **UART (TX/RX)** : Communication série des données et commandes.

---

### Installation
Le fichier de classe doit être stocké dans la mémoire Flash de l'**ESP32**. 



**By OH - Mars 2026 - Version 1.0**
