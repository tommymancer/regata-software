# Aquarela — Runbook diagnostico

Guida per Claude: come diagnosticare problemi su un Pi remoto usando i dati che il cliente manda via Telegram.

## Regola fondamentale

Le UNICHE azioni che puoi chiedere al cliente sono:
- **Premere bottoni nell'app** (Diagnostica, CAN Dump, BLE Scan, Aggiorna Pi da GitHub)
- **Azioni fisiche** (riaccendi sensore, controlla cavo, riavvia il Pi staccando e riattaccando l'alimentazione)

MAI suggerire: SSH, terminale, comandi, modifica file, configurazioni manuali. Il cliente non ha accesso tecnico e non deve averlo.

## Flusso operativo

1. Cliente scrive su Telegram descrivendo il problema
2. Claude chiede: "apri l'app Aquarela, vai su Impostazioni e premi **Diagnostica**, poi condividi il risultato qui"
3. Claude legge il report e identifica il problema
4. Se serve più info: "premi **CAN Dump**" o "premi **BLE Scan**" e condividi
5. Claude risponde con la soluzione (bottone nell'app o azione fisica)

## Registro barche

Il file `~/.claude/boats.json` contiene l'elenco delle barche e i `telegram_chat_id` associati.

## Diagnosi per sintomo

### "Non vedo dati" / "schermo vuoto"

1. Chiedi Diagnostica → guarda `sensor_ages_ms`
2. Se tutti i sensori hanno age alto → il Pi non riceve dati dal bus
   - "Controlla che la rete NMEA sia alimentata (interruttore strumenti)"
   - "Controlla che il cavo NMEA 2000 sia collegato al Pi"
3. Se solo un sensore ha age alto → quel sensore specifico non trasmette
   - "Il sensore [X] non sta trasmettendo. Controlla che sia acceso e collegato"
4. Se non capisci → chiedi CAN Dump per vedere cosa c'è sul bus

### "Il vento non funziona" / "dati vento sbagliati"

1. Chiedi Diagnostica → guarda `sensor_ages_ms.wind`
   - Se age alto: il sensore vento non trasmette
   - Per vento CAN: "Controlla che il sensore vento sia acceso"
   - Per Calypso BLE: chiedi BLE Scan → controlla se "ULTRASONIC" appare
     - Non appare → "Il Calypso potrebbe essere scarico o spento"
     - Appare con RSSI basso (< -85) → "Prova ad avvicinare il Pi al sensore"
2. Se il sensore trasmette ma i dati sembrano sbagliati:
   - Chiedi CAN Dump → guarda PGN 130306 (Wind Data)
   - Se ci sono 2+ source address per PGN 130306 → conflitto sorgenti
   - La calibrazione vento si aggiusta automaticamente — NON suggerire mai di cambiarla

### "La bussola sembra sbagliata"

- La calibrazione bussola si aggiusta automaticamente via tack symmetry
- NON suggerire mai di cambiare calibrazioni manualmente
- Se persiste dopo diverse virate: potrebbe essere un problema hardware
  - Chiedi CAN Dump → guarda PGN 127250 (Vessel Heading) → controlla frequenza

### "Dashboard non si apre" / "app non si connette"

1. "Sei connesso alla rete WiFi Aquarela?"
2. "Prova a chiudere e riaprire l'app"
3. Se ancora non funziona: "Prova a riavviare il Pi staccando e riattaccando il cavo di alimentazione"
4. Se dopo il riavvio non funziona: "Vai su Impostazioni e premi Aggiorna Pi da GitHub"

### "Sessioni fantasma" / "sessioni da 0 nm"

- Le sessioni si avviano automaticamente quando la barca si muove (>1.5 kt per 30 secondi)
- Sessioni corte spurie possono capitare con corrente forte in porto
- Non è un problema critico, si possono ignorare

### "Disco pieno"

1. Chiedi Diagnostica → guarda `disk_free_mb`
2. Se < 500 MB: "Dall'app, vai in Sessioni e cancella le sessioni vecchie"
3. Il Pi cancella automaticamente le sessioni > 90 giorni

### Bug software / comportamento strano

1. Chiedi Diagnostica → leggi i log per capire l'errore
2. Se è un bug: Claude fixa il codice e pusha su GitHub
3. "Vai su Impostazioni e premi **Aggiorna Pi da GitHub**"
4. Dopo l'aggiornamento: "Premi **Diagnostica** e condividi qui per verificare"
5. Controlla `version.sha` nel nuovo report

## Cose da NON fare MAI

- NON suggerire SSH, terminale, o comandi
- NON suggerire di modificare file di configurazione
- NON suggerire di cambiare calibrazioni manualmente (il sistema si auto-calibra)
- NON usare linguaggio tecnico inutile — parla come un meccanico di barche, non un programmatore
