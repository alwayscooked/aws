import pandas as pd
import boto3, pathlib

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
        return 0

    def delete_key(self, name:str):
        ec2 = boto3.client('ec2')
        response = ec2.delete_key_pair(KeyName=name)
        print(response)
        return 0

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

    def change_sec_group(self,id_sec_group, proto, port, ip_cidr): 
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
            s3.create_bucket(Bucket=name,CreateBucketConfiguration=location)
        elif op.lower()=='remove':
            s3.delete_bucket(Bucket=name)
        else:
            raise Exception("Unknown operation!")

        return 0

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
        s3.delete_object(Bucket=bucket, Key=filename)

    def remove_folder(self, bucket, filename): 
        list_of_files = list((self.get_list(bucket)).keys())
        for i in list_of_files:
            if filename in i:
                self.remove_file(bucket,i)  

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

def main():
    a = DynamoDB()
    # a.create_table('table1','id','N')
    print(a.scan('table1'))

if __name__=="__main__":
    main()