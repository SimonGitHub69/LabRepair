using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Net;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Threading;
using CIE.MRTD.SDK.EAC;
using CIE.MRTD.SDK.PCSC;

namespace CieReader
{
    internal static class Program
    {
        private const int DefaultAgentPort = 17345;

        private static readonly byte[] KeyFullName = { 0x5F, 0x0E };
        private static readonly byte[] KeyBirthAddress = { 0x5F, 0x11 };
        private static readonly byte[] KeyAddress = { 0x5F, 0x42 };
        private static readonly byte[] KeyCf = { 0x5F, 0x10 };
        private static readonly byte[] KeyMrz = { 0x5F, 0x1F };
        private static readonly byte[] KeyDateIssue = { 0x5F, 0x26 };
        private static readonly byte[] KeyDateExpire = { 0x5F, 0x24 };

        private static readonly object ReadLock = new object();

        private static int Main(string[] args)
        {
            try
            {
                if (HasFlag(args, "--serve") || HasFlag(args, "-s"))
                {
                    int port = ParsePort(args);
                    int timeoutSeconds = ParseTimeout(args);
                    return RunAgent(port, timeoutSeconds);
                }

                string can = ParseCan(args);
                if (string.IsNullOrEmpty(can))
                {
                    Fail("Parametro --can obbligatorio (6 cifre), oppure usa --serve.");
                    return 2;
                }

                int timeout = ParseTimeout(args);
                var data = ReadCie(can, timeout);
                // Output flat per il wrapper Django (apps.anagrafiche.cie.map_cie_payload).
                Console.WriteLine(JsonSerializer.Serialize(data));
                return 0;
            }
            catch (Exception ex)
            {
                Fail(ex.Message);
                return 1;
            }
        }

        private static bool HasFlag(string[] args, string flag)
        {
            for (int i = 0; i < args.Length; i++)
            {
                if (string.Equals(args[i], flag, StringComparison.OrdinalIgnoreCase))
                    return true;
            }
            return false;
        }

        private static string ParseCan(string[] args)
        {
            for (int i = 0; i < args.Length - 1; i++)
            {
                if (args[i] == "--can" || args[i] == "-c")
                    return args[i + 1].Trim();
            }
            return null;
        }

        private static int ParseTimeout(string[] args)
        {
            for (int i = 0; i < args.Length - 1; i++)
            {
                if ((args[i] == "--timeout" || args[i] == "-t") &&
                    int.TryParse(args[i + 1], out int seconds) &&
                    seconds > 0)
                {
                    return seconds;
                }
            }
            return 20;
        }

        private static int ParsePort(string[] args)
        {
            for (int i = 0; i < args.Length - 1; i++)
            {
                if ((args[i] == "--port" || args[i] == "-p") &&
                    int.TryParse(args[i + 1], out int port) &&
                    port > 0 && port < 65536)
                {
                    return port;
                }
            }
            return DefaultAgentPort;
        }

        /// <summary>
        /// Agent locale: il browser del PC con il Bit4id chiama http://127.0.0.1:port
        /// così la lettura PC/SC avviene sul client, non sul server Django.
        /// </summary>
        private static int RunAgent(int port, int timeoutSeconds)
        {
            string prefix = $"http://127.0.0.1:{port}/";
            var listener = new HttpListener();
            listener.Prefixes.Add(prefix);
            try
            {
                listener.Start();
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine(
                    $"Impossibile avviare l'agent CIE su {prefix}: {ex.Message}");
                return 1;
            }

            Console.WriteLine($"CIE agent in ascolto su {prefix}");
            Console.WriteLine("Endpoint: GET /health  POST /read  (Ctrl+C per uscire)");

            while (true)
            {
                HttpListenerContext context;
                try
                {
                    context = listener.GetContext();
                }
                catch (HttpListenerException)
                {
                    break;
                }

                ThreadPool.QueueUserWorkItem(_ => HandleAgentRequest(context, timeoutSeconds));
            }

            return 0;
        }

