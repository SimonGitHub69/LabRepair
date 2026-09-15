from contextlib import contextmanager
from dataclasses import dataclass

from apps.core.models import ConfigurazioneMssql

ODBC_DRIVERS = (
    "ODBC Driver 18 for SQL Server",
    "ODBC Driver 17 for SQL Server",
    "SQL Server Native Client 11.0",
    "SQL Server",
)


@dataclass
class MssqlTestResult:
    ok: bool
    message: str
    driver: str = ""


def get_mssql_config():
    return ConfigurazioneMssql.get_solo()


def config_from_post(post, instance=None):
    instance = instance or ConfigurazioneMssql.get_solo()
    if not post:
        return instance

    password = (post.get("password") or "").strip()
    porta_raw = (post.get("porta") or "").strip()
    iva_id_raw = (post.get("iva_id_cassa") or "").strip()
    aliquota_raw = (post.get("iva_aliquota_cassa") or "").strip()

    try:
        porta = int(porta_raw) if porta_raw else instance.porta
    except ValueError:
        porta = instance.porta

    try:
        iva_id = int(iva_id_raw) if iva_id_raw else instance.iva_id_cassa
    except ValueError:
        iva_id = instance.iva_id_cassa

    try:
        from decimal import Decimal, InvalidOperation

        iva_aliquota = Decimal(aliquota_raw) if aliquota_raw else instance.iva_aliquota_cassa
    except (InvalidOperation, TypeError, ValueError):
        iva_aliquota = instance.iva_aliquota_cassa

    return ConfigurazioneMssql(
        attiva=post.get("attiva") == "on",
        autenticazione_windows=post.get("autenticazione_windows") == "on",
        server=(post.get("server") or "").strip() or instance.server,
        porta=porta or 1433,
        nome_database=(post.get("nome_database") or "").strip() or instance.nome_database,
        nome_database_cassa=(post.get("nome_database_cassa") or "").strip()
        or instance.nome_database_cassa,
        utente=(post.get("utente") or "").strip() or instance.utente,
        password=password or instance.password,
        prz_pvn_codice=(post.get("prz_pvn_codice") or "").strip() or instance.prz_pvn_codice or "TN",
        iva_id_cassa=iva_id,
        iva_aliquota_cassa=iva_aliquota,
        note=(post.get("note") or "").strip() or instance.note,
    )


def escape_odbc_value(value):
    if value is None:
        return ""
    text = str(value)
    if any(char in text for char in (";", "{", "}", "=")):
        return "{" + text.replace("}", "}}") + "}"
    return text


def build_odbc_connection_string(config, driver, database=None):
    parts = [
        f"DRIVER={{{driver}}}",
        f"SERVER={config.server_display}",
    ]

    db_name = (database if database is not None else config.nome_database) or ""
    db_name = db_name.strip()
    if db_name:
        parts.append(f"DATABASE={db_name}")

    utente = (config.utente or "").strip()
    if config.autenticazione_windows or not utente:
        parts.append("Trusted_Connection=yes")
    else:
        parts.append(f"UID={escape_odbc_value(utente)}")
        parts.append(f"PWD={escape_odbc_value(config.password or '')}")

    driver_name = driver.lower()
    if "odbc driver 1" in driver_name:
        parts.append("Encrypt=no")
        parts.append("TrustServerCertificate=yes")

    return ";".join(parts) + ";"


def format_mssql_error(driver, error_text):
    normalized = error_text.lower()

    if "18456" in error_text or "accesso non" in normalized or "login failed" in normalized:
        return (
            "Accesso negato da SQL Server: utente o password non validi. "
            "Abilita l'autenticazione mista su SQL Server (SQL + Windows) e verifica le credenziali, "
            "oppure usa Autenticazione Windows nel form."
        )

    if is_mssql_network_error(error_text):
        return (
            "Server non raggiungibile. Controlla istanza, porta e che SQL Server sia avviato "
            f"(driver: {driver})."
        )

    if "invalid connection string attribute" in normalized or "attributo di stringa" in normalized:
        return f"Parametri di connessione non validi con {driver}."

    return f"{driver}: {error_text}"


