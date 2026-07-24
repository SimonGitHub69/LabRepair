# CIE Reader (helper locale)

Console Windows che legge i dati anagrafici dalla CIE tramite lettore PC/SC (es. Bit4id miniLector) usando PACE con CAN.

## Build

```powershell
.\build.ps1
```

Output: `publish\cie_reader.exe`

Richiede .NET SDK 8+ e runtime .NET installato sulla macchina.

## Uso CLI (solo se Django e lettore sono sullo stesso PC)

```text
cie_reader.exe --can 123456 [--timeout 20]
```

Stdout: JSON con i campi anagrafici. Exit code 0 = ok.

## Agent per PC client (consigliato)

Se LabRepair gira su un **server** e il Bit4id è collegato a un **PC client**, sul client deve girare l'agent:

```powershell
.\start_agent.ps1
# oppure:
.\publish\cie_reader.exe --serve
```

L'agent ascolta su `http://127.0.0.1:17345` (solo locale):

- `GET /health` → stato
- `POST /read` con body `{"can":"123456"}` → dati anagrafici

Il browser della pagina Anagrafica chiama prima l'agent locale (dove è il lettore), poi eventualmente l'endpoint Django.

### Installazione su ogni PC cassa/banco

1. Copia la cartella `tools\cie_reader\publish` sul PC (o usa la copia già nel progetto)
2. Installa [.NET 8 Desktop Runtime](https://dotnet.microsoft.com/download/dotnet/8.0) se manca
3. Collega il Bit4id e verifica che Windows lo veda (Gestione dispositivi → Lettori smart card)
4. Avvia `start_agent.ps1` (o aggiungilo all'avvio di Windows)
5. Apri LabRepair nel browser, Anagrafica → Leggi CIE

Opzioni agent:

```text
cie_reader.exe --serve [--port 17345] [--timeout 20]
```

## Dipendenze

Codice SDK basato su [italia/cie-mrtd-dotnet-sdk](https://github.com/italia/cie-mrtd-dotnet-sdk) (vendored in `vendor/CIE.MRTD.SDK`).
