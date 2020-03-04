"""
Creates, updates, and deletes a job object.
"""

from os import path
import os

import yaml
import uuid

from kubernetes import client, config

JOB_NAME='omicidx-biosample-j' + str(uuid.uuid4().hex)[0:5]

def create_job_object():
    # Configureate Pod template container

    # volume inside of which you put your service account
    # This is the secret name, basically
    volume_name = "google-cloud-json" 
    google_app_credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')

    # create a volume mount
    volume_mount = client.V1VolumeMount(
        mount_path = '/etc/stuff',
        name=volume_name
        )

    # Create environment variables for container.
    # In this case, grab the values from the execution environment
    # perhaps using something like a .env file. 
    env = [
           client.V1EnvVar(
               name='GOOGLE_APPLICATION_CREDENTIALS',
               # note this is a path + the filename of the app creds in the secret
               value='/etc/stuff/key.json'), # google_app_credentials_path),
           client.V1EnvVar(
               name='GCS_STAGING_URL',
               value=os.environ.get('GCS_STAGING_URL')),
           client.V1EnvVar(
               name='GCS_EXPORT_URL',
               value=os.environ.get('GCS_EXPORT_URL')),
           client.V1EnvVar(
               name='ES_HOST',
               value=os.environ.get('ES_HOST'))
               ]

    # Create a volume.
    # This will go into the spec section of the template
    # Note that this specifies a secret volume
    # The secret needs to be created separately.
    volume = client.V1Volume(
        name=volume_name,
        secret=client.V1SecretVolumeSource(secret_name='google-cloud-json')
        )

    # Create the container section that will
    # go into the spec section
    container = client.V1Container(
        name="omicidx-builder",
        image="seandavi/omicidx-builder",
        volume_mounts=[volume_mount],
        env=env,
        command = ['/bin/bash','/code/biosample_pipeline.sh'])

    # Create and configurate a spec section
    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={"app": "omicidx-builder"}),
        spec=client.V1PodSpec(restart_policy="Never",
                              volumes=[volume],
                              containers=[container]))
    # Create the specification of deployment
    spec = client.V1JobSpec(
        template=template,
        backoff_limit=4)
    # Instantiate the job object
    job = client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(name=JOB_NAME),
        spec=spec)

    return job


def create_job(api_instance, job):
    api_response = api_instance.create_namespaced_job(
        body=job,
        namespace="default")
    print("Job created. status='%s'" % str(api_response.status))


# this is just here for completeness and is not used
def update_job(api_instance, job):
    # Update container image
    job.spec.template.spec.containers[0].image = "perl"
    api_response = api_instance.patch_namespaced_job(
        name=JOB_NAME,
        namespace="default",
        body=job)
    print("Job updated. status='%s'" % str(api_response.status))


def delete_job(api_instance):
    api_response = api_instance.delete_namespaced_job(
        name=JOB_NAME,
        namespace="default",
        body=client.V1DeleteOptions(
            propagation_policy='Foreground',
            grace_period_seconds=5))
    print("Job deleted. status='%s'" % str(api_response.status))


def main():
    # Configs can be set in Configuration class directly or using helper
    # utility. If no argument provided, the config will be loaded from
    # default location.
    config.load_kube_config()
    batch_v1 = client.BatchV1Api()
    # Create a job object with client-python API. The job we
    # created is same as the `pi-job.yaml` in the /examples folder.
    job = create_job_object()

    create_job(batch_v1, job)

    print(job)

    #update_job(batch_v1, job)

    #delete_job(batch_v1)


if __name__ == '__main__':
    main()
