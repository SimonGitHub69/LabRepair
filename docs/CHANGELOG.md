# LabRepair

## Changelog

Tutte le modifiche importanti del programma sono documentate in questo file.

Il formato segue le linee guida di Keep a Changelog.
La versione corrente è nel file `VERSION` e compare in sidebar, piè di pagina, login e Sistema.

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