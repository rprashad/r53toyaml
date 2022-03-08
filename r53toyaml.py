#!/usr/bin/env python3

import boto3, yaml
from pprint import pprint

class R53toyaml(object):

    def __init__(self, client):
        self.client = client

    def fetch_results(self, **kwargs):
        command = kwargs['command']
        del(kwargs['command'])
        paginator = self.client.get_paginator(command)

        results = []
        page_iterator = paginator.paginate(**kwargs)
        for page in page_iterator:
            results.append(page)

        return results

    def get_public_zones(self):
        zones = self.fetch_results(command='list_hosted_zones')
        public = {}
        for zone in zones[0]['HostedZones']:
            if zone['Config']['PrivateZone'] == False:
                public.update({zone['Name'] : zone['Id']})
        return public

    def _get_resource_values(self, rvalues, rtype):
        if rtype == "mx":
            mx = []
            for x in rvalues:
                for k,v in x.items():
                    v = v.split("\t")
                    if len(v) == 1:
                        v = v[0].split(" ")
                    mx.append({ 'preference' : v[0], 'exchange' : v[1] })
            return mx
        else:
            return [ v for x in rvalues for k,v in x.items() ]

    def get_record_sets(self, zones):

        raw_records = {}
        records = {}
        for name, host_id in zones.items():
            raw_records[name] = self.fetch_results(command='list_resource_record_sets', HostedZoneId=host_id)

        for name, data in raw_records.items():
            name = name.rstrip('.')
            if name not in records:
                records[name] =  {'soa' : '*default_soa', 'records' : { "a" : {}, "mx" : {}, "ns" : {}, "caa" : {}, "ptr" : {}, "txt" : {}, "soa" : {}, "srv" : {}, "aaaa" : {}, "cname" : {}} }
            for page in data:
                sets = (page['ResourceRecordSets'])
                for s in sets:
                    if (name == s['Name'].rstrip('.')):
                        rname = "@"
                    else:
                        rname= '.'.join(s['Name'].split(".")[:-3])
                    alias = True if "AliasTarget" in s else False
                    rtype = s['Type'].lower() if not alias else "cname"
                    rtype = "txt" if s['Type'] == 'SPF' else rtype
                    ttl   = s['TTL'] if 'TTL' in s else 60
                    rr    = self._get_resource_values(s['ResourceRecords'], rtype) if not alias else s["AliasTarget"]["DNSName"]
                    rr = [rr] if type(rr) == str else rr
                    data = {}
                    if (rtype == "cname"):
                        data = {'ttl': ttl, 'record': rr[0]}
                    else:
                        data = {'ttl': ttl, 'records': rr}

                    if not ((rname == '@') and (rtype == "soa" or rtype == "ns")):
                        if rname not in records[name]['records'][rtype]:
                            records[name]['records'][rtype].update({rname : data})

        return { 'public' : records }

client = boto3.client('route53')
r2y = R53toyaml(client)
print(yaml.dump(r2y.get_record_sets(r2y.get_public_zones())))

