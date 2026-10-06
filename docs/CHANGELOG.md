# LabRepair

## Changelog

Tutte le modifiche importanti del programma sono documentate in questo file.

Il formato segue le linee guida di Keep a Changelog.
La versione corrente è nel file `VERSION` e compare in sidebar, piè di pagina, login e Sistema.

---

# [0.9.31] - 2026-10-06

## Aggiunto

- Riparazione con busta stampata: **Modifica Cliente** aggiorna solo telefono, cellulare ed email. Nome e cognome restano invariati.

---

# [0.9.30] - 2026-10-02

## Corretto

- Riparazioni in stato Evasa: testata Accettazione bloccata come dopo stampa busta (lucchetto, campi non modificabili).

---

# [0.9.29] - 2026-10-02

## Corretto

- Eliminazione foto riparazione: conferma obbligatoria prima della rimozione (dialogo Elimina/Annulla).

---

# [0.9.28] - 2026-10-02

## Corretto

- Produzione Windows: le foto e gli allegati in `/media/` vengono serviti anche con `DEBUG=False` (`SERVE_MEDIA=True`).
- Logo sidebar LabRepair riallineato (stesse misure/DPI del logo negozio che risultava leggibile).

## Modificato

- Installer server Windows: download automatico di Python e PostgreSQL se mancanti; messaggio ALLOWED_HOSTS con IP di rete; installazione servizio più robusta.

---

# [0.9.26] - 2026-09-22

## Modificato

- Salvataggio riparazione: telefono e/o cellulare inseriti sulla scheda aggiornano anche l’anagrafica cliente collegata.

---

# [0.9.25] - 2026-09-18

## Aggiunto

- Ordinamento colonne su tutte le liste (click sull’intestazione, asc/desc; preservato con filtri e paginazione).

## Corretto

- Stampa busta/Privacy: annullare la maschera «telefono mancante» non mostra più un errore di stampa; su nuova riparazione la maschera compare anche da «Stampa busta».
- Stampa busta: la conferma telefono non resta più nascosta sotto il modal (blocco su «Preparazione busta…»).
- Stampa busta: codice a barre come immagine PNG (non più solo font), così compare anche in stampa tramite agent.
- Stampa busta: barcode più stretto (barre più dense).
- Stampa busta: barcode allineato in larghezza al codice pratica sopra.
- Stampa busta: nel barcode il trattino del codice non viene stampato (es. P26-0039 → P260039).

---

# [0.9.24] - 2026-09-17

## Modificato

- Salvataggio riparazione senza telefono/cellulare: non è più bloccante; compare una maschera per **Inserisci telefono** oppure **Forza salvataggio**.
- Errori di validazione in scheda riparazione: messaggio mostrato **accanto al campo**, non più come alert in alto «Salvataggio non eseguito».
- Layout: ridotto lo spazio tra navbar e titolo pagina in tutte le finestre.

---

# [0.9.23] - 2026-09-17

## Aggiunto

- Stampa busta: con priorità **Urgente**, solo sulla parte B compare **URGENTE** in un box rosso centrato tra date e barcode, leggermente ruotato (stile timbro).

## Modificato

- Creazione DDT / bolla centro assistenza: se la riparazione è in **Accettazione**, passa a **dal Riparatore**; se **Data riparatore** è vuota, viene impostata alla data della bolla.

## Corretto

- Elenco riparazioni e ricerca clienti: la ricerca ignora gli **accenti** (es. `Filie` trova `Filiè`).

---

# [0.9.22] - 2026-09-17

## Corretto

- Sync pagamenti cassa: all'apertura scheda/modifica la lettura avviene **prima** del render (con messaggio se aggiorna); in elenco controlla anche Accettazione / Riparatore / Non ritirata, non solo In consegna.

---

# [0.9.21] - 2026-09-17

## Modificato

- **Nuova riparazione + prezioso** con documento scaduto: non blocca più il lavoro; al Salva (o alla selezione cliente) si può scegliere **Forza registrazione** oppure aggiornare il documento.

---

# [0.9.20] - 2026-09-17

## Corretto

- **Data prevista consegna** retroattiva: blocca il Salva **solo** in **Nuova riparazione**; in modifica di una scheda già esistente non è mai bloccante.
- Modifica scheda: al click su Salva la data consegna retroattiva **non viene più svuotata** dal controllo JS (prima il `change` sul campo data la azzerava e poi la validazione la trovava vuota).
- Salva scheda: **non azzera** più i dati già memorizzati (N. scontrino, prezzo pagato, data vendita/evasione, data apertura, data consegna) se il POST arriva vuoto o la sync cassa ha aggiornato il DB dopo l'apertura della maschera.
- Click su Salva/Annulla: evita lo spostamento della maschera per blur sui campi data/nome che costringeva a ripremere.