        private static void HandleAgentRequest(HttpListenerContext context, int timeoutSeconds)
        {
            HttpListenerRequest request = context.Request;
            HttpListenerResponse response = context.Response;
            try
            {
                AddCorsHeaders(request, response);

                if (string.Equals(request.HttpMethod, "OPTIONS", StringComparison.OrdinalIgnoreCase))
                {
                    response.StatusCode = 204;
                    response.Close();
                    return;
                }

                string path = (request.Url?.AbsolutePath ?? "/").TrimEnd('/');
                if (string.IsNullOrEmpty(path))
                    path = "/";

                if (string.Equals(request.HttpMethod, "GET", StringComparison.OrdinalIgnoreCase) &&
                    (path == "/health" || path == "/"))
                {
                    WriteJson(response, 200, new Dictionary<string, object>
                    {
                        ["ok"] = true,
                        ["service"] = "cie_reader",
                        ["version"] = "1",
                    });
                    return;
                }

                if (string.Equals(request.HttpMethod, "POST", StringComparison.OrdinalIgnoreCase) &&
                    path == "/read")
                {
                    string body;
                    using (var reader = new StreamReader(request.InputStream, request.ContentEncoding))
                        body = reader.ReadToEnd();

                    string can = null;
                    try
                    {
                        using (JsonDocument doc = JsonDocument.Parse(string.IsNullOrWhiteSpace(body) ? "{}" : body))
                        {
                            if (doc.RootElement.TryGetProperty("can", out JsonElement canEl))
                                can = canEl.GetString();
                        }
                    }
                    catch (JsonException)
                    {
                        WriteJson(response, 400, new Dictionary<string, object>
                        {
                            ["ok"] = false,
                            ["message"] = "Richiesta non valida.",
                        });
                        return;
                    }

                    can = (can ?? "").Trim();
                    if (can.Length != 6 || !IsDigits(can))
                    {
                        WriteJson(response, 400, new Dictionary<string, object>
                        {
                            ["ok"] = false,
                            ["message"] = "Il CAN deve essere composto da 6 cifre.",
                        });
                        return;
                    }

                    try
                    {
                        Dictionary<string, string> raw;
                        lock (ReadLock)
                        {
                            raw = ReadCie(can, timeoutSeconds);
                        }

                        WriteJson(response, 200, new Dictionary<string, object>
                        {
                            ["ok"] = true,
                            ["data"] = ToFormPayload(raw),
                        });
                    }
                    catch (Exception ex)
                    {
                        WriteJson(response, 400, new Dictionary<string, object>
                        {
                            ["ok"] = false,
                            ["message"] = ex.Message ?? "Lettura CIE non riuscita.",
                        });
                    }
                    return;
                }

                WriteJson(response, 404, new Dictionary<string, object>
                {
                    ["ok"] = false,
                    ["message"] = "Endpoint non trovato.",
                });
            }
            catch (Exception ex)
            {
                try
                {
                    WriteJson(response, 500, new Dictionary<string, object>
                    {
                        ["ok"] = false,
                        ["message"] = "Errore agent CIE: " + ex.Message,
                    });
                }
                catch
                {
                    // ignore
                }
            }
        }

        private static void AddCorsHeaders(HttpListenerRequest request, HttpListenerResponse response)
        {
            string origin = request.Headers["Origin"];
            response.Headers["Access-Control-Allow-Origin"] =
                string.IsNullOrWhiteSpace(origin) ? "*" : origin;
            response.Headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS";
            response.Headers["Access-Control-Allow-Headers"] = "Content-Type";
            response.Headers["Access-Control-Max-Age"] = "86400";
            if (!string.IsNullOrWhiteSpace(origin))
                response.Headers["Vary"] = "Origin";
        }

        private static void WriteJson(HttpListenerResponse response, int statusCode, object payload)
        {
            byte[] bytes = Encoding.UTF8.GetBytes(JsonSerializer.Serialize(payload));
            response.StatusCode = statusCode;
            response.ContentType = "application/json; charset=utf-8";
            response.ContentEncoding = Encoding.UTF8;
            response.ContentLength64 = bytes.Length;
            response.OutputStream.Write(bytes, 0, bytes.Length);
            response.Close();
        }

