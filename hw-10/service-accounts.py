def GenerateConfig(context):
    project_id = context.env['project']
    service_account = context.properties['service-account']

    resources = [
        {
            'name': service_account,
            'type': 'iam.v1.serviceAccount',
            'properties': {
                'accountId': service_account,
                'displayName': service_account,
                'projectId': project_id
            }
        },
        {
            'name': 'bind-iam-policy-log',
            'type': 'gcp-types/cloudresourcemanager-v1:virtual.projects.iamMemberBinding',
            'properties': {
                'resource': project_id,
                'role': 'roles/logging.logWriter',
                'member': 'serviceAccount:$(ref.' + service_account + '.email)'
            },
            'metadata': {
                'dependsOn': [service_account]
            }
        },
        {
            'name': 'bind-iam-policy-pubsub',
            'type': 'gcp-types/cloudresourcemanager-v1:virtual.projects.iamMemberBinding',
            'properties': {
                'resource': project_id,
                'role': 'roles/pubsub.admin',
                'member': 'serviceAccount:$(ref.' + service_account + '.email)'
            },
            'metadata': {
                'dependsOn': [service_account]
            }
        },
        {
            'name': 'bind-iam-policy-sql',
            'type': 'gcp-types/cloudresourcemanager-v1:virtual.projects.iamMemberBinding',
            'properties': {
                'resource': project_id,
                'role': 'roles/cloudsql.admin',
                'member': 'serviceAccount:$(ref.' + service_account + '.email)'
            },
            'metadata': {
                'dependsOn': [service_account]
            }
        },
        {
            'name': 'bind-iam-policy-sm',
            'type': 'gcp-types/cloudresourcemanager-v1:virtual.projects.iamMemberBinding',
            'properties': {
                'resource': project_id,
                'role': 'roles/secretmanager.admin',
                'member': 'serviceAccount:$(ref.' + service_account + '.email)'
            },
            'metadata': {
                'dependsOn': [service_account]
            }
        }
    ]

    return {'resources': resources}