# -*- coding: utf-8 -*-

#    Copyright 2013 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import json

from copy import deepcopy
from netaddr import IPNetwork

from nailgun.db.sqlalchemy.models import AllowedNetworks
from nailgun.db.sqlalchemy.models import Cluster
from nailgun.db.sqlalchemy.models import NetworkAssignment
from nailgun.test.base import BaseIntegrationTest
from nailgun.test.base import reverse


class TestClusterHandlers(BaseIntegrationTest):

    def test_assigned_networks_when_node_added(self):
        mac = '123'
        meta = self.env.default_metadata()
        self.env.set_interfaces_in_meta(
            meta,
            [{'name': 'eth0', 'mac': mac},
             {'name': 'eth1', 'mac': '654'}])

        node = self.env.create_node(api=True, meta=meta, mac=mac)
        self.env.create_cluster(api=True, nodes=[node['id']])

        resp = self.app.get(
            reverse('NodeNICsHandler', kwargs={'node_id': node['id']}),
            headers=self.default_headers)

        self.assertEquals(resp.status, 200)

        response = json.loads(resp.body)

        for resp_nic in response:
            if resp_nic['mac'] == mac:
                self.assertEquals(len(resp_nic['assigned_networks']), 1)
            else:
                self.assertGreater(len(resp_nic['assigned_networks']), 0)

    def test_allowed_networks_when_node_added(self):
        mac = '123'
        meta = self.env.default_metadata()
        self.env.set_interfaces_in_meta(
            meta,
            [{'name': 'eth0', 'mac': mac},
             {'name': 'eth1', 'mac': 'abc'}])
        node = self.env.create_node(api=True, meta=meta, mac=mac)
        self.env.create_cluster(api=True, nodes=[node['id']])

        resp = self.app.get(
            reverse('NodeNICsHandler', kwargs={'node_id': node['id']}),
            headers=self.default_headers)
        self.assertEquals(resp.status, 200)
        response = json.loads(resp.body)

        for resp_nic in response:
            self.assertGreater(len(resp_nic['allowed_networks']), 0)

    def test_assignment_is_removed_when_delete_node_from_cluster(self):
        mac = '123'
        meta = self.env.default_metadata()
        self.env.set_interfaces_in_meta(
            meta,
            [{'name': 'eth0', 'mac': mac},
             {'name': 'eth1', 'mac': 'abc'}])
        node = self.env.create_node(api=True, meta=meta, mac=mac)
        cluster = self.env.create_cluster(api=True, nodes=[node['id']])
        resp = self.app.put(
            reverse('ClusterHandler', kwargs={'cluster_id': cluster['id']}),
            json.dumps({'nodes': []}),
            headers=self.default_headers
        )
        self.assertEquals(resp.status, 200)

        resp = self.app.get(
            reverse('NodeNICsHandler', kwargs={'node_id': node['id']}),
            headers=self.default_headers)
        self.assertEquals(resp.status, 200)
        response = json.loads(resp.body)
        for resp_nic in response:
            self.assertEquals(resp_nic['assigned_networks'], [])
            self.assertEquals(resp_nic['allowed_networks'], [])

    def test_assignment_is_removed_when_delete_cluster(self):
        mac = '12364759'
        meta = self.env.default_metadata()
        self.env.set_interfaces_in_meta(
            meta,
            [{'name': 'eth0', 'mac': mac},
             {'name': 'eth1', 'mac': 'abc'}])
        node = self.env.create_node(api=True, meta=meta, mac=mac)
        cluster = self.env.create_cluster(api=True, nodes=[node['id']])
        cluster_db = self.db.query(Cluster).get(cluster['id'])
        self.db.delete(cluster_db)
        self.db.commit()

        net_assignment = self.db.query(NetworkAssignment).all()
        self.assertEquals(len(net_assignment), 0)
        allowed_nets = self.db.query(AllowedNetworks).all()
        self.assertEquals(len(allowed_nets), 0)