        /// <summary>
        /// Allinea l'output al payload Django (map_cie_payload) usato dal form anagrafica.
        /// </summary>
        private static Dictionary<string, object> ToFormPayload(Dictionary<string, string> raw)
        {
            string Get(string key) =>
                raw != null && raw.TryGetValue(key, out string value) ? (value ?? "").Trim() : "";

            string documentoTipo = Get("documento_tipo");
            if (string.IsNullOrEmpty(documentoTipo))
                documentoTipo = "Carta di Identità";

            string cf = Get("codice_fiscale").ToUpperInvariant();
            string provinciaNascita = Get("provincia_nascita");
            if (provinciaNascita.Length > 2)
                provinciaNascita = provinciaNascita.Substring(0, 2);
            provinciaNascita = provinciaNascita.ToUpperInvariant();

            string indirizzo = Get("indirizzo");
            string civico = Get("civico");
            string cap = Get("cap");
            string comune = Get("comune");
            string provincia = Get("provincia");
            if (provincia.Length > 2)
                provincia = provincia.Substring(0, 2);
            provincia = provincia.ToUpperInvariant();
            string indirizzoRaw = Get("indirizzo_raw");
            if (string.IsNullOrEmpty(indirizzoRaw))
                indirizzoRaw = Get("chip_indirizzo");

            if (string.IsNullOrEmpty(cap) && !string.IsNullOrEmpty(indirizzoRaw))
            {
                Match match = Regex.Match(indirizzoRaw, @"\b(\d{5})\b");
                if (match.Success)
                    cap = match.Groups[1].Value;
            }

            string rilasciato = Get("documento_rilasciato_da");
            if (string.IsNullOrEmpty(rilasciato) ||
                rilasciato.IndexOf("MINISTERO", StringComparison.OrdinalIgnoreCase) >= 0)
            {
                if (!string.IsNullOrEmpty(comune))
                {
                    rilasciato = comune.StartsWith("COMUNE", StringComparison.OrdinalIgnoreCase)
                        ? comune
                        : "Comune di " + comune;
                }
            }

            var data = new Dictionary<string, object>
            {
                ["cognome"] = Get("cognome"),
                ["nome"] = Get("nome"),
                ["sesso"] = Get("sesso"),
                ["data_nascita"] = Get("data_nascita"),
                ["luogo_nascita"] = Get("luogo_nascita"),
                ["provincia_nascita"] = provinciaNascita,
                ["codice_fiscale"] = cf,
                ["documento_tipo"] = documentoTipo,
                ["documento_numero"] = Get("documento_numero"),
                ["documento_data_rilascio"] = Get("documento_data_rilascio"),
                ["documento_data_scadenza"] = Get("documento_data_scadenza"),
                ["documento_rilasciato_da"] = rilasciato,
                ["indirizzo_raw"] = indirizzoRaw,
            };

            if (!string.IsNullOrEmpty(indirizzo) || !string.IsNullOrEmpty(comune) ||
                !string.IsNullOrEmpty(cap) || !string.IsNullOrEmpty(provincia))
            {
                data["indirizzo"] = new Dictionary<string, object>
                {
                    ["indirizzo"] = indirizzo,
                    ["civico"] = civico,
                    ["cap"] = cap,
                    ["comune"] = comune,
                    ["provincia"] = provincia,
                    ["tipo"] = "residenza",
                    ["indirizzo_raw"] = indirizzoRaw,
                };
            }
            else
            {
                data["indirizzo"] = null;
            }

            return data;
        }

