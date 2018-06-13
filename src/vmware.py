# -*- coding: utf-8 -*-
from pyVmomi import vim
from pyVim import connect
import atexit
import requests
import ssl
import pchelper
from datetime import timedelta


class vCenterException(RuntimeError):
    """An VMWare vCenter error occured."""


class vCenter(object):
    def __init__(self, server, username, password):
        self.server = server
        self.username = username
        self.password = password
        self.SI = None
        requests.packages.urllib3.disable_warnings()
        self.context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        self.context.verify_mode = ssl.CERT_NONE
        try:
            self.SI = connect.SmartConnect(host=self.server,
                                           user=self.username,
                                           pwd=self.password,
                                           sslContext=self.context)

        except Exception as exc:
            raise vCenterException(exc)

        else:
            atexit.register(connect.Disconnect, self.SI)
        self.vchtime = self.SI.CurrentTime()

        self.perf_dict = {}
        perfList = self.SI.content.perfManager.perfCounter
        for counter in perfList:
            counter_full = "{}.{}.{}".format(counter.groupInfo.key,
                                             counter.nameInfo.key,
                                             counter.rollupType)
            self.perf_dict[counter_full] = counter.key

    def stat_check(self, perf_dict, counter_name):
        counter_key = perf_dict[counter_name]
        return counter_key

    def build_perf_query(self, vchtime, counterId, instance, vm, interval=20, count=15):
        perfManager = self.SI.RetrieveContent().perfManager
        metricId = vim.PerformanceManager.MetricId(counterId=counterId,
                                                   instance=instance)
        startTime = vchtime - timedelta(minutes=(interval * count) / 60)
        endTime = vchtime
        query = vim.PerformanceManager.QuerySpec(intervalId=interval,
                                                 entity=vm,
                                                 metricId=[metricId],
                                                 startTime=startTime,
                                                 endTime=endTime)
        perfResults = perfManager.QueryPerf(querySpec=[query])
        if perfResults:
            return perfResults

    def get_virtualdisk_scsi(self, vm_hardware, virtualdisk):
        controllerID = virtualdisk.controllerKey
        unitNumber = virtualdisk.unitNumber
        for vm_hardware_device in vm_hardware.device:
            if vm_hardware_device.key == controllerID:
                busNumber = vm_hardware_device.busNumber
        return "scsi{}:{}".format(busNumber, unitNumber)

    def get_vm(self):
        data = {}
        vm_properties = ["name", "summary.runtime.host", "config.hardware", "runtime.powerState"]
        view = pchelper.get_container_view(self.SI,
                                           obj_type=[vim.VirtualMachine])
        vm_data = pchelper.collect_properties(self.SI, view_ref=view,
                                              obj_type=vim.VirtualMachine,
                                              path_set=vm_properties,
                                              include_mors=True)
        for vm in vm_data:
            if vm['runtime.powerState'] == vim.VirtualMachinePowerState.poweredOn:
                data.update({'{}.{}.{}.vm.{}.fatstats.numIOAvg'.format(self.server.replace('.', '_'),
                                                                       vm['summary.runtime.host'].parent.parent.parent.name.replace('.', '_'),
                                                                       vm['summary.runtime.host'].parent.name.replace('.', '_').lower(),
                                                                       vm['name'].replace('.', '_')): self.get_vm_vd_iops(vm, vm['obj'])})

                vm_ds_iops = self.get_vm_ds_iops(vm, vm['obj'])
                for key, value in vm_ds_iops.items():
                    data.update({'{}.{}.{}.datastore.{}.{}.numIOAvg'.format(self.server.replace('.', '_'),
                                                                            vm['summary.runtime.host'].parent.parent.parent.name.replace('.', '_'),
                                                                            vm['summary.runtime.host'].parent.name.replace('.', '_').lower(),
                                                                            key.replace('.', '_').lower(),
                                                                            vm['name'].replace('.', '_')): value})
        return data

    def get_vm_vd_iops(self, vm, moref, interval=20, count=15):
        vm_hardware = vm['config.hardware']
        vmNumAvg = 0
        for each_vm_hardware in vm_hardware.device:
            if (each_vm_hardware.key >= 2000) and (each_vm_hardware.key < 3000):
                statVirtualdiskIORead = self.build_perf_query(self.vchtime,
                                                              self.stat_check(self.perf_dict, 'virtualDisk.numberReadAveraged.average'),
                                                              self.get_virtualdisk_scsi(vm_hardware, each_vm_hardware),
                                                              moref,
                                                              interval,
                                                              count)
                VirtualdiskIORead = (sum(statVirtualdiskIORead[0].value[0].value)) / count

                statVirtualdiskIOWrite = self.build_perf_query(self.vchtime,
                                                               self.stat_check(self.perf_dict, 'virtualDisk.numberWriteAveraged.average'),
                                                               self.get_virtualdisk_scsi(vm_hardware, each_vm_hardware),
                                                               moref,
                                                               interval,
                                                               count)
                VirtualdiskIOWrite = (sum(statVirtualdiskIOWrite[0].value[0].value)) / count

                vmNumAvg += (VirtualdiskIORead + VirtualdiskIOWrite)
        return vmNumAvg

    def get_vm_ds_iops(self, vm, moref, interval=20, count=15):
        vm_hardware = vm['config.hardware']
        data = {}
        for each_vm_hardware in vm_hardware.device:
            if (each_vm_hardware.key >= 2000) and (each_vm_hardware.key < 3000):
                if each_vm_hardware.backing.datastore.summary.type != "vsan":
                    statDatastoreIORead = self.build_perf_query(self.vchtime,
                                                                self.stat_check(self.perf_dict, 'datastore.numberReadAveraged.average'),
                                                                each_vm_hardware.backing.datastore.info.vmfs.uuid,
                                                                moref,
                                                                interval,
                                                                count)
                    if not statDatastoreIORead:
                        continue

                    DatastoreIORead = (sum(statDatastoreIORead[0].value[0].value)) / count

                    statDatastoreIOWrite = self.build_perf_query(self.vchtime,
                                                                 self.stat_check(self.perf_dict, 'datastore.numberWriteAveraged.average'),
                                                                 each_vm_hardware.backing.datastore.info.vmfs.uuid,
                                                                 moref,
                                                                 interval,
                                                                 count)
                    if not statDatastoreIOWrite:
                        continue
                    DatastoreIOWrite = (sum(statDatastoreIOWrite[0].value[0].value)) / count

                    if each_vm_hardware.backing.datastore.summary.name not in data:
                        data[each_vm_hardware.backing.datastore.summary.name] = (DatastoreIORead + DatastoreIOWrite)
        return data