class TestNodeHandlers(BaseIntegrationTest):

    def test_network_assignment_when_node_created_and_added(self):
        cluster = self.env.create_cluster(api=True)
        mac = '123'
        meta = self.env.default_metadata()
        self.env.set_interfaces_in_meta(
            meta,
            [{'name': 'eth0', 'mac': mac},
             {'name': 'eth1', 'mac': '654'}])
        node = self.env.create_node(api=True, meta=meta, mac=mac,
                                    cluster_id=cluster['id'])
        resp = self.app.get(
            reverse('NodeNICsHandler', kwargs={'node_id': node['id']}),
            headers=self.default_headers)
        self.assertEquals(resp.status, 200)
        response = json.loads(resp.body)
        for resp_nic in response:
            if resp_nic['mac'] == mac:
                self.assertEquals(len(resp_nic['assigned_networks']), 1)
            else:
                self.assertGreater(len(resp_nic['assigned_networks']), 0)
            self.assertGreater(len(resp_nic['allowed_networks']), 0)

    def test_network_assignment_when_node_added(self):
        cluster = self.env.create_cluster(api=True)
        mac = '123'
        meta = self.env.default_metadata()
        self.env.set_interfaces_in_meta(
            meta,
            [{'name': 'eth0', 'mac': mac},
             {'name': 'eth1', 'mac': 'abc'}])
        node = self.env.create_node(api=True, meta=meta, mac=mac)
        resp = self.app.put(
            reverse('NodeCollectionHandler'),
            json.dumps([{'id': node['id'], 'cluster_id': cluster['id']}]),
            headers=self.default_headers
        )
        self.assertEquals(resp.status, 200)

        resp = self.app.get(
            reverse('NodeNICsHandler', kwargs={'node_id': node['id']}),
            headers=self.default_headers)
        self.assertEquals(resp.status, 200)
        response = json.loads(resp.body)
        for resp_nic in response:
            if resp_nic['mac'] == mac:
                self.assertEquals(len(resp_nic['assigned_networks']), 1)
            else:
                self.assertGreater(len(resp_nic['assigned_networks']), 0)
            self.assertGreater(len(resp_nic['allowed_networks']), 0)

    def test_assignment_is_removed_when_delete_node_from_cluster(self):
        cluster = self.env.create_cluster(api=True)
        mac = '123'
        meta = self.env.default_metadata()
        self.env.set_interfaces_in_meta(
            meta,
            [{'name': 'eth0', 'mac': mac},
             {'name': 'eth1', 'mac': 'abc'}])
        node = self.env.create_node(api=True, meta=meta, mac=mac,
                                    cluster_id=cluster['id'])
        resp = self.app.put(
            reverse('NodeCollectionHandler'),
            json.dumps([{'id': node['id'], 'cluster_id': None}]),
            headers=self.default_headers
        )
        self.assertEquals(resp.status, 200)

        resp = self.app.get(
            reverse('NodeNICsHandler', kwargs={'node_id': node['id']}),
            headers=self.default_headers)
        self.assertEquals(resp.status, 200)
        response = json.loads(resp.body)
        for resp_nic in response:
            self.assertEquals(resp_nic['assigned_networks'], [])
            self.assertEquals(resp_nic['allowed_networks'], [])

    def test_getting_default_nic_information_for_node(self):
        cluster = self.env.create_cluster(api=True)
        macs = ('123', 'abc')
        meta = self.env.default_metadata()
        self.env.set_interfaces_in_meta(
            meta,
            [{'name': 'eth0', 'mac': macs[0]},
             {'name': 'eth1', 'mac': macs[1]}])
        node = self.env.create_node(api=True, meta=meta, mac=macs[0],
                                    cluster_id=cluster['id'])
        resp = self.app.get(
            reverse('NodeNICsDefaultHandler', kwargs={'node_id': node['id']}),
            headers=self.default_headers
        )
        resp_macs = map(
            lambda interface: interface["mac"],
            json.loads(resp.body)
        )
        self.assertEquals(resp.status, 200)
        self.assertItemsEqual(macs, resp_macs)


