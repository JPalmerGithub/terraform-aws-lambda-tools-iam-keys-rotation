#!/usr/bin/env python3

import boto3
import json
import hvac
from retrying import retry

from common import LOGGER, get_ssm_value, SSM_PATH_FOR_IAM_VAULT_INFO, \
    SSM_KEY_FOR_VAULE_API, get_current_access_key_id, create_new_iam_keys, \
    delete_old_iam_keys, WriteToVaultFailedException


@retry(wait_exponential_multiplier=1000, wait_exponential_max=10000,
       stop_max_delay=30000)
def update_vault_key(vault_key, vault_value, vault_token):
    vault_url = "https://vault-tools.onemedical.io:8200"
    try:
        hvac_client = hvac.Client(url=vault_url, token=vault_token)
        hvac_client.write(vault_key, value=vault_value)
        LOGGER.info("Successfully updated {0} vault".format(vault_key))
    except Exception as e:
        LOGGER.error(("Failed to write to {0} vault"
                      ": {1}").format(vault_key, str(e)))

        raise WriteToVaultFailedException(e)


def write_iam_keys_to_vault(vault_info_list, new_access_key_id, new_secret_key,
                            current_access_key_id, vault_token):

    update_vault_success = True

    for vault_info in vault_info_list:
        try:
            access_key_vault = vault_info["AccessKeyVaultName"]
            secret_key_vault = vault_info["SecretKeyVaultName"]
        except KeyError:
            update_vault_success = False
            LOGGER.error("IAM to vault mapping in ssm is not correct")
            continue

        # Update access key id to vault
        try:
            update_vault_key(access_key_vault, new_access_key_id, vault_token)
        except WriteToVaultFailedException as e:
            update_vault_success = False
            LOGGER.error(("Failed to update access key id. Skipping secret key"
                          " updation. Error: {0}").format(str(e)))
            continue

        # Update secret key to vault
        try:
            update_vault_key(secret_key_vault, new_secret_key, vault_token)
        except WriteToVaultFailedException as e:
            update_vault_success = False
            LOGGER.error(("Access key was updated but secret key updation "
                          "failed. Reverting access key to previous value."
                          "Error: {0}").format(str(e)))

            try:
                update_vault_key(access_key_vault, current_access_key_id,
                                 vault_token)
            except WriteToVaultFailedException as e:
                LOGGER.error(("Access key id revert failed. Now access key id"
                              "and secret key belongs to different iam keys."
                              "This will cause corresponding tool to fail."
                              "Error: {0}").format(str(e)))
                # TODO: send a message to slack channel pd-infrastructure

    return update_vault_success


def rotate_vault_keys(iam_user_name):
    LOGGER.info(("Performing vault key rotation for:"
                 " {0}").format(iam_user_name))

    iam_client = boto3.client("iam")

    # Get current access keys
    current_access_key_id = get_current_access_key_id(iam_client,
                                                      iam_user_name)

    # Fetch vault info where given iam user is being used
    vault_info_ssm_key = "{0}/{1}".format(SSM_PATH_FOR_IAM_VAULT_INFO,
                                          iam_user_name)

    vault_info_list = json.loads(get_ssm_value(vault_info_ssm_key))

    # fetch vault token key from ssm
    vault_token = get_ssm_value(SSM_KEY_FOR_VAULE_API)

    # Create new iam keys
    new_access_key_id, new_secret_key = create_new_iam_keys(iam_client,
                                                            iam_user_name)

    # Update vault with new iam keys
    update_vault_success = write_iam_keys_to_vault(vault_info_list,
                                                   new_access_key_id,
                                                   new_secret_key,
                                                   current_access_key_id,
                                                   vault_token)

    # Delete old iam access keys
    delete_old_iam_keys(iam_client, iam_user_name,
                        current_access_key_id, update_vault_success)
