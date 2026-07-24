from django.contrib.auth.hashers import PBKDF2PasswordHasher


class LabRepairPBKDF2PasswordHasher(PBKDF2PasswordHasher):
    """
    PBKDF2 con meno iterazioni del default Django 6 (1.200.000).

    Uso interno in LAN: resta sicuro e rende login / password errata
    molto piu' reattivi. Le password gia' salvate con iterazioni alte
    vengono ricalcolate al primo login corretto.
    """

    iterations = 390000
