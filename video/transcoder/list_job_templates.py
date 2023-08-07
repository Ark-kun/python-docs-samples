#!/usr/bin/env python

# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Google Cloud Transcoder sample for listing job templates in a location.

Example usage:
    python list_job_templates.py --project_id <project-id> --location <location>
"""

# [START transcoder_list_job_templates]

import argparse

from google.cloud.video.transcoder_v1.services.transcoder_service import (
    pagers,
    TranscoderServiceClient,
)


def list_job_templates(
    project_id: str,
    location: str,
) -> pagers.ListJobTemplatesPager:
    """Lists all job templates in a location.

    Args:
        project_id: The GCP project ID.
        location: The location of the templates.

    Returns:
        An iterable object containing job template resources.
    """

    client = TranscoderServiceClient()

    parent = f"projects/{project_id}/locations/{location}"
    response = client.list_job_templates(parent=parent)
    print("Job templates:")
    for jobTemplate in response.job_templates:
        print({jobTemplate.name})

    return response


# [END transcoder_list_job_templates]

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project_id", help="Your Cloud project ID.", required=True)
    parser.add_argument(
        "--location", help="The location of the templates.", required=True
    )
    args = parser.parse_args()
    list_job_templates(args.project_id, args.location)
