#!/usr/bin/env python3

import json
import urllib
import boto3
from retrying import retry
from common import LOGGER, CircleCiUpdateFailedException, get_ssm_value, \
    SSM_PATH_FOR_IAM_CIRCLECI_INFO, SSM_KEY_FOR_CIRCLECI_API, \
    delete_old_iam_keys, create_new_iam_keys, get_current_access_key_id


@retry(wait_exponential_multiplier=1000, wait_exponential_max=10000,
       stop_max_delay=30000)
def _update_circleci_env_var(token_key, project_name,
                             env_var_name, env_var_value):

    create_url = ("https://circleci.com/api/v1.1/project/github/onemedical/{0"
                  "}/envvar?circle-token={1}").format(project_name, token_key)

    data = {"name": env_var_name, "value": env_var_value}

    try:
        data = urllib.parse.urlencode(data).encode('utf-8')
        post_req = urllib.request.Request(create_url,
                                          data=data, method="POST")

        response = urllib.request.urlopen(post_req)
        LOGGER.info(("Successfully updated {0} circleci env var {1}: "
                     "{2}").format(project_name, env_var_name,
                                   response.read().decode("utf8")))

    except Exception as e:
        LOGGER.error(("Error updating circleci env var {0} with new keys"
                      ": {1}").format(env_var_name, str(e)))

        raise CircleCiUpdateFailedException(e)


def _update_circleci(circleci_info_list, new_access_key_id, new_secret_key,
                     current_access_key_id, circleci_token_key):

    update_circleci_success = True

    for circleci_info in circleci_info_list:
        try:
            circleci_project_name = circleci_info["CircleciProjectName"]
            access_key_env_var_name = circleci_info["AccessKeyEnvVarName"]
            secret_key_env_var_name = circleci_info["SecretKeyEnvVarName"]
        except KeyError:
            update_circleci_success = False
            LOGGER.error("IAM to circleci mapping in ssm is not correct")
            continue

        # Update access key id in circleci environment variable
        try:
            _update_circleci_env_var(circleci_token_key, circleci_project_name,
                                     access_key_env_var_name,
                                     new_access_key_id)

        except CircleCiUpdateFailedException as e:
            update_circleci_success = False
            LOGGER.error(("Failed to update access key id. Skipping secret key"
                          " updation. Error: {0}").format(str(e)))

            continue

        # Update secret key in circleci environment variable
        try:
            _update_circleci_env_var(circleci_token_key, circleci_project_name,
                                     secret_key_env_var_name, new_secret_key)
        except CircleCiUpdateFailedException as e:
            update_circleci_success = False
            LOGGER.error(("Access key was updated but secret key updation "
                          "failed. Reverting access key to previous value."
                          "Error: {0}").format(str(e)))

            try:
                _update_circleci_env_var(circleci_token_key,
                                         circleci_project_name,
                                         access_key_env_var_name,
                                         current_access_key_id)

            except CircleCiUpdateFailedException as e:
                LOGGER.error(("Access key id revert failed. Now access key id"
                              "and secret key belongs to different iam keys."
                              "This will cause circleci build failures."
                              "Error: {0}").format(str(e)))
                # TODO: send a message to slack channel pd-infrastructure

    return update_circleci_success


def rotate_circleci_keys(iam_user_name):
    LOGGER.info(("Performing circleci key rotation for:"
                 " {0}").format(iam_user_name))

    iam_client = boto3.client("iam")

    # Get current access keys
    current_access_key_id = get_current_access_key_id(iam_client,
                                                      iam_user_name)

    # Fetch all circleci jobs info where given iam user is being used
    circleci_info_ssm_key = "{0}/{1}".format(SSM_PATH_FOR_IAM_CIRCLECI_INFO,
                                             iam_user_name)

    circleci_info_list = json.loads(get_ssm_value(circleci_info_ssm_key))

    # Fetch circleci api token key from ssm
    circleci_token_key = get_ssm_value(SSM_KEY_FOR_CIRCLECI_API)

    # Create new iam keys
    new_access_key_id, new_secret_key = create_new_iam_keys(iam_client,
                                                            iam_user_name)

    # Update circleci environment variables
    update_circleci_success = _update_circleci(circleci_info_list,
                                               new_access_key_id,
                                               new_secret_key,
                                               current_access_key_id,
                                               circleci_token_key)

    # Delete old iam access keys
    delete_old_iam_keys(iam_client, iam_user_name,
                        current_access_key_id, update_circleci_success)
