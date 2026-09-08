# LabRepair

## Changelog

Tutte le modifiche importanti del programma sono documentate in questo file.

Il formato segue le linee guida di Keep a Changelog.
La versione corrente è nel file `VERSION` e compare in sidebar, piè di pagina, login e Sistema.

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