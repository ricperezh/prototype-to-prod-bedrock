import boto3
import cfnresponse

def handler(event, context):
    try:
        if event['RequestType'] in ['Create', 'Update']:
            bedrock = boto3.client('bedrock-agent')
            agent_id = event['ResourceProperties']['AgentId']
            
            # Create a new version from DRAFT
            version_response = bedrock.create_agent_version(
                agentId=agent_id,
                agentVersion='1.0'
            )
            
            # Create the alias pointing to the new version
            alias_response = bedrock.create_agent_alias(
                agentId=agent_id,
                agentAliasName='prod',
                routingConfiguration={
                    'routingStrategy': 'CAPACITY'
                }
            )
            
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {
                'AliasArn': alias_response['agentAliasArn']
            })
        else:
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
            
    except Exception as e:
        print(f"Error: {str(e)}")
        cfnresponse.send(event, context, cfnresponse.FAILED, {'Error': str(e)})