class TestNodeNICAdminAssigning(BaseIntegrationTest):

    def test_admin_nic_and_ip_assignment(self):
        cluster = self.env.create_cluster(api=True)
        admin_ip = str(IPNetwork(
            self.env.network_manager.get_admin_network_group().cidr)[0])
        mac1, mac2 = '123', '321'
        meta = self.env.default_metadata()
        meta['interfaces'] = [{'name': 'eth0', 'mac': mac1},
                              {'name': 'eth1', 'mac': mac2, 'ip': admin_ip}]
        self.env.create_node(api=True, meta=meta, mac=mac1,
                             cluster_id=cluster['id'])
        node_db = self.env.nodes[0]
        self.assertEquals(node_db.admin_interface.mac, mac2)
        self.assertEquals(node_db.admin_interface.ip_addr, admin_ip)

        meta = deepcopy(node_db.meta)
        for interface in meta['interfaces']:
            if interface['mac'] == mac2:
                # reset admin ip for previous admin interface
                interface['ip'] = None
            elif interface['mac'] == mac1:
                # set new admin interface
                interface['ip'] = admin_ip

        resp = self.app.put(
            reverse('NodeCollectionHandler'),
            json.dumps([{'id': node_db.id,
                        'meta': meta,
                        'is_agent': True}]),
            headers=self.default_headers
        )
        self.assertEquals(resp.status, 200)

        self.db.refresh(node_db)
        self.assertEquals(node_db.admin_interface.mac, mac2)
        self.assertEquals(node_db.admin_interface.ip_addr, None)

        resp = self.app.put(
            reverse('NodeCollectionHandler'),
            json.dumps([{'id': node_db.id,
                         'cluster_id': None}]),
            headers=self.default_headers
        )
        self.assertEquals(resp.status, 200)

        self.db.refresh(node_db)
        self.assertEquals(node_db.admin_interface.mac, mac1)
        self.assertEquals(node_db.admin_interface.ip_addr, admin_ip)


class TestNodePublicNetworkToNICAssignment(BaseIntegrationTest):

    def create_node(self):
        meta = self.env.default_metadata()
        admin_ip = str(IPNetwork(
            self.env.network_manager.get_admin_network_group().cidr)[0])
        meta['interfaces'] = [{'name': 'eth3', 'mac': '000'},
                              {'name': 'eth2', 'mac': '111'},
                              {'name': 'eth0', 'mac': '222', 'ip': admin_ip},
                              {'name': 'eth1', 'mac': '333'}]
        return self.env.create_node(api=True, meta=meta,
                                    cluster_id=self.env.clusters[0].id)

    def test_nova_net_public_network_assigned_to_second_nic_by_name(self):
        self.env.create_cluster(api=True)
        node = self.create_node()

        resp = self.app.get(
            reverse('NodeNICsHandler', kwargs={'node_id': node['id']}),
            headers=self.default_headers)
        self.assertEquals(resp.status, 200)
        data = json.loads(resp.body)
        eth1 = [nic for nic in data if nic['name'] == 'eth1']
        self.assertEqual(len(eth1), 1)
        self.assertEqual(
            len(filter(lambda n: n['name'] == 'public',
                       eth1[0]['assigned_networks'])),
            1)

    def test_neutron_gre_public_network_assigned_to_second_nic_by_name(self):
        self.env.create_cluster(api=True,
                                net_provider='neutron',
                                net_segment_type='gre')
        node = self.create_node()

        resp = self.app.get(
            reverse('NodeNICsHandler', kwargs={'node_id': node['id']}),
            headers=self.default_headers)
        self.assertEquals(resp.status, 200)
        data = json.loads(resp.body)
        eth1 = [nic for nic in data if nic['name'] == 'eth1']
        self.assertEqual(len(eth1), 1)
        self.assertEqual(
            len(filter(lambda n: n['name'] == 'public',
                       eth1[0]['assigned_networks'])),
            1)

    def test_neutron_vlan_public_network_assigned_to_second_nic_by_name(self):
        self.env.create_cluster(api=True,
                                net_provider='neutron',
                                net_segment_type='vlan')
        node = self.create_node()

        resp = self.app.get(
            reverse('NodeNICsHandler', kwargs={'node_id': node['id']}),
            headers=self.default_headers)
        self.assertEquals(resp.status, 200)
        data = json.loads(resp.body)
        eth1 = [nic for nic in data if nic['name'] == 'eth1']
        self.assertEqual(len(eth1), 1)
        self.assertEqual(
            len(filter(lambda n: n['name'] == 'public',
                       eth1[0]['assigned_networks'])),
            1)