        private static Dictionary<string, string> ReadCie(string can, int timeoutSeconds)
        {
            if (can.Length != 6 || !IsDigits(can))
                throw new Exception("Il CAN deve essere composto da 6 cifre.");

            using (var sc = new SmartCard())
            {
                string reader = WaitForCard(sc, timeoutSeconds);
                if (!sc.Connect(reader, Share.SCARD_SHARE_EXCLUSIVE, Protocol.SCARD_PROTOCOL_T1))
                {
                    // Alcuni lettori Bit4id preferiscono T0/T1 automatico
                    if (!sc.Connect(reader, Share.SCARD_SHARE_EXCLUSIVE, Protocol.SCARD_PROTOCOL_T0orT1))
                        throw new Exception(
                            "Impossibile connettersi al lettore CIE. Verifica che la carta sia poggiata correttamente.");
                }

                try
                {
                    var eac = new EAC(sc);
                    if (!eac.IsSAC())
                        throw new Exception("La carta non supporta PACE/SAC. Usa una CIE contactless.");

                    eac.PACE(can);
                    try
                    {
                        eac.ReadDG(DG.DG14);
                        eac.ChipAuthentication();
                    }
                    catch
                    {
                        // Dopo PACE i DG anagrafici sono comunque leggibili.
                    }

                    byte[] dg11 = eac.ReadDG(DG.DG11);
                    byte[] dg1 = eac.ReadDG(DG.DG1);
                    byte[] dg12 = eac.ReadDG(DG.DG12);

                    string fullName = GetTagValue(KeyFullName, dg11);
                    string birthPlace = GetTagValue(KeyBirthAddress, dg11);
                    string addressRaw = GetTagValue(KeyAddress, dg11);
                    string cf = GetTagValue(KeyCf, dg11);
                    string mrz = GetTagValue(KeyMrz, dg1);
                    string dateIssue = GetTagValue(KeyDateIssue, dg12);
                    string dateExpire = GetTagValue(KeyDateExpire, dg12);
                    string issuingAuthority = GetTagValue(new byte[] { 0x5F, 0x19 }, dg12);

                    var names = SplitName(fullName);
                    var birth = SplitParts(birthPlace);
                    var address = ParseResidenceAddress(addressRaw);
                    var mrzFields = ParseMrz(mrz);

                    // Scadenza: preferisci MRZ (DG12 italiano non la espone in modo affidabile)
                    string scadenzaIso = mrzFields.ExpiryIso;
                    if (string.IsNullOrEmpty(scadenzaIso))
                        scadenzaIso = ToIsoDate(dateExpire);

                    // Sul fronte CIE "Rilasciato da" è il Comune, non il Ministero (tag ICAO 5F19).
                    string rilasciatoDa = FormatComuneRilascio(address.Comune);

                    var result = new Dictionary<string, string>
                    {
                        ["cognome"] = names.Cognome ?? "",
                        ["nome"] = names.Nome ?? "",
                        ["sesso"] = mrzFields.Sex ?? "",
                        ["data_nascita"] = mrzFields.BirthIso ?? "",
                        ["luogo_nascita"] = birth.Length > 0 ? birth[0] : "",
                        ["provincia_nascita"] = birth.Length > 1 ? birth[1] : "",
                        ["codice_fiscale"] = (cf ?? "").Trim().ToUpperInvariant(),
                        ["documento_tipo"] = "Carta di Identità",
                        ["documento_numero"] = mrzFields.DocumentNumber ?? "",
                        ["documento_data_rilascio"] = ToIsoDate(dateIssue) ?? "",
                        ["documento_data_scadenza"] = scadenzaIso ?? "",
                        ["documento_rilasciato_da"] = rilasciatoDa,
                        ["indirizzo"] = address.Indirizzo ?? "",
                        ["civico"] = address.Civico ?? "",
                        ["comune"] = address.Comune ?? "",
                        ["provincia"] = address.Provincia ?? "",
                        ["cap"] = address.Cap ?? "",
                        // Dati grezzi dal chip (per verifica)
                        ["chip_nome_completo"] = fullName ?? "",
                        ["chip_luogo_nascita"] = birthPlace ?? "",
                        ["chip_indirizzo"] = addressRaw ?? "",
                        ["chip_autorita_emissione"] = issuingAuthority ?? "",
                        ["chip_data_rilascio"] = dateIssue ?? "",
                        ["chip_data_scadenza_dg12"] = dateExpire ?? "",
                        ["indirizzo_raw"] = addressRaw ?? "",
                        ["mrz"] = mrz ?? "",
                    };

                    return result;
                }
                finally
                {
                    sc.Disconnect(Disposition.SCARD_RESET_CARD);
                }
            }
        }

