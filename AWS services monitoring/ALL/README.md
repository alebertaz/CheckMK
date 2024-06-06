# check_cloudwatch.py

This is the Python3 and Boto3 converted version of the original Python2 and Boto2 "pmp-check-aws-rds" from GitHub user "vimeo":
https://github.com/vimeo/nagios-cloudwatch-plugin

Setup:
```
pip install nagios-cloudwatch-plugin
```

Usage example:
```
check_cloudwatch.sh --region=eu-west-1 --namespace="AmazonMQ" --dimensions="Name=Broker,Value=broker-dns" --metric="CpuUtilization" --statistics="Average" --mins=15 --warning=:70 --critical=:80
```

CheckMK install path:
```
/opt/omd/sites/(site)/local/lib/nagios/plugins/
```