# bluelink-hyundai-siri

Controlla la tua Hyundai (ibrida EU) con Siri tramite un server HTTP su Synology NAS.

---

## Come funziona

Dal 14/10/2026 Hyundai blocca i refresh token esterni. Da `hyundai-kia-connect-api` ≥ 4.35.3 il login EU funziona con **email e password** (senza OTP), quindi non serve più nessun token da rinnovare. Questo progetto:

1. Avvia un server Flask su Docker nel NAS, che fa login con email e password
2. Espone endpoint HTTP protetti da una **chiave segreta** (`API_KEY`)
3. Gli endpoint sono chiamati dalle Siri Shortcuts

---

## Requisiti

- Hyundai con Bluelink EU attivo (testato su Tucson Full Hybrid 2024)
- NAS Synology con Docker (testato su DS218+, DSM 7.2)
- iPhone con app Comandi
- Router con port forwarding (es. FritzBox)
- Synology DDNS configurato

---

## Step 1 — Configura il server sul NAS

Crea la cartella `/volume1/docker/bluelink-server` in File Station e carica `app.py` e `Dockerfile`.

Le credenziali **non** stanno nel codice: vanno in un file `bluelink.env` creato sul NAS. Via SSH, una riga alla volta (password con `!` va bene, tra apici singoli):

```bash
cd /volume1/docker/bluelink-server
echo 'BLUELINK_USERNAME=tua_email@email.com' > bluelink.env
echo 'BLUELINK_PASSWORD=LA_TUA_PASSWORD' >> bluelink.env
echo 'BLUELINK_PIN=IL_TUO_PIN' >> bluelink.env
echo 'API_KEY=UNA_CHIAVE_SEGRETA_LUNGA' >> bluelink.env
cat bluelink.env
```

Build e avvio:

```bash
sudo docker build --no-cache -t bluelink-server .
sudo docker run -d --name bluelink-server --restart unless-stopped -p 8765:8765 --env-file bluelink.env bluelink-server
```

Test (senza chiave deve rispondere 401 "Non autorizzato"):

```bash
curl "http://192.168.1.200:8765/status?key=UNA_CHIAVE_SEGRETA_LUNGA"
```

> ℹ️ Il Dockerfile usa `python:3.12-slim`: la libreria ≥ 4.35 richiede Python ≥ 3.12 (con 3.11 pip installerebbe una versione vecchia).

> ℹ️ Righe molto lunghe incollate nel terminale del NAS possono troncarsi: per questo si usa `--env-file`.

---

## Step 2 — Port forwarding

Sul router aggiungi una regola:
- Porta esterna: **8765**
- Porta interna: **8765**
- IP dispositivo: IP locale del NAS (es. 192.168.1.200)

---

## Endpoint disponibili

Ogni chiamata richiede la chiave: `?key=API_KEY` in fondo all'URL oppure header `X-API-Key`. Senza chiave → 401.

| Endpoint | Descrizione |
|---|---|
| `GET /status` | Stato auto (locked, odometer, engine, climate) |
| `GET /lock` | Blocca le portiere |
| `GET /unlock` | Sblocca le portiere |
| `GET /location` | Posizione GPS |
| `GET /windows/open` | Apri tutti i finestrini |
| `GET /windows/close` | Chiudi tutti i finestrini |
| `GET /windows/ventilation` | Finestrini socchiusi |

> ℹ️ I comandi hanno un cooldown di **30 secondi** per evitare errori "Duplicate request" dall'API Hyundai.

> ℹ️ Funzioni **non disponibili** su Tucson Full Hybrid: avvio remoto, climatizzatore remoto, apertura/chiusura baule e tettuccio.
> Baule e tettuccio si possono solo **leggere** (aperto/chiuso): la libreria non ha comandi per azionarli e i server Hyundai non li offrono per questo modello (nemmeno l'app MyHyundai). Clonare il segnale del telecomando non funziona: usa codici variabili (rolling code).

---

## Step 3 — Siri Shortcuts (iOS 26)

Per ogni comando crea una Shortcut nell'app **Comandi**:

1. **+** in alto a destra
2. Aggiungi azione → cerca **"Ottieni dettagli di rete"** → seleziona **Nome rete** → **Wi-Fi**
3. Aggiungi azione → cerca **"Se"**
4. Tocca **Condizione** → scegli **"Dettagli rete"** → **è** → `NomeTuaReteWiFi`
5. Nel ramo **Se**: aggiungi **URL** → `http://192.168.1.200:8765/lock?key=API_KEY` → poi aggiungi **"Ottieni contenuti dell'URL"**
6. Nel ramo **Altrimenti**: aggiungi **URL** → `http://tuonome.synology.me:8765/lock?key=API_KEY` → poi aggiungi **"Ottieni contenuti dell'URL"**
7. Salva con un nome naturale tipo **"Blocca Tucson"**

### Shortcut "Posizione Tucson" → Apple Mappe

`/location` restituisce anche `maps_url`, un link pronto per Apple Mappe. Dopo gli step 1–6 (URL `/location?key=API_KEY`), **sotto "Fine Se"** aggiungi:

1. **"Ottieni valore dizionario"** → Ottieni **Valore** per `maps_url` in **Risultato Se**
2. **"Apri URL"** (icona freccia ↗ — non l'azione "Dizionario")

> ℹ️ Alla prima esecuzione iOS chiede il permesso di accedere alla rete Wi-Fi — scegli **"Consenti sempre"**.

> ℹ️ In iOS 26 Siri trova la Shortcut automaticamente per nome — dì solo "Blocca Tucson" senza configurazione aggiuntiva.

### Frasi Siri suggerite

| Shortcut | Frase |
|---|---|
| Blocca Tucson | "Blocca Tucson" |
| Sblocca Tucson | "Sblocca Tucson" |
| Stato Tucson | "Stato Tucson" |
| Posizione Tucson | "Dov'è la Tucson" |
| Apri finestrini | "Apri i finestrini" |
| Chiudi finestrini | "Chiudi i finestrini" |
| Ventilazione | "Ventilazione Tucson" |

---

## Aggiornare il server

Dopo aver caricato un nuovo `app.py` o `Dockerfile`, via SSH una riga alla volta:

```bash
cd /volume1/docker/bluelink-server
sudo docker rm -f bluelink-server
sudo docker build --no-cache -t bluelink-server .
sudo docker run -d --name bluelink-server --restart unless-stopped -p 8765:8765 --env-file bluelink.env bluelink-server
```

Per cambiare password o chiave basta modificare `bluelink.env` e rifare `rm -f` + `run` (senza build).

---

## Crediti

- [Hyundai-Kia-Connect/hyundai_kia_connect_api](https://github.com/Hyundai-Kia-Connect/hyundai_kia_connect_api)