def is_mssql_network_error(error_text):
    normalized = (error_text or "").lower()
    markers = (
        "08001",
        "server sql inesistente",
        "network interfaces",
        "timed out",
        "timeout",
        "impossibile connettersi",
        "could not open a connection",
        "server is not found",
        "server does not exist",
        "nè è stato possibile stabilire",
        "communication link failure",
    )
    return any(marker in normalized for marker in markers)


def get_available_odbc_drivers():
    try:
        import pyodbc
    except ImportError:
        return []
    installed_drivers = pyodbc.drivers()
    return [driver for driver in ODBC_DRIVERS if driver in installed_drivers]


def _open_mssql_raw(config, timeout, database=None):
    """Apre la prima connessione pyodbc funzionante (senza context manager)."""
    try:
        import pyodbc
    except ImportError as exc:
        raise RuntimeError("Modulo pyodbc non installato.") from exc

    drivers_to_try = get_available_odbc_drivers()
    if not drivers_to_try:
        raise RuntimeError("Nessun driver ODBC SQL Server installato.")

    errors = []
    for driver in drivers_to_try:
        try:
            connection_string = build_odbc_connection_string(
                config, driver, database=database
            )
            return pyodbc.connect(connection_string, timeout=timeout)
        except pyodbc.Error as exc:
            errors.append((driver, str(exc)))
            if is_mssql_network_error(str(exc)):
                break

    driver, error_text = errors[0]
    raise RuntimeError(format_mssql_error(driver, error_text))


@contextmanager
def open_mssql_connection(config=None, timeout=2):
    config = config or get_mssql_config()
    if not config.attiva or not config.is_configured:
        raise RuntimeError("Collegamento MS-SQL non attivo o incompleto.")

    connection = _open_mssql_raw(config, timeout)
    try:
        yield connection
    finally:
        connection.close()


@contextmanager
def open_mssql_cassa_connection(config=None, timeout=2):
    """Connessione al Database Cassa (lettura scontrini)."""
    config = config or get_mssql_config()
    if not config.attiva or not config.is_cassa_configured:
        raise RuntimeError("Database Cassa non attivo o incompleto.")

    database = (config.nome_database_cassa or "").strip()
    connection = _open_mssql_raw(config, timeout, database=database)
    try:
        yield connection
    finally:
        connection.close()


def test_mssql_connection(config=None, timeout=5, *, database=None, label=None):
    config = config or get_mssql_config()
    db_name = (database if database is not None else config.nome_database) or ""
    db_name = db_name.strip()
    label = label or "database"

    if not (config.server or "").strip() or not db_name:
        if config.autenticazione_windows:
            msg = f"Compila istanza server e {label}."
        else:
            msg = f"Compila istanza server, {label}, utente e password."
        return MssqlTestResult(ok=False, message=msg)

    if not config.autenticazione_windows and not (
        (config.utente or "").strip() and config.password
    ):
        return MssqlTestResult(
            ok=False,
            message="Compila utente e password (oppure attiva Autenticazione Windows).",
        )

    try:
        import pyodbc
    except ImportError:
        return MssqlTestResult(
            ok=False,
            message="Modulo pyodbc non installato. Esegui: pip install pyodbc",
        )

    installed_drivers = get_available_odbc_drivers()

    if not installed_drivers:
        return MssqlTestResult(
            ok=False,
            message="Nessun driver ODBC SQL Server installato (17, 18 o SQL Server).",
        )

    errors = []
    for driver in installed_drivers:
        try:
            connection_string = build_odbc_connection_string(
                config, driver, database=db_name
            )
            connection = pyodbc.connect(connection_string, timeout=timeout)
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            connection.close()
            return MssqlTestResult(
                ok=True,
                message=f"Connessione riuscita a {config.server_display} / {db_name} ({driver}).",
                driver=driver,
            )
        except pyodbc.Error as exc:
            errors.append((driver, str(exc)))
        except Exception as exc:
            errors.append((driver, str(exc)))

    driver, error_text = errors[0]
    return MssqlTestResult(
        ok=False,
        message=format_mssql_error(driver, error_text),
        driver=driver,
    )


def test_mssql_cassa_connection(config=None, timeout=5):
    config = config or get_mssql_config()
    return test_mssql_connection(
        config,
        timeout=timeout,
        database=(config.nome_database_cassa or "").strip(),
        label="Database Cassa",
    )
