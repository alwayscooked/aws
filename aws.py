import pandas as pd
import boto3, pathlib,argparse

class EC2:
    #KeyFormat='pem'|'ppk'
    def create_key(self, name, key_format='ppk'):
        ec2 = boto3.client('ec2')
        try:
            response = ec2.create_key_pair(KeyName=name, KeyFormat=key_format)
        except Exception as e:
            print(f"func create_key: ec2.create_key_pair - {e}!")
            return -1

        priv_key = response['KeyMaterial']
        with open(f'{name}.ppk','w') as fd:
            fd.write(priv_key)

        print("Key with name :"+name+" was created!")
        return response

    def delete_key(self, name:str):
        ec2 = boto3.client('ec2')
        response = ec2.delete_key_pair(KeyName=name)
        return response

    def create_instance(self, key_name, user_data:str = None):
        ec2_client = boto3.client('ec2')
        try:
            if not user_data:
                resp = ec2_client.run_instances(
                    ImageId='ami-03f71e078efdce2c9',
                    InstanceType='t3.micro',
                    KeyName=key_name,
                    MinCount=1,
                    MaxCount=1
                )
            
            else:
                resp = ec2_client.run_instances(
                    ImageId='ami-03f71e078efdce2c9',
                    InstanceType='t3.micro',
                    KeyName=key_name,
                    MinCount=1,
                    MaxCount=1,
                    UserData = user_data
                )
        except Exception as e:
            print(e)
            return -1
        
        print('Instance ID:',resp["Instances"][0]["InstanceId"])
        return resp

    def add_port(self,id_sec_group, proto, port, ip_cidr): 
        ec2 = boto3.client('ec2')
        resp = ec2.authorize_security_group_ingress(
            GroupId=id_sec_group,
            IpPermissions=[
                {
                    'FromPort': port,
                    'ToPort': port,
                    'IpProtocol':proto,
                    'IpRanges':[{'CidrIp': ip_cidr}]
                }
            ]
        )
        return resp

    def change_name(self, id, name):
        ec2 = boto3.client('ec2')
        try:
            resp  =ec2.create_tags(Resources=[id], Tags=[{"Key":"Name","Value":name}])
        
        except Exception as e:
            print(e)
            return -1
        
        return resp

    def add_tags(self, id, tags:dict[str:str]):
        ec2 = boto3.client('ec2')
        try:
            resp = ec2.create_tags(Resources=[id], Tags=[tags])
        except Exception as e:
            print(e)
            return -1
        
        return resp
        
    def get_info(self, id):
        ec2 = boto3.client('ec2')
        try:
            response = ec2.describe_instances(InstanceIds=[id])
        except Exception as e:
            print("func get_info: ",e)
            return -1
        res = {"Id: ":id,
        "State:": response['Reservations'][0]['Instances'][0]['State']['Name'],
        "Type:": response['Reservations'][0]['Instances'][0]['InstanceType'],
        "Public address:": response['Reservations'][0]['Instances'][0]['PublicIpAddress'],
        "Private address:": response['Reservations'][0]['Instances'][0]['PrivateIpAddress'],
        "Volume id: ": response['Reservations'][0]['Instances'][0]['BlockDeviceMappings'][0]['Ebs']['VolumeId'],
        "Security groups: ": response['Reservations'][0]['Instances'][0]['SecurityGroups']
        }
        return res

    def start(self, id, dryrun = False):
        ec2 = boto3.client('ec2')
        try:
            response = ec2.start_instances(InstanceIds=[id], DryRun=dryrun)
        except Exception as e:
            print("func start: ",e)
            return -1
        
        return response
        
    def stop(self, id, dryrun = False):
        ec2 = boto3.client('ec2')
        try:
            response = ec2.stop_instances(InstanceIds=[id], DryRun=dryrun)
            print(response)
        except Exception as e:
            print(f"func stop: {e}")
            return -1
        return response
    
    def terminate(self, id, dryrun = False):
        ec2 = boto3.client('ec2')
        try:
            response = ec2.terminate_instances(InstanceIds=[id], DryRun=dryrun)
            print(response)
        except Exception as e:
            print(f"func stop: {e}")
            return -1
        
        return response

