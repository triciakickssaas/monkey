from common.common_consts.validation_formats import (
    VALID_RANSOMWARE_TARGET_PATH_LINUX,
    VALID_RANSOMWARE_TARGET_PATH_WINDOWS,
)

RANSOMWARE = {
    "title": "Ransomware",
    "type": "object",
    "properties": {
        "encryption": {
            "title": "Simulation",
            "type": "object",
            "description": "To simulate ransomware encryption, create a directory and put some "
            "files there to be encrypted. Do this on each machine on which you want to run the "
            "ransomware encryption simulation.\n\nProvide the path to the directory that was "
            "created on each machine:",
            "properties": {
                "enabled": {
                    "title": "Encrypt files",
                    "type": "boolean",
                    "default": True,
                    "description": "Ransomware encryption will be simulated by flipping every bit "
                    "in the files contained within the target directories.",
                },
                "info_box": {
                    "title": "",
                    "type": "object",
                    "info": "No files will be encrypted if a directory is not specified or doesn't "
                    "exist on a victim machine.",
                },
                "directories": {
                    "title": "Directories to encrypt",
                    "type": "object",
                    "properties": {
                        "linux_target_dir": {
                            "title": "Linux target directory",
                            "type": "string",
                            "format": VALID_RANSOMWARE_TARGET_PATH_LINUX,
                            "default": "",
                            "description": "A path to a directory on Linux systems that contains "
                            "files that you will allow Infection Monkey to encrypt. If no "
                            "directory is specified, no files will be encrypted.",
                        },
                        "windows_target_dir": {
                            "title": "Windows target directory",
                            "type": "string",
                            "format": VALID_RANSOMWARE_TARGET_PATH_WINDOWS,
                            "default": "",
                            "description": "A path to a directory on Windows systems that contains "
                            "files that you will allow Infection Monkey to encrypt. If no "
                            "directory is specified, no files will be encrypted.",
                        },
                    },
                },
            },
        },
        "other_behaviors": {
            "title": "Other behavior",
            "type": "object",
            "properties": {
                "readme": {
                    "title": "Create a README.txt file",
                    "type": "boolean",
                    "default": True,
                    "description": "Creates a README.txt ransomware note on infected systems.",
                }
            },
        },
    },
}
