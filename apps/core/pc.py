import ipaddress
import os
import re
import socket
import subprocess
import sys

from apps.core.models.configurazione_pc import ConfigurazionePC
from apps.core.negozi import normalize_negozio_code

COOKIE_NAME = "labrepair_pc"
SESSION_KEY = "nome_pc"
COOKIE_MAX_AGE = 365 * 24 * 60 * 60
_LOOPBACK = {"127.0.0.1", "::1", "localhost"}
_INVALID_HOST_NAMES = {"unknown", "localhost"}


def normalize_nome_pc(value):
    return (value or "").strip()


def normalize_remote_ip(addr):
    """Normalizza REMOTE_ADDR (es. ::ffff:192.168.1.10 -> 192.168.1.10)."""
    text = (addr or "").strip()
    if not text:
        return ""
    if text.lower().startswith("::ffff:"):
        text = text.split(":", 2)[-1]
    try:
        ip = ipaddress.ip_address(text)
        if getattr(ip, "ipv4_mapped", None) is not None:
            return str(ip.ipv4_mapped)
        return str(ip)
    except ValueError:
        return text


def _is_loopback(addr):
    text = normalize_remote_ip(addr).lower()
    if text in _LOOPBACK:
        return True
    try:
        return ipaddress.ip_address(text).is_loopback
    except ValueError:
        return False


def _is_ip_literal(value):
    try:
        ipaddress.ip_address((value or "").strip())
        return True
    except ValueError:
        return False


def is_valid_pc_name(value):
    """
    Accetta nomi computer Windows plausibili.
    Scarta IP e frammenti tipo '192' da reverse DNS su 192.168.x.x.
    """
    nome = normalize_nome_pc(value)
    if not nome:
        return False
    if nome.lower() in _INVALID_HOST_NAMES:
        return False
    if _is_ip_literal(nome):
        return False
    # Solo cifre (es. primo ottetto IP da reverse DNS su 192.168.x.x)
    if re.fullmatch(r"\d+", nome):
        return False
    # Hostname / NetBIOS: lettere, numeri, trattino, underscore
    if not re.fullmatch(r"[A-Za-z0-9]([A-Za-z0-9_-]{0,62}[A-Za-z0-9])?", nome):
        return False
    return True


def get_local_system_pc_name():
    """Nome fisico del computer che esegue LabRepair (Windows COMPUTERNAME / hostname)."""
    for key in ("COMPUTERNAME", "HOSTNAME"):
        value = normalize_nome_pc(os.environ.get(key))
        if is_valid_pc_name(value):
            return value
    try:
        value = normalize_nome_pc(socket.gethostname().split(".")[0])
        if is_valid_pc_name(value):
            return value
    except OSError:
        pass
    return ""


def _local_ipv4_addresses():
    found = set()
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if ip and not _is_loopback(ip):
                found.add(ip)
    except OSError:
        pass
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            if ip and not _is_loopback(ip):
                found.add(ip)
    except OSError:
        pass
    return found


def _is_request_from_this_machine(remote_ip):
    remote_ip = normalize_remote_ip(remote_ip)
    if not remote_ip:
        return False
    if _is_loopback(remote_ip):
        return True
    return remote_ip in _local_ipv4_addresses()


def _netbios_name_from_ip(ip):
    """Su Windows LAN prova a risolvere il nome NetBIOS del client."""
    if sys.platform != "win32" or not ip or _is_loopback(ip):
        return ""
    try:
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        result = subprocess.run(
            ["nbtstat", "-A", ip],
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
            creationflags=creationflags,
        )
        output = f"{result.stdout or ''}\n{result.stderr or ''}"
    except (OSError, subprocess.SubprocessError, TimeoutError):
        return ""

    for line in output.splitlines():
        match = re.search(
            r"^\s*([A-Za-z0-9_$-]{1,15})\s+<00>\s+UNIQUE\b",
            line,
            flags=re.IGNORECASE,
        )
        if match:
            name = normalize_nome_pc(match.group(1))
            if name.endswith("$"):
                continue
            if is_valid_pc_name(name):
                return name
    return ""


def _reverse_dns_name(ip):
    if not ip or _is_loopback(ip):
        return ""
    try:
        host, _, _ = socket.gethostbyaddr(ip)
    except OSError:
        return ""
    host = normalize_nome_pc(host or "")
    if not host or _is_ip_literal(host):
        return ""
    # Es. PTR sbagliato / IP come hostname -> "192.168.1.10" -> primo pezzo "192"
    first = normalize_nome_pc(host.split(".")[0])
    if is_valid_pc_name(first):
        return first
    return ""


