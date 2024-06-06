#!/usr/bin/env python3

import argparse
import logging
from datetime import datetime, timedelta
import os
import boto3
import nagiosplugin
from botocore.config import Config

my_config = Config(
    retries = {
        'max_attempts': 10,
        'mode': 'standard'
    }
)

class CloudWatchBase(nagiosplugin.Resource):

    def __init__(self, namespace, metric, dimensions, statistic, period, lag, region=None):
        self.namespace = namespace
        self.metric = metric
        self.dimensions = dimensions
        self.statistic = statistic
        self.period = int(period)
        self.lag = int(lag)
        if region:
            self.region = region
        else:
            self.region = boto3.Session().region_name

    def _connect(self):
        try:
            self._cw
        except AttributeError:
            self._cw = boto3.client('cloudwatch', region_name=self.region, config=my_config)
        return self._cw


class CloudWatchMetric(CloudWatchBase):

    def probe(self):
        logging.info('getting stats from cloudwatch')
        cw = self._connect()
        start_time = datetime.utcnow() - timedelta(seconds=self.period) - timedelta(seconds=self.lag)
        logging.info(start_time)
        end_time = datetime.utcnow()
        stats = []
        stats = cw.get_metric_statistics(
            Period=self.period,
            StartTime=start_time,
            EndTime=end_time,
            MetricName=self.metric,
            Namespace=self.namespace,
            Statistics=[self.statistic],
            Dimensions=[self.dimensions])
        if len(stats['Datapoints']) == 0:
            return []
        stat = stats['Datapoints'][0]
        return [nagiosplugin.Metric(self.metric, int(stat[self.statistic]), stat['Unit'])]


class CloudWatchRatioMetric(nagiosplugin.Resource):

    def __init__(self, dividend_namespace, dividend_metric, dividend_dimension, dividend_statistic, period, lag,
                 divisor_namespace, divisor_metric, divisor_dimension, divisor_statistic, region):
        self.dividend_metric = CloudWatchMetric(
            dividend_namespace, dividend_metric, dividend_dimension, dividend_statistic, int(period), int(lag), region)
        self.divisor_metric = CloudWatchMetric(
            divisor_namespace, divisor_metric, divisor_dimension, divisor_statistic, int(period), int(lag), region)

    def probe(self):
        dividend = self.dividend_metric.probe()[0]
        divisor = self.divisor_metric.probe()[0]

        ratio_unit = '%s / %s' % (dividend.uom, divisor.uom)

        return [nagiosplugin.Metric('cloudwatchmetric', dividend.value / divisor.value, ratio_unit)]


class CloudWatchDeltaMetric(CloudWatchBase):

    def __init__(self, namespace, metric, dimensions, statistic, period, lag, delta, region):
        super(CloudWatchDeltaMetric, self).__init__(namespace, metric, dimensions, statistic, period, lag, region)
        self.delta = delta

    def probe(self):
        logging.info('getting stats from cloudwatch')
        cw = self._connect()

        datapoint1_start_time = (datetime.utcnow() - timedelta(seconds=self.period) - timedelta(seconds=self.lag)) - timedelta(seconds=self.delta)
        datapoint1_end_time = datetime.utcnow() - timedelta(seconds=self.delta)
        datapoint1_stats = cw.get_metric_statistics(
            Period=self.period,
            StartTime=datapoint1_start_time,
            EndTime=datapoint1_end_time,
            MetricName=self.metric,
            Namespace=self.namespace,
            Statistics=[self.statistic],
            Dimensions=self.dimensions)

        datapoint2_start_time = datetime.utcnow() - timedelta(seconds=self.period) - timedelta(seconds=self.lag)
        datapoint2_end_time = datetime.utcnow()
        datapoint2_stats = cw.get_metric_statistics(
            Period=self.period,
            StartTime=datapoint2_start_time,
            EndTime=datapoint2_end_time,
            MetricName=self.metric,
            Namespace=self.namespace,
            Statistics=[self.statistic],
            Dimensions=self.dimensions)

        if len(datapoint1_stats['Datapoints']) == 0 or len(datapoint2_stats['Datapoints']) == 0:
            return []

        datapoint1_stat = datapoint1_stats['Datapoints'][0]
        datapoint2_stat = datapoint2_stats['Datapoints'][0]
        num_delta = datapoint2_stat[self.statistic] - datapoint1_stat[self.statistic]
        per_delta = (100 / datapoint2_stat[self.statistic]) * num_delta
        return [nagiosplugin.Metric('cloudwatchmetric', per_delta, '%')]