class S3:

    def bucket(self,op:str, name:str, region:str='eu-north-1'):
        s3 = boto3.client('s3')
        if op.lower()=='create':
            location = {'LocationConstraint': region}    
            response = s3.create_bucket(Bucket=name,CreateBucketConfiguration=location)
        elif op.lower()=='remove':
            response = s3.delete_bucket(Bucket=name)
        else:
            raise Exception("Unknown operation!")

        return response 

    def upload_file(self, bucket, filename): 
        s3 = boto3.client('s3')
        with open(filename, 'rb') as data:
            s3.upload_fileobj(data, bucket, filename.replace('\\','/'))
        return 0        
    
    def upload_folder(self, bucket, folder):
        some_folder = pathlib.Path(folder)
        files = some_folder.rglob('*')
        for i in files:
            if i.is_file():
                self.upload_file(bucket,str(i))

    def get_list(self, bucket)->dict:
        s3 = boto3.client('s3')
        list_obj = s3.list_object_versions(Bucket=bucket)
        objects = {}
        for obj in list_obj["Versions"]:
            objects[obj['Key']] = {
                "Size:":obj['Size'],
                "StorageClass:":obj['StorageClass'],
                "VersionId":obj['VersionId']
            }

        return objects

    def download_file(self, bucket, filename)->dict:
        s3 = boto3.client('s3')
        obj = s3.get_object(Bucket=bucket,
                            Key=filename)
        
        return obj['Body']

    def make_file_public(self, bucket, filename):

        s3 = boto3.client('s3')
        resp = s3.put_bucket_policy(Bucket=bucket,
        Policy='{"Version": "2012-10-17", "Statement": [{ "Sid": "id-1","Effect": "Allow","Principal": "*", "Action": ["s3:GetObject"],"Resource": ["arn:aws:s3:::'+bucket+'/'+filename+'"]}]}')
        return resp
    
    def remove_file(self, bucket:str, filename:str): 
        s3 = boto3.client('s3')
        response = s3.delete_object(Bucket=bucket, Key=filename)
        return response

    def remove_folder(self, bucket, filename): 
        list_of_files = list((self.get_list(bucket)).keys())
        for i in list_of_files:
            if filename in i:
                self.remove_file(bucket,i)  
        
        return 0 

class DynamoDB:
    
    def create_table(self, name, hash_key_name, hash_type:str, sort_key_name=None, sort_type=None): 
        if not (sort_key_name and sort_type):
            dynamodb = boto3.resource('dynamodb')

            table = dynamodb.create_table(
                TableName=name,
                KeySchema=[
                    {
                        'AttributeName':hash_key_name,
                        'KeyType':'HASH'
                    },
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName':hash_key_name,
                        'AttributeType':hash_type
                    }
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            )

        else: 
            table = dynamodb.create_table(
                TableName=name,
                KeySchema=[
                    {
                        'AttributeName':hash_key_name,
                        'KeyType':'HASH'
                    },
                    {
                        'AttributeName':sort_key_name,
                        'KeyType':'RANGE'
                    },
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName':hash_key_name,
                        'AttributeType':hash_type
                    },
                    {
                        'AttributeName':sort_key_name,
                        'AttributeType':sort_type
                    }
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            )

        table.wait_until_exists()
        return table

    def insert_data(self,table,data:dict):
        client = boto3.client('dynamodb')
        response = client.put_item(
            TableName=table,
            Item=data
        )
        return response

    def insert_csv_data_from_s3(self,from_bucket,filename, to_table, hash_col_name='id', type_hash_col='N', number_of_rows=10,delimiter=','):
        s3 = S3()
        data = s3.download_file(from_bucket, filename)
        df = pd.read_csv(data, delimiter=delimiter)
        for i in range(number_of_rows):
            res = {hash_col_name:{str(type_hash_col):str(i)}}
            for j in df.columns:
                res[j] = {"S":str(df.loc[i][j])}

            self.insert_data(to_table, res)       

    def scan(self, table):
        client = boto3.client('dynamodb')
        resp = client.scan(TableName=table)
        return resp

    def delete_table(self, name):
        dynamodb = boto3.client('dynamodb')
        response = dynamodb.delete_table(TableName=name)
        return response