---

# [0.9.19] - 2026-09-17

## Aggiunto

- Sync pagamenti da **Database Cassa** (`GS_VENDITE_DETTAGLIO`): se `ID_ARTICOLO` coincide con il codice riparazione, aggiorna **Prezzo pagato**, **N. scontrino**, **Data vendita/evasione** e imposta stato **Evasa** (se non lo era già).
- Controllo automatico all'apertura elenco / scheda riparazione; comando `manage.py sync_pagamenti_cassa` per batch/cron.

## Modificato

- Elenco DDT filtrato per negozio di lavoro (come le riparazioni).
- Salva riparazione e elenco non restano più in attesa delle sync MS-SQL/cassa (eseguite in background).
- Salva riparazione: feedback «Salvataggio…», anti doppio-click, sblocco automatico su timeout; apertura scheda non blocca più su MS-SQL.
- Documento scaduto: blocca il Salva **solo** in **Nuova riparazione** con tipologia **prezioso**; in modifica o non prezioso viene solo segnalato.

---

# [0.9.18] - 2026-09-17

## Modificato

- Client Windows: durante l'auto-update mostra una **finestra di avanzamento** (download %, estrazione, installazione).
- Client Windows: all'inizio dell'aggiornamento chiude le finestre LabRepair già aperte **senza** il dialogo "Leave app?".
- Modalità app: nel menu laterale non compare più l'indirizzo del server in basso a sinistra al passaggio sulle voci.

---

# [0.9.14] - 2026-09-16

## Aggiunto

- Tabella **Negozi** (menu Parametri): CRUD sedi con prefisso riparazione, località privacy, **sede operativa** e **numerazione DDT indipendente** per negozio.
- DDT: possibilità di aggiungere **numeri busta** anche non collegati al centro assistenza (con o senza trattino nel codice).

## Modificato

- La numerazione DDT usa il negozio di sessione (sezionale e progressivo per sede).
- Stampa DDT: sede operativa in intestazione, tipografia Arial, fincatura più leggera, box destinazione merce regolato.
- Stampa DDT: stampa dalla scheda/elenco **senza cambiare pagina**; Annulla nel dialogo di stampa più reattivo.

---

# [0.9.13] - 2026-09-16

## Aggiunto

- CRUD completo sui **DDT**: modifica (buste e dati trasporto) ed eliminazione con sblocco delle buste.
- Client Windows: a ogni avvio controlla sul server se c'è una versione più recente e, se disponibile lo zip in `installazione/`, aggiorna in automatico.
- API pubbliche `/api/client/version/` e `/api/client/download/` per l'auto-update dei PC client.

## Modificato

- Stampa DDT: contenuto abbassato di **2 mm** per evitare taglio in alto.

---

# [0.9.12] - 2026-09-15

## Aggiunto

- Parametri programma: **Numerazione DDT iniziale** per gestire il progressivo (es. partire da 100 → `100/R`).
- Alla creazione DDT, su ogni busta inclusa vengono registrati **N. DDT** e **Data DDT** (visibili in scheda riparazione).

---

# [0.9.11] - 2026-09-15

## Aggiunto

- Gestione **DDT** (Documenti di Trasporto) per centri assistenza: elenco, creazione e stampa PDF.
- Nuovo DDT: selezione centro assistenza, proposta automatica delle **buste aperte** (riparazioni non chiuse e non già in un DDT), dati destinatario dall'anagrafica.
- Numerazione con sezionale configurabile (es. **100/R**), data odierna, causale/aspetto/vettore predefiniti in Parametri programma.
- Voce di menu **DDT** in Gestione.

---

# [0.9.10] - 2026-09-15

## Aggiunto

