#!/usr/bin/env python3

import logging
import time
import json
import sys

from circleci_utils import rotate_circleci_keys
from vault_utils import rotate_vault_keys

from common import LOGGER, LOGGER_LEVEL, CIRCLECI_TOOL_NAME, \
    CONCOURSE_TOOL_NAME, BOSH_TOOL_NAME


def _rotate_keys_for_an_iam_user(iam_user_name, tool_name):

    if tool_name == CIRCLECI_TOOL_NAME:
        rotate_circleci_keys(iam_user_name)
    elif tool_name == CONCOURSE_TOOL_NAME or tool_name == BOSH_TOOL_NAME:
        rotate_vault_keys(iam_user_name)
    else:
        LOGGER.error("{0} tool is not supported.".format(tool_name))


def lambda_handler(event, context):
    '''
    Entry point for AWS Lambda
    '''
    start_t = time.time()
    iam_user_info = event.get("iam-user-info").split(":")
    iam_user_name = iam_user_info[0]
    iam_user_tool = iam_user_info[1]

    _rotate_keys_for_an_iam_user(iam_user_name, iam_user_tool)

    LOGGER.info(("Finished running key rotation script. Duration: "
                 "%d ms"), round(1000 * (time.time() - start_t), 2))


if __name__ == "__main__":
    logging.basicConfig(format="{%(levelname)s} {%(asctime)s %(pathname)s:"
                               "%(lineno)d} %(message)s", level=LOGGER_LEVEL)

    event = dict(json.loads(sys.argv[1]))
    lambda_handler(event, None)
