"""Google Cloud service definitions and command templates."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class GCService(Enum):
    GCS = "cloud_storage"
    COMPUTE = "compute_engine"
    KUBERNETES = "kubernetes"
    BIGQUERY = "bigquery"
    IAM = "iam"
    NETWORKING = "networking"
    CLOUD_RUN = "cloud_run"
    FUNCTIONS = "cloud_functions"
    PUBSUB = "pubsub"
    ARTFACTORY = "artifact_registry"
    SECRET_MANAGER = "secret_manager"
    SQL = "cloud_sql"
    DATAFLOW = "dataflow"
    SPANNER = "spanner"
    OTHER = "other"


SERVICE_COMMANDS: dict[GCService, dict[str, list[str]]] = {
    GCService.GCS: {
        "create_bucket": ["gsutil mb -p gs://BUCKET_NAME"],
        "list_buckets": ["gsutil ls"],
        "upload_file": ["gsutil cp FILE gs://BUCKET_NAME/"],
        "download_file": ["gsutil cp gs://BUCKET_NAME/FILE ."],
        "delete_object": ["gsutil rm gs://BUCKET_NAME/OBJECT"],
        "make_public": ["gsutil acl ch -u AllUsers:R gs://BUCKET_NAME/OBJECT"],
        "get_metadata": ["gsutil ls -l gs://BUCKET_NAME/"],
    },
    GCService.COMPUTE: {
        "list_instances": ["gcloud compute instances list"],
        "create_instance": ["gcloud compute instances create NAME --zone ZONE --machine-type TYPE"],
        "start_instance": ["gcloud compute instances start NAME --zone ZONE"],
        "stop_instance": ["gcloud compute instances stop NAME --zone ZONE"],
        "delete_instance": ["gcloud compute instances delete NAME --zone ZONE"],
        "describe_instance": ["gcloud compute instances describe NAME --zone ZONE"],
        "ssh_into": ["gcloud compute ssh NAME --zone ZONE"],
    },
    GCService.KUBERNETES: {
        "cluster_list": ["gcloud container clusters list"],
        "cluster_create": ["gcloud container clusters create NAME --zone ZONE"],
        "cluster_delete": ["gcloud container clusters delete NAME --zone ZONE"],
        "deploy_yaml": ["kubectl apply -f manifest.yaml"],
        "get_pods": ["kubectl get pods"],
        "get_deployments": ["kubectl get deployments"],
        "get_services": ["kubectl get services"],
        "describe_pod": ["kubectl describe pod POD_NAME"],
        "logs_pod": ["kubectl logs POD_NAME"],
    },
    GCService.BIGQUERY: {
        "list_datasets": ["bq ls"],
        "create_dataset": ["bq mk DATASET_NAME"],
        "run_query": ['bq query --use_legacy_sql=false "SELECT ..."'],
        "list_tables": ["bq ls DATASET_NAME"],
        "describe_table": ["bq show DATASET_NAME.TABLE"],
        "load_data": ["bq load --source_format=CSV DATASET.TABLE PATH_TO_FILE SCHEMA"],
    },
    GCService.IAM: {
        "add_role": ["gcloud projects add-iam-policy-binding PROJECT --member=MEMBER --role=ROLE"],
        "remove_role": ["gcloud projects remove-iam-policy-binding PROJECT --member=MEMBER --role=ROLE"],
        "list_bindings": ["gcloud projects get-iam-policy PROJECT"],
        "service_accounts": ["gcloud iam service-accounts list"],
        "create_sa": ["gcloud iam service-accounts create SA_NAME"],
    },
    GCService.NETWORKING: {
        "list_vpcs": ["gcloud compute networks list"],
        "create_vpc": ["gcloud compute networks create NAME"],
        "create_subnet": ["gcloud compute networks subnets create NAME --network VPC --region REGION --range RANGE"],
        "list_firewall_rules": ["gcloud compute firewall-rules list"],
        "create_firewall": ["gcloud compute firewall-rules create NAME --allow PROTOCOL:PORT"],
    },
    GCService.CLOUD_RUN: {
        "list_services": ["gcloud run services list"],
        "deploy_service": ["gcloud run deploy NAME --image IMAGE --platform managed"],
        "invoke_service": ["gcloud run services invoke NAME"],
        "describe_service": ["gcloud run services describe NAME"],
    },
    GCService.FUNCTIONS: {
        "list_functions": ["gcloud functions list"],
        "deploy_function": ["gcloud functions deploy NAME --runtime RUNTIME --trigger-http"],
        "invoke_function": ["curl FUNCTION_URL"],
        "delete_function": ["gcloud functions delete NAME"],
    },
    GCService.PUBSUB: {
        "list_topics": ["gcloud pubsub topics list"],
        "create_topic": ["gcloud pubsub topics create TOPIC"],
        "create_subscription": ["gcloud pubsub subscriptions create SUB --topic TOPIC"],
        "publish_message": ['gcloud pubsub topics publish TOPIC --message="MSG"'],
        "delete_topic": ["gcloud pubsub topics delete TOPIC"],
    },
    GCService.ARTFACTORY: {
        "list_repos": ["gcloud artifacts repositories list"],
        "create_repo": ["gcloud artifacts repositories create REPO --repository-format=docker"],
        "push_image": ["gcloud artifacts docker push REGISTRY/project/repo TAG"],
        "list_images": ["gcloud artifacts images list REPO"],
    },
    GCService.SECRET_MANAGER: {
        "list_secrets": ["gcloud secrets list"],
        "create_secret": ["gcloud secrets create NAME"],
        "add_version": ['echo -n "VALUE" | gcloud secrets versions add NAME --data-file=-'],
        "access_secret": ["gcloud secrets versions access LATEST --secret=NAME"],
        "delete_secret": ["gcloud secrets delete NAME"],
    },
    GCService.SQL: {
        "list_instances": ["gcloud sql instances list"],
        "create_instance": ["gcloud sql instances create NAME --tier=db-n1-standard-1"],
        "connect": ["gcloud sql connect NAME --user=root"],
        "restore_backup": ["gcloud sql backups restore TIMESTAMP --instance=NAME"],
    },
}


def detect_gcp_service(text: str) -> list[GCService]:
    """Detect which GCP services are referenced in the text."""
    detected = set()
    service_patterns = {
        GCService.GCS: ["gsutil", "gs://", "google cloud storage", "storage bucket", "object storage"],
        GCService.COMPUTE: ["gcloud compute", "compute engine", "vm instance", "gce"],
        GCService.KUBERNETES: ["kubernetes", "gke", "k8s", "kubectl", "container cluster"],
        GCService.BIGQUERY: ["bigquery", "bq", "sql query"],
        GCService.IAM: ["iam", "service account", "policy binding", "permissions", "roles"],
        GCService.NETWORKING: ["vpc", "firewall", "network", "subnet", "cloud nat"],
        GCService.CLOUD_RUN: ["cloud run", "serverless", "container service"],
        GCService.FUNCTIONS: ["cloud function", "functions", "cloud functions"],
        GCService.PUBSUB: ["pub/sub", "pubsub", "message queue", "topic", "subscription"],
        GCService.ARTFACTORY: ["artifact registry", "docker registry", "container image"],
        GCService.SECRET_MANAGER: ["secret manager", "secrets"],
        GCService.SQL: ["cloud sql", "sql instance", "database"],
    }
    lower_text = text.lower()
    for service, patterns in service_patterns.items():
        if any(p in lower_text for p in patterns):
            detected.add(service)
    return list(detected)


def get_commands_for_service(service: GCService, operation: str) -> list[str]:
    """Get relevant commands for a specific service and operation."""
    svc_cmds = SERVICE_COMMANDS.get(service, {})
    cmd_map = {
        "create": f"create_{operation}" if operation else "create_instance",
        "delete": f"delete_{operation}" if operation else "delete_instance",
        "read": f"list_{operation}" if operation else "list_instances",
        "verify": f"get_metadata" if operation else "get_metadata",
    }
    key = cmd_map.get(operation, "list_instances")
    return svc_cmds.get(key, [])


def generate_suggested_commands(tasks, project: str, region: str, zone: str) -> list[str]:
    """Generate gcloud commands based on detected services and operations."""
    cmds = []
    services = set()
    for task in tasks:
        services.update(task.gcp_services or [])

    for service in services:
        for op in ("create", "read", "verify"):
            for cmd_template in get_commands_for_service(service, op):
                cmd = cmd_template
                if "PROJECT" in cmd:
                    cmd = cmd.replace("PROJECT", project)
                if "REGION" in cmd:
                    cmd = cmd.replace("REGION", region)
                if "ZONE" in cmd:
                    cmd = cmd.replace("ZONE", zone)
                cmds.append(cmd)
    return list(dict.fromkeys(cmds))[:20]