- Parametri PC: **Grafica ad alto contrasto** (testo più grande, contrasto maggiore, valori in blu grassetto) solo su **Anagrafiche** e **Riparazioni**.
- Scheda riparazione: dopo la selezione del cliente la ricerca si nasconde; **Cambia cliente** la riapre se serve correggere.
- Documento scaduto in modifica riparazione: resta evidenziato (badge **Scaduto**), sezione **compattabile** e chiusa di default.
- Stesso comportamento per **Anagrafica completa cliente** (badge Doc. scaduto, Apri/Chiudi, chiusa di default).
- In riparazione **preziosa**, con cliente selezionato, anagrafica e documento partono sempre **compattati** (Apri per espandere); se il documento è scaduto resta l’evidenza.
- Data prevista consegna: non si accettano più date precedenti a oggi (né in modifica lasciando invariata una data passata).
- Data prevista consegna: blocco immediato in uscita dal campo / calendario (messaggio subito, senza attendere Salva).
- Scheda riparazione: **Nuovo cliente** si apre in una maschera sopra la riparazione; alla chiusura si torna alla scheda (e se salvato il cliente viene selezionato).
- Anagrafica cliente: **Conferma** e **Annulla** usano gli stessi tasti della scheda riparazione (Parametri PC).
- Data di nascita: formato **gg/mm/aaaa** (anno a 4 cifre).
- Data di nascita: controllo di coerenza sull'età (non futura; avviso se **inferiore a 6 anni** o **oltre 100**).
- Nuovo cliente: all'apertura il cursore va sul campo **Cognome**.
- Parametri Sistema (MS-SQL): campo **Database Cassa** per la lettura degli scontrini (oltre al Database prezzi).
- Parametri SQL: occhiolino per **mostrare/nascondere** la password (solo utenti amministratore / superuser).
- Parametri programma: rimosso **Stile grafica maschere** (resta impostabile per PC in Parametri PC).
- Parametri PC: scorciatoie **Riparatore** (default F6) e **Tipo oggetto** (default F7) per portare il focus sui campi in scheda riparazione; abbreviazione mostrata sull'etichetta.
- Scorciatoia **Salva** (Parametri PC): attiva su tutte le maschere di modifica (tabelle, anagrafiche, parametri), non solo riparazione.

## Corretto

- Elenco riparazioni: filtro **Cliente** — il menu a tendina resta visibile sopra l'elenco; digitando un nome e premendo Filtra/Invio senza selezione si cerca comunque; i select applicano subito il filtro.
- Elenco riparazioni: ricerca filtro **Cliente** limitata ai clienti che hanno almeno una riparazione (e al negozio selezionato), non all'intera anagrafica.
- Icona calendario dei campi data: il selettore nativo si riapre (non restava più bloccato da readonly antifill e dal focus sul testo).
- Maschera **Nuovo cliente** in riparazione: la scheda si apre davvero nell’overlay (non restava più pagina vuota) e **Conferma** seleziona il cliente e torna alla riparazione.
- Scheda riparazione: **Annulla** non richiede più due pressioni (il blur su nome/date non marca più a torto «modifiche non salvate» né blocca il click).

---

# [0.9.9] - 2026-09-11

## Corretto

- Modalità App: navigazioni interne (stampa busta, cambio pagina, back, `location.assign`) non fanno più logout né chiedono «Uscire dall'app?». Il logout resta solo alla chiusura della finestra.

## Modificato

- Liste riparazioni/anagrafiche: i link di paginazione tengono la scelta **Righe** anche se arriva dalla sessione.
- Parametri PC: opzioni stampa busta raggruppate in un’unica sezione.
- Date documento scaduto in stampa Privacy allineate al formato giorno/mese/anno a 2 cifre.

---

# [0.9.8] - 2026-09-10

## Modificato

- Stampa busta: **Salva scheda** e **Torna all'elenco** si impostano in Parametri PC (non più nel dialogo di stampa).
- Stampa busta: con salvataggio attivo, la scheda viene salvata **prima** dell'anteprima così mostra le modifiche appena fatte.
- Scheda riparazione: flag **Senza spesa** spostato sotto **Prezzo al Pubblico**.
- Stato «In consegna»: messaggio e controllo su **Prezzo al Pubblico** oppure **Senza Spesa** (non più sul costo totale).
- Scheda riparazione: **Stato** e **Priorità** spostati nella card Oggetto.
- Non viene più mostrato il messaggio «Prezzo cassa aggiornato…» dopo il salvataggio (restano gli avvisi se la sync fallisce).

---

# [0.9.7] - 2026-09-09

## Aggiunto

- Non si può eliminare un cliente (o centro assistenza) se ha riparazioni collegate.

## Modificato

- In scheda riparazione, **Riparatore** è il primo campo della card Oggetto.
- Stampa/salva busta: non fallisce più con «Cliente: scelta non valida» se il cliente collegato non è più nell'elenco attivo.
- Liste: la scelta «Righe» (10/20/50/100) resta memorizzata per la sessione.
- Stampa busta: opzioni **Salva la scheda** e **Torna all'elenco**; di default in modifica si resta sulla riparazione.

---

# [0.9.6] - 2026-09-09

## Modificato

- Messaggio «Prezzo cassa aggiornato»: non si accumula più; resta solo l'ultimo.

---

# [0.9.5] - 2026-09-09

## Modificato

