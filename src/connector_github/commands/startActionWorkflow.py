import json
import requests
import time
import uuid
import datetime

from typing import Any
from typing import Dict
from typing import Optional
from typing import Tuple

# Your workflow yml will need to be set up like: https://stackoverflow.com/a/69500478/6090676
# we require an input with the name: workflow_cross_reference_id
class StartActionWorkflow:
    def __init__(
        self,
        github_repo_api_url: str,
        workflow_id: str,
        token: str,
        additional_workflow_inputs: Optional[dict] = None,
        github_ref: Optional[str] = "main",
    ):
        self.github_repo_api_url = github_repo_api_url
        self.workflow_id = workflow_id
        self.token = token
        self.additional_workflow_inputs = additional_workflow_inputs or {}
        self.github_ref = github_ref

    # this is one of the API methods we hit
    # https://docs.github.com/en/rest/actions/workflows?apiVersion=2022-11-28#create-a-workflow-dispatch-event
    def execute(self, config, task_data):
        try:
            authHeader = { "Authorization": f"Token {self.token}" }
            
            # generate a random id
            workflow_cross_reference_id = str(uuid.uuid4())

            # filter runs that were created after this date minus 5 minutes
            delta_time = datetime.timedelta(minutes=5)
            run_date_filter = (datetime.datetime.utcnow() - delta_time).strftime("%Y-%m-%dT%H:%M") 

            github_inputs = {**self.additional_workflow_inputs, **{"workflow_cross_reference_id": workflow_cross_reference_id}}

            post_response = requests.post(
                f"{self.github_repo_api_url}/actions/workflows/{self.workflow_id}/dispatches",
                headers=authHeader,
                json={
                    "ref": self.github_ref,
                    "inputs": github_inputs,
                }
            )
            post_response.raise_for_status()

            run_url = None
            while run_url is None:
                run_list_response = requests.get(f"{self.github_repo_api_url}/actions/runs?created=%3E{run_date_filter}",
                    headers = authHeader)
                run_list_response.raise_for_status()
                runs = run_list_response.json()["workflow_runs"]
            
                if len(runs) > 0:
                    for workflow in runs:
                        jobs_url = workflow["jobs_url"]
            
                        job_list_response = requests.get(jobs_url, headers= authHeader)
                        job_list_response.raise_for_status()

                        jobs = job_list_response.json()["jobs"]
                        if len(jobs) > 0:
                            # we only take the first job, edit this if you need multiple jobs
                            job = jobs[0]
                            steps = job["steps"]
                            if len(steps) >= 2:
                                second_step = steps[1] # if you have position the workflow_cross_reference_id step at 1st position
                                if second_step["name"] == workflow_cross_reference_id:
                                    run_url = job["run_url"]
                            else:
                                time.sleep(3)
                        else:
                            time.sleep(3)
                else:
                    time.sleep(3)

            status_code = 200
            response = {"run_url": run_url}

        except requests.exceptions.HTTPError as ex:
            status_code = ex.response.status_code
            response = json.dumps({"error": str(ex.response.text)})
        except Exception as ex:
            status_code = 500
            response = json.dumps({"error": str(ex)})

        return ({
            "response": response,
            "status": status_code,
            "mimetype": "application/json",
        })