        private static string WaitForCard(SmartCard sc, int timeoutSeconds)
        {
            DateTime deadline = DateTime.UtcNow.AddSeconds(timeoutSeconds);
            while (DateTime.UtcNow < deadline)
            {
                string[] readers;
                try
                {
                    readers = sc.ListReaders();
                }
                catch
                {
                    readers = null;
                }

                if (readers != null)
                {
                    foreach (string reader in readers)
                    {
                        if (string.IsNullOrWhiteSpace(reader))
                            continue;
                        try
                        {
                            if (sc.IsCardInReader(reader))
                                return reader;
                        }
                        catch
                        {
                            // ignore transient reader errors
                        }
                    }
                }

                Thread.Sleep(250);
            }

            throw new Exception(
                "Nessuna CIE rilevata sul lettore. Poggia la carta sul Bit4id e riprova.");
        }

        private static (string Cognome, string Nome) SplitName(string value)
        {
            if (string.IsNullOrWhiteSpace(value))
                return (null, null);

            string[] parts = value.Split(new[] { "<<" }, StringSplitOptions.None);
            string cognome = parts.Length > 0 ? CleanMrzText(parts[0]) : null;
            string nome = parts.Length > 1 ? CleanMrzText(parts[1].Replace("<", " ")) : null;
            return (cognome, nome);
        }

        private static string[] SplitParts(string value)
        {
            if (string.IsNullOrWhiteSpace(value))
                return Array.Empty<string>();

            string normalized = value
                .Replace('\u001c', '<')
                .Replace('|', '<')
                .Replace(';', '<')
                .Replace('\n', '<')
                .Replace('\r', '<');

            string[] parts = normalized.Split(new[] { '<' }, StringSplitOptions.RemoveEmptyEntries);
            for (int i = 0; i < parts.Length; i++)
                parts[i] = parts[i].Trim();
            return parts;
        }

        private static string FormatComuneRilascio(string comune)
        {
            if (string.IsNullOrWhiteSpace(comune))
                return "";

            comune = comune.Trim();
            if (comune.StartsWith("COMUNE DI ", StringComparison.OrdinalIgnoreCase) ||
                comune.StartsWith("COMUNE ", StringComparison.OrdinalIgnoreCase))
            {
                return comune;
            }

            return "Comune di " + comune;
        }

