#!/usr/bin/env python3

import logging
import boto3

LOGGER = logging.getLogger()
LOGGER_LEVEL = logging.INFO
LOGGER.setLevel(LOGGER_LEVEL)

CIRCLECI_TOOL_NAME = "CIRCLECI"
CONCOURSE_TOOL_NAME = "CONCOURSE"
BOSH_TOOL_NAME = "BOSH"

SSM_KEY_FOR_CIRCLECI_API = ("/default/tools_iam_keys_rotation/"
                            "default/circleci_api_key")

SSM_KEY_FOR_VAULE_API = ("/default/tools_iam_keys_rotation/"
                         "default/vault_api_key")

SSM_PATH_FOR_IAM_CIRCLECI_INFO = ("/default/tools_iam_keys_rotation/default"
                                  "/iam_to_circle_mapping/iam_users")

SSM_PATH_FOR_IAM_VAULT_INFO = ("/default/tools_iam_keys_rotation/default"
                               "/iam_to_vault_mapping/iam_users")


# Exceptions #

class KeyRotationFailedException(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return(repr(self.value))


class CircleCiUpdateFailedException(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return(repr(self.value))


class WriteToVaultFailedException(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return(repr(self.value))


# AWS FUNCTIONS #

def get_ssm_value(key):
    try:
        ssm = boto3.client("ssm")
        return ssm.get_parameter(Name=key,
                                 WithDecryption=True)["Parameter"]["Value"]
    except Exception as e:
        error_message = ("Failed to fetch ssm key value for {0}: "
                         "{1}").format(key, str(e))
        raise KeyRotationFailedException(error_message)


def get_current_access_key_id(iam_client, iam_user_name):
    try:
        access_keys = iam_client.list_access_keys(
            UserName=iam_user_name)["AccessKeyMetadata"]
    except Exception as e:
        error_message = ("List access keys failed for {0} iam user: "
                         "{1}").format(iam_user_name, str(e))

        raise KeyRotationFailedException(error_message)

    # Validate existing number of access keys
    number_of_keys = len(access_keys)

    if number_of_keys == 0:
        error_message = ("No access keys found for {0} iam"
                         "user.").format(iam_user_name)

        raise KeyRotationFailedException(error_message)

    if number_of_keys > 1:
        error_message = ("More than 1 access key found for {0} iam user. "
                         "Delete unused access key. Or create separate iam "
                         "user for second key, update mappings and rerun "
                         "this script.").format(iam_user_name)

        raise KeyRotationFailedException(error_message)

    current_access_key_id = access_keys[0]["AccessKeyId"]
    return current_access_key_id


def create_new_iam_keys(iam_client, user_name):
    try:
        response = iam_client.create_access_key(UserName=user_name)
    except Exception as e:
        error_message = ("Access keys creation failed for {0} iam user:"
                         "{1}").format(user_name, str(e))

        raise KeyRotationFailedException(error_message)

    LOGGER.info(("Successfully created new access keys for {0} "
                 "iam user").format(user_name))

    access_key = response.get("AccessKey")
    access_key_id = access_key.get("AccessKeyId")
    secret_key = access_key.get("SecretAccessKey")
    return access_key_id, secret_key


def delete_old_iam_keys(iam_client, iam_user_name, current_access_key_id,
                        update_success):
    if update_success:
        try:
            iam_client.delete_access_key(
                AccessKeyId=current_access_key_id, UserName=iam_user_name)

            LOGGER.info(("Successfully deleted old access keys for {0} "
                         "iam user").format(iam_user_name))
        except Exception as e:
            LOGGER.error(("Failed to delete old access keys for {0} iam user."
                          " Error: {1}").format(iam_user_name, str(e)))
    else:
        LOGGER.error(("An error occured while updating the tool with new "
                      "keys for {0} iam user. Skipping deletion of old "
                      "access keys because they are still in use. "
                      " Now iam user has 2 access keys. Need to"
                      " manually update corresponding tool with new "
                      "keys and delete old iam keys.").format(iam_user_name))