class CloudWatchMetricSummary(nagiosplugin.Summary):

    def __init__(self, namespace, metric, dimensions, statistic):
        self.namespace = namespace
        self.metric = metric
        self.dimensions = dimensions
        self.statistic = statistic

    def ok(self, results):
        full_metric = '%s:%s' % (self.namespace, self.metric)
        return '%s' % self.metric

    def problem(self, results):
        full_metric = '%s:%s' % (self.namespace, self.metric)
        return '%s' % self.metric


class CloudWatchMetricRatioSummary(nagiosplugin.Summary):

    def __init__(self, dividend_namespace, dividend_metric, dividend_dimensions, dividend_statistic, divisor_namespace,
                 divisor_metric, divisor_dimensions, divisor_statistic):
        self.dividend_namespace = dividend_namespace
        self.dividend_metric = dividend_metric
        self.dividend_dimensions = dividend_dimensions
        self.dividend_statistic = dividend_statistic
        self.divisor_namespace = divisor_namespace
        self.divisor_metric = divisor_metric
        self.divisor_dimensions = divisor_dimensions
        self.divisor_statistic = divisor_statistic

    def ok(self, results):
        dividend_full_metric = '%s:%s' % (self.dividend_namespace, self.dividend_metric)
        divisor_full_metric = '%s:%s' % (self.divisor_namespace, self.divisor_metric)
        return 'Ratio: %s / %s' % (dividend_full_metric, divisor_full_metric)

    def problem(self, results):
        dividend_full_metric = '%s:%s' % (self.dividend_namespace, self.dividend_metric)
        divisor_full_metric = '%s:%s' % (self.divisor_namespace, self.divisor_metric)
        return 'Ratio: %s / %s' % (dividend_full_metric, divisor_full_metric)

class CloudWatchDeltaMetricSummary(nagiosplugin.Summary):

    def __init__(self, namespace, metric, dimensions, statistic, delta):
        self.namespace = namespace
        self.metric = metric
        self.dimensions = dimensions
        self.statistic = statistic
        self.delta = delta

    def ok(self, results):
        full_metric = '%s:%s' % (self.namespace, self.metric)
        return '%d seconds Delta %s' % (self.delta, self.metric)

    def problem(self, results):
        full_metric = '%s:%s' % (self.namespace, self.metric)
        return '%d seconds Delta %s' % (self.delta, self.metric)