def main(service:str, operation:str, args:list):
    if service == 'ec2':
        ec2 = EC2()
        if operation=='create_key': 
            resp = ec2.create_key(*args)
        elif operation=='delete_key':
            resp = ec2.delete_key(*args)
        elif operation=='create_instance':
            resp = ec2.create_instance(*args)
        elif operation=='terminate_instance':
            resp = ec2.terminate(*args)
        elif operation=='start_instance':
            resp = ec2.start(*args)
        elif operation=='stop_instance':
            resp = ec2.stop(*args)
        elif operation=='add_port':
            resp = ec2.add_port(*args)
        elif operation=='change_name':
            resp = ec2.change_name(*args)
        elif operation=='add_tags':
            resp = ec2.add_tags(*args)
        elif operation=='get_info':
            resp = ec2.get_info(*args)
        print(resp)
         
    elif service == 's3':
        s3 = S3()
        if operation=='create_bucket':
            resp = s3.bucket('create', *args)
        elif operation=='delete_bucket':
            resp = s3.bucket('remove', *args)
        elif operation=='upload_file':
            resp = s3.upload_file(*args)
        elif operation=='upload_folder':
            resp = s3.upload_folder(*args)
        elif operation=='get_list':
            resp = s3.get_list(*args)
        elif operation=='make_file_public':
            resp = s3.make_file_public(*args)
        elif operation=='remove_file':
            resp = s3.remove_file(*args)
        elif operation=='remove_folder':
            resp = s3.remove_folder(*args)

        print(resp)
    elif service == 'dynamodb':
        dynamodb = DynamoDB()
        if operation=='create_table':
            resp = dynamodb.create_table(*args)
        elif operation=='insert_csv_data_from_s3':
            resp = dynamodb.insert_csv_data_from_s3(*args)
        elif operation=='get_data':
            resp = dynamodb.scan(*args)
        elif operation=='delete_table':
            resp = dynamodb.delete_table(*args)  
        print(resp)

    else: 
        print("Unknown service!")


if __name__=="__main__":
    parser = argparse.ArgumentParser(prog='AWS management system',
                                     description='Simple AWS MS, that maintain operation for so AWS service: EC2, S3, DynamoDB',
                                     usage='''python3 aws.py -h
python3 aws.py [service] [operation] [args]

Service: ec2, s3, dynamodb 
Service operations and args:
    ec2:
        create_key [name_key],[key_format] - create key with name_key, and key_format(optional); key_format can be: pem, ppk(default),
        delete_key [name_key] - delete key with name_key,
        create_instance [key_name],[user_data] - create instance with specified key_name and user_data(optional),
        terminate_instance [id_instance] - terminate instance with specified id,
        start_instance [id_instance] - start instance with specified id,
        stop_instance [id_instance] - stop instance with specified id,
        add_port [id_sec_group],[proto],[port],[ip_cidr] - add security group rule to 'Inbound rules' specified id_sec_group; proto - protocol(that will be use in inboard connection), ip_cidr - source ip in cidr format,
        change_name [id],[name] - change value of tag "Name",
        add_tags [id],[tags] - add info tag; Tag format dict[name_of_tag:value],
        get_info [id_instance] - get info about specified instance
    s3:
        create_bucket [name],[region] - create bucket with specified name and region(optional), 
        delete_bucket [name] - delete bucket with specified name,
        upload_file [bucket],[filename] - upload specified file to specified bucket,
        upload_folder [bucket],[folder] - upload specified folder to specified bucket,
        get_list [bucket] - get list of object specified bucket,
        make_file_public [bucket],[filename] - make file with filename public_read in specified bucket,
        remove_file [bucket],[filename] - remove specified file from specified bucket,
        remove_folder [bucket],[filename] - remove specified folder from specified bucket,
    dynamodb:
        create_table [name],[hash_key_name],[hash_type],[sort_key_name],[sort_type] - create table with specified name, hash key, and sort key(optional),
        insert_csv_data_from_s3 [from_bucket],[filename],[to_table],[hash_col_name],[type_hash_col],[number_of_rows],[delimiter] - insert csv entries from file in specified bucket to a table;
        get_data [name] - get data from table with specified name,
        delete_table [name] - delete table with specified name;
''')
    parser.add_argument("service", type=str ,help="So services can be here: ec2, s3, dynamodb")
    parser.add_argument("operation", type=str ,help="Read help")
    parser.add_argument("args",type=str, help="args for specific operation")
    args = parser.parse_args()
    print("Service:",args)
    print("Operation:",args.operation)
    print("Args:",args.args.split(','))
    args = vars(args)
    args['args'] = args['args'].split(',')
    main(**args)