- Stampa busta: se l'agent stampanti non risponde, compare **Stampa dal browser** (non serve più premere due volte Stampa).
- PC client: LabRepairApp consente a Chrome/Edge l'accesso all'agent stampanti su 127.0.0.1 (server in LAN).
- Agent stampanti: `/health` indica versione ed endpoint (incluso `/print`); messaggio 404 più chiaro.
- Installazione client: prima di copiare i file, ferma agent CIE e stampanti se già in esecuzione.

---

# [0.9.4] - 2026-09-09

## Modificato

- Aprendo una riparazione dalla lista, documento di identità scaduto: evidenziato in scheda (badge/alert), senza dialog.
- Date in interfaccia in formato giorno/mese/anno a 2 cifre (es. 08/09/26).
- Data prevista consegna: non accettata se precedente a oggi (il valore già salvato resta valido se invariato).
- Su TB_PREZZICASSE, PRZ_EAN usa il codice riparazione senza trattino (es. P26-0026 → P260026).

---

# [0.9.3] - 2026-09-08

## Modificato

- In modalità App: cambio righe per pagina (10/20/50/100) non mostra più «Uscire dall'app?».

---

# [0.9.2] - 2026-09-07

## Modificato

- In scheda riparazione (Stato a radio): Priorità non si sovrappone più a Stato stringendo la maschera.
- Per oggetti preziosi il peso è obbligatorio solo se è selezionato il tipo di metallo.
- Ordine campi: Tipo di metallo prima del Peso.
- Su peso e importi, al focus il valore è selezionato (digitando si sostituisce invece di aggiungere in coda).
- In modalità App: clic su Riparazioni / Anagrafiche / menu non mostra più «Uscire dall'app?».

---

# [0.9.1] - 2026-09-06

## Aggiunto

- In Nuova Riparazione: pulsante **Stampa busta + Salva** (salva e stampa secondo il flag «senza anteprima» del PC).
- Documento di identità modificabile dalla scheda riparazione (AJAX sull'anagrafica), con avviso se scaduto; bloccante solo per oggetti preziosi.

## Modificato

- Date della riparazione limitate tra il **2026** e il **2099**.
- Campo **Note** nascosto nella scheda riparazione (i dati già salvati restano in database).
- Messaggi e fallback se l'agent stampanti non è raggiungibile.

---

# [0.9.0] - 2026-09-02

Prima versione LabRepair con numero di versione visibile in applicazione.

## Aggiunto

- Numero di versione del programma, visibile in basso a sinistra, nel piè di pagina, in login e in Sistema.
- Pagina Novità (Sistema) con la cronologia delle modifiche.
- Pacchetto auto-installante per PC client Windows (app, agent CIE, agent stampanti).

---

# [0.2.0-alpha] - 2026-07-07

## 🎉 Architettura

- Creata la struttura definitiva del progetto.
- Configurato Django 6.
- Configurato PostgreSQL.
- Inizializzato repository Git.

## Core

- Creato BaseModel.
- Creato BaseAdmin.
- Creato BaseForm.
- Definita la struttura delle applicazioni.

```
apps/
├── accounts/
├── agenda/
├── anagrafiche/
├── core/
├── dashboard/
└── pratiche/
```

## Frontend

Installati:

- Tabler
- Bootstrap 5
- HTMX
- Alpine.js

## Layout

Realizzati:

- layout.html
- sidebar.html
- navbar.html
- footer.html
- messages.html

## Dashboard

- Creata Dashboard iniziale.
- Creato componente KPI (`stats_card.html`).
- Predisposto caricamento dati tramite `get_context_data()`.

## Static

Organizzazione definitiva:

```
static/
└── securtek/
    ├── css/
    ├── js/
    ├── img/
    ├── fonts/
    └── icons/
```

## UI

- Sidebar personalizzata.
- Navbar personalizzata.
- Inizio Design System SECURTEK.

## Refactoring

- Riorganizzati i template.
- Preparata la struttura per componenti riutilizzabili.

---

# [0.3.0-alpha] (In sviluppo)

## Previsto

- Dashboard professionale
- Tabelle
- Form
- Modali
- Tema SECURTEK
- Menu dinamico

---

# [0.4.0-alpha] (Pianificato)

## Core

- Login
- Permessi
- Gruppi
- Audit Log
- Configurazioni

---

# [0.5.0-alpha] (Pianificato)

## Modulo Anagrafiche

- Clienti
- Aziende
- Contatti

---

# [0.6.0-alpha] (Pianificato)

## Modulo Pratiche

- Workflow
- Allegati
- Note
- Stato pratica

---

# [1.0.0]

Prima release stabile.