def detect_client_pc_name(request):
    """
    Rileva il nome fisico del PC che sta usando LabRepair.
    Ordine: header agent/app → stesso host del server → NetBIOS → reverse DNS.
    """
    if request is None:
        return get_local_system_pc_name()

    headers = getattr(request, "headers", None)
    if headers is not None:
        for key in ("X-LabRepair-PC", "X-Computer-Name", "X-Client-Computer"):
            value = normalize_nome_pc(headers.get(key))
            if is_valid_pc_name(value):
                return value

    # Cookie/sessione impostati dal launcher LabRepairApp (?pc=COMPUTERNAME)
    session_val = normalize_nome_pc(getattr(request, "session", {}).get(SESSION_KEY))
    if is_valid_pc_name(session_val):
        return session_val
    cookies = getattr(request, "COOKIES", None) or {}
    cookie_val = normalize_nome_pc(cookies.get(COOKIE_NAME))
    if is_valid_pc_name(cookie_val):
        return cookie_val

    remote = normalize_remote_ip(request.META.get("REMOTE_ADDR"))
    # Browser sul PC server via localhost O via IP LAN (es. http://192.168.x.x)
    if _is_request_from_this_machine(remote):
        local = get_local_system_pc_name()
        if local:
            return local

    for candidate in (
        _netbios_name_from_ip(remote),
        _reverse_dns_name(remote),
        normalize_nome_pc(request.META.get("REMOTE_HOST")).split(".")[0],
    ):
        value = normalize_nome_pc(candidate)
        if is_valid_pc_name(value) and value.lower() != remote.lower():
            return value

    return ""


def get_nome_pc_from_request(request):
    if request is None:
        return ""

    session_val = normalize_nome_pc(getattr(request, "session", {}).get(SESSION_KEY))
    if session_val:
        return session_val

    cookies = getattr(request, "COOKIES", None) or {}
    cookie_val = normalize_nome_pc(cookies.get(COOKIE_NAME))
    if cookie_val:
        return cookie_val

    headers = getattr(request, "headers", None)
    if headers is not None:
        header_val = normalize_nome_pc(headers.get("X-LabRepair-PC"))
        if header_val:
            return header_val

    return ""


def get_configurazione_pc(nome_pc):
    nome = normalize_nome_pc(nome_pc)
    if not nome:
        return None
    return (
        ConfigurazionePC.objects.filter(is_active=True, nome_pc__iexact=nome)
        .order_by("nome_pc")
        .first()
    )


def get_configurazione_pc_for_request(request):
    return get_configurazione_pc(get_nome_pc_from_request(request))


def bind_nome_pc(request, response, nome_pc):
    """Associa il PC alla sessione e a un cookie di lunga durata."""
    nome = normalize_nome_pc(nome_pc)
    cfg = get_configurazione_pc(nome) if nome else None
    if cfg:
        request.session[SESSION_KEY] = cfg.nome_pc
        response.set_cookie(
            COOKIE_NAME,
            cfg.nome_pc,
            max_age=COOKIE_MAX_AGE,
            samesite="Lax",
            httponly=False,
        )
        return cfg

    request.session.pop(SESSION_KEY, None)
    response.delete_cookie(COOKIE_NAME)
    return None


def negozio_default_for_pc(nome_pc):
    cfg = get_configurazione_pc(nome_pc)
    if not cfg:
        return ""
    return normalize_negozio_code(cfg.negozio_default)


def pc_choices(include_blank=True):
    rows = list(
        ConfigurazionePC.objects.filter(is_active=True)
        .order_by("nome_pc")
        .values_list("nome_pc", "descrizione", "negozio_default", "layout_stile")
    )
    choices = []
    if include_blank:
        choices.append(("", "— Seleziona postazione —"))
    for nome, descrizione, _negozio, _layout in rows:
        label = f"{nome} — {descrizione}" if descrizione else nome
        choices.append((nome, label))
    return choices


def pc_negozio_map():
    return {
        nome: negozio
        for nome, negozio in ConfigurazionePC.objects.filter(is_active=True).values_list(
            "nome_pc", "negozio_default"
        )
    }