class KeyValArgs(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        kvs = {}
        for pair in values.split(','):
            kv = pair.split('=')
            kvs[kv[0]] = kv[1]
        setattr(namespace, self.dest, kvs)

@nagiosplugin.guarded
def main():
    argp = argparse.ArgumentParser(description='Nagios plugin to check cloudwatch metrics')

    argp.add_argument('-n', '--namespace', required=True,
                      help='namespace for cloudwatch metric')
    argp.add_argument('--ec2name',
                      help='Valid only for EC2: this will find InstanceId by TAG name. Do not set -d if you use this option')
    argp.add_argument('-m', '--metric', required=True,
                      help='metric name')
    argp.add_argument('-d', '--dimensions', action=KeyValArgs,
                      help='dimensions of cloudwatch metric in the format dimension=value[,dimension=value...]')
    argp.add_argument('-s', '--statistic', choices=['Average','Sum','SampleCount','Maximum','Minimum'], default='Average',
                      help='statistic used to evaluate metric')
    argp.add_argument('-p', '--period', default=60, type=int,
                      help='the period in seconds over which the statistic is applied')
    argp.add_argument('-l', '--lag', default=0,
                      help='delay in seconds to add to starting time for gathering metric. useful for ec2 basic monitoring which aggregates over 5min periods')

    argp.add_argument('-r', '--ratio', default=False, action='store_true',
                      help='this activates ratio mode')
    argp.add_argument('--divisor-namespace',
                      help='ratio mode: namespace for cloudwatch metric of the divisor')
    argp.add_argument('--divisor-metric',
                      help='ratio mode: metric name of the divisor')
    argp.add_argument('--divisor-dimensions', action=KeyValArgs,
                      help='ratio mode: dimensions of cloudwatch metric of the divisor')
    argp.add_argument('--divisor-statistic', choices=['Average','Sum','SampleCount','Maximum','Minimum'],
                      help='ratio mode: statistic used to evaluate metric of the divisor')

    argp.add_argument('--delta', type=int,
                      help='time in seconds to build a delta mesurement')

    argp.add_argument('-w', '--warning', metavar='RANGE', default=0,
                      help='warning if threshold is outside RANGE')
    argp.add_argument('-c', '--critical', metavar='RANGE', default=0,
                      help='critical if threshold is outside RANGE')
    argp.add_argument('-v', '--verbose', action='count', default=0,
                      help='increase verbosity (use up to 3 times)')

    argp.add_argument('-R', '--region',
                      help='The AWS region to read metrics from')

    args=argp.parse_args()


    if args.verbose > 0:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        #logging.basicConfig(filename='/opt/omd/sites/teraaws/local/lib/nagios/plugins/check_cloudwatch.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    if args.namespace == 'AWS/EC2' and args.ec2name and not args.dimensions:
        logging.info(args.ec2name)
        ec2conn = connect_to_region(args.region)
        reservations = ec2conn.get_all_instances()
        for r in reservations:
            for i in r.instances:
                if "Name" in i.tags and args.ec2name == i.tags['Name'] and "running" in i.state:
                    args.dimensions = {'InstanceId' : str(i.id)}
                    break

        if not args.dimensions:
            logging.info("Could not convert EC2 Name to InstanceId")

    logging.info(args.dimensions)

    if args.ratio:
        metric = CloudWatchRatioMetric(args.namespace, args.metric, args.dimensions, args.statistic, args.period, args.lag, args.divisor_namespace,  args.divisor_metric, args.divisor_dimensions, args.divisor_statistic, args.region)
        summary = CloudWatchMetricRatioSummary(args.namespace, args.metric, args.dimensions, args.statistic, args.divisor_namespace,  args.divisor_metric, args.divisor_dimensions, args.divisor_statistic)
        check = nagiosplugin.Check(metric,nagiosplugin.ScalarContext('cloudwatchmetric', args.warning, args.critical),summary)
        check.main(verbose=args.verbose)

    elif args.delta:
        metric = CloudWatchDeltaMetric(args.namespace, args.metric, args.dimensions, args.statistic, args.period, args.lag, args.delta, args.region)
        summary = CloudWatchDeltaMetricSummary(args.namespace, args.metric, args.dimensions, args.statistic, args.delta)
        check = nagiosplugin.Check(metric,nagiosplugin.ScalarContext('cloudwatchmetric', args.warning, args.critical),summary)
        check.main(verbose=args.verbose)

    else:
        metric = CloudWatchMetric(args.namespace, args.metric, args.dimensions, args.statistic, args.period, args.lag, args.region)
        summary = CloudWatchMetricSummary(args.namespace, args.metric, args.dimensions, args.statistic)
        check = nagiosplugin.Check(metric,nagiosplugin.ScalarContext(args.metric, args.warning, args.critical),summary)
        check.main(verbose=args.verbose)

if __name__ == "__main__":
    main()