        /// <summary>
        /// Formati tipici CIE (tag 5F42):
        /// - VIA ROMA 1&lt;00100&lt;ROMA&lt;RM
        /// - VIA ROMA 1&lt;ROMA&lt;RM
        /// - VIA ROMA&lt;1&lt;00100&lt;ROMA&lt;RM
        /// - VIA ROMA 1 00100 ROMA RM
        /// </summary>
        private static (string Indirizzo, string Civico, string Cap, string Comune, string Provincia)
            ParseResidenceAddress(string value)
        {
            if (string.IsNullOrWhiteSpace(value))
                return (null, null, null, null, null);

            string raw = value.Trim();
            var parts = new List<string>(SplitParts(raw));
            string cap = null;
            string provincia = null;
            string civico = null;

            var capMatch = Regex.Match(raw, @"\b(\d{5})\b");
            if (capMatch.Success)
                cap = capMatch.Groups[1].Value;

            for (int i = parts.Count - 1; i >= 0; i--)
            {
                string part = parts[i];
                if (Regex.IsMatch(part, @"^\d{5}$"))
                {
                    if (string.IsNullOrEmpty(cap))
                        cap = part;
                    parts.RemoveAt(i);
                    continue;
                }

                var embedded = Regex.Match(part, @"^(?:(\d{5})\s+(.+)|(.+?)\s+(\d{5}))$");
                if (embedded.Success)
                {
                    if (string.IsNullOrEmpty(cap))
                    {
                        cap = embedded.Groups[1].Success
                            ? embedded.Groups[1].Value
                            : embedded.Groups[4].Value;
                    }
                    parts[i] = embedded.Groups[1].Success
                        ? embedded.Groups[2].Value.Trim()
                        : embedded.Groups[3].Value.Trim();
                }
            }

            for (int i = parts.Count - 1; i >= 0; i--)
            {
                if (provincia == null && Regex.IsMatch(parts[i], @"^[A-Za-z]{2}$"))
                {
                    provincia = parts[i].ToUpperInvariant();
                    parts.RemoveAt(i);
                }
            }

            if (parts.Count >= 2 && Regex.IsMatch(parts[1], @"^\d+[A-Za-z]?$") && parts[1].Length <= 6)
            {
                civico = parts[1];
                parts.RemoveAt(1);
            }

            string indirizzo = parts.Count > 0 ? parts[0] : null;
            string comune = parts.Count > 1 ? parts[1] : null;

            if (parts.Count <= 1 && raw.IndexOf('<') < 0)
            {
                var spaced = Regex.Match(
                    raw,
                    @"^(?<ind>.+?)\s+(?<cap>\d{5})\s+(?<comune>.+?)(?:\s+(?<prov>[A-Za-z]{2}))?$"
                );
                if (spaced.Success)
                {
                    indirizzo = spaced.Groups["ind"].Value.Trim();
                    cap = spaced.Groups["cap"].Value;
                    comune = spaced.Groups["comune"].Value.Trim();
                    if (spaced.Groups["prov"].Success)
                        provincia = spaced.Groups["prov"].Value.ToUpperInvariant();
                }
            }

            if (string.IsNullOrEmpty(cap) && !string.IsNullOrEmpty(indirizzo))
            {
                var match = Regex.Match(indirizzo, @"^(.*?)(?:\s+)(\d{5})$");
                if (match.Success)
                {
                    indirizzo = match.Groups[1].Value.Trim();
                    cap = match.Groups[2].Value;
                }
            }

            return (indirizzo, civico, cap, comune, provincia);
        }

        private static string CleanMrzText(string value)
        {
            if (string.IsNullOrWhiteSpace(value))
                return null;
            return value.Replace("<", " ").Trim();
        }

        private static string GetTagValue(byte[] key, byte[] dg)
        {
            if (dg == null || key == null)
                return null;

            int[] indexes = Locate(dg, key);
            if (indexes.Length == 0)
                return null;

            int start = indexes.Length == 1 ? indexes[0] : indexes[1];
            int offset = start + key.Length;
            if (offset >= dg.Length)
                return null;

            if (!TryReadBerLength(dg, ref offset, out int size) || size < 0)
                return null;
            if (offset + size > dg.Length)
                size = dg.Length - offset;
            if (size <= 0)
                return null;

            byte[] slice = new byte[size];
            Array.Copy(dg, offset, slice, 0, size);
            string utf8 = Encoding.UTF8.GetString(slice).Trim('\0', ' ');
            if (utf8.IndexOf('\uFFFD') >= 0)
                return Encoding.GetEncoding("ISO-8859-1").GetString(slice).Trim('\0', ' ');
            return utf8;
        }

        private static bool TryReadBerLength(byte[] data, ref int offset, out int length)
        {
            length = 0;
            if (offset >= data.Length)
                return false;

            int first = data[offset++];
            if (first < 0x80)
            {
                length = first;
                return true;
            }

            int count = first & 0x7F;
            if (count == 0 || count > 3 || offset + count > data.Length)
                return false;

            for (int i = 0; i < count; i++)
                length = (length << 8) | data[offset++];
            return true;
        }

        private static int[] Locate(byte[] data, byte[] candidate)
        {
            var list = new List<int>();
            for (int i = 0; i <= data.Length - candidate.Length; i++)
            {
                bool match = true;
                for (int j = 0; j < candidate.Length; j++)
                {
                    if (data[i + j] != candidate[j])
                    {
                        match = false;
                        break;
                    }
                }
                if (match)
                    list.Add(i);
            }
            return list.ToArray();
        }

        private static (string DocumentNumber, string Sex, string BirthIso, string ExpiryIso) ParseMrz(string mrz)
        {
            if (string.IsNullOrWhiteSpace(mrz))
                return (null, null, null, null);

            string compact = mrz.Replace("\r", "").Replace("\n", "").Trim();
            if (compact.Length < 60)
                return (null, null, null, null);

            // TD1 CIE: 3 linee da 30 caratteri
            string line1 = compact.Substring(0, Math.Min(30, compact.Length));
            string line2 = compact.Length >= 60 ? compact.Substring(30, 30) : "";

            string documentNumber = line1.Length >= 14
                ? line1.Substring(5, 9).Replace("<", "").Trim()
                : null;

            string birthIso = null;
            string expiryIso = null;
            string sex = null;
            if (line2.Length >= 15)
            {
                birthIso = YymmddToIso(line2.Substring(0, 6), isExpiry: false);
                sex = NormalizeSex(line2.Substring(7, 1));
                expiryIso = YymmddToIso(line2.Substring(8, 6), isExpiry: true);
            }

            return (documentNumber, sex, birthIso, expiryIso);
        }

        private static string NormalizeSex(string value)
        {
            if (string.IsNullOrEmpty(value))
                return "";
            value = value.ToUpperInvariant();
            if (value == "M" || value == "F")
                return value;
            return "";
        }

        private static string YymmddToIso(string yymmdd, bool isExpiry)
        {
            if (string.IsNullOrEmpty(yymmdd) || yymmdd.Length != 6 || !IsDigits(yymmdd))
                return null;

            int yy = int.Parse(yymmdd.Substring(0, 2), CultureInfo.InvariantCulture);
            int mm = int.Parse(yymmdd.Substring(2, 2), CultureInfo.InvariantCulture);
            int dd = int.Parse(yymmdd.Substring(4, 2), CultureInfo.InvariantCulture);
            int year2000 = 2000 + yy;
            int year1900 = 1900 + yy;
            int year;
            int currentYear = DateTime.Today.Year;

            if (isExpiry)
            {
                // Scadenze CIE: "31" = 2031, non 1931
                year = year2000;
                if (year > currentYear + 50)
                    year = year1900;
            }
            else
            {
                // Nascita: se 20xx è nel futuro → 19xx (es. 31 = 1931)
                year = year2000 > currentYear ? year1900 : year2000;
            }

            try
            {
                return new DateTime(year, mm, dd).ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
            }
            catch
            {
                return null;
            }
        }

        private static string ToIsoDate(string value)
        {
            if (string.IsNullOrWhiteSpace(value))
                return null;

            value = value.Trim();
            if (value.Length == 8 && IsDigits(value))
            {
                // aaaammgg
                try
                {
                    return DateTime.ParseExact(value, "yyyyMMdd", CultureInfo.InvariantCulture)
                        .ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
                }
                catch
                {
                    return null;
                }
            }

            if (DateTime.TryParse(value, CultureInfo.InvariantCulture, DateTimeStyles.None, out var dt))
                return dt.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);

            return null;
        }

        private static bool IsDigits(string value)
        {
            foreach (char c in value)
            {
                if (c < '0' || c > '9')
                    return false;
            }
            return true;
        }

        private static void Fail(string message)
        {
            var payload = new Dictionary<string, object>
            {
                ["ok"] = false,
                ["message"] = message ?? "Errore sconosciuto durante la lettura CIE.",
            };
            Console.Error.WriteLine(JsonSerializer.Serialize(payload));
            // Also print a single-line message for simpler wrappers
            Console.Error.WriteLine(message);
        }
    }
}
