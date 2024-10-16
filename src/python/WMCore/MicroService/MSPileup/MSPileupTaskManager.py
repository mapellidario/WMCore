#!/usr/bin/env python
"""
File       : MSPileupTaskManager.py
Author     : Valentin Kuznetsov <vkuznet AT gmail dot com>
Description: MSPileupTaskManager handles MSPileupTasks

In particular, it perform the following tasks each polling cycle:
    - fetches pileup sizes for all pileup documents in database back-end
    - update RSE quotas
    - perform monitoring task
    - perform task for active pileups using up-to-date RSE quotas
    - perform task for inactive pileups
"""

# system modules
from threading import current_thread

# WMCore modules
from WMCore.MicroService.MSCore.MSCore import MSCore
from WMCore.MicroService.DataStructs.DefaultStructs import PILEUP_REPORT
from WMCore.MicroService.MSPileup.MSPileupData import MSPileupData
from WMCore.MicroService.MSPileup.MSPileupTasks import MSPileupTasks


class MSPileupTaskManager(MSCore):
    """
    MSPileupTaskManager handles MSPileup tasks
    """

    def __init__(self, msConfig, **kwargs):
        super().__init__(msConfig, **kwargs)
        self.marginSpace = msConfig.get('marginSpace', 1024**4)
        self.rucioAccount = msConfig.get('rucioAccount', 'wmcore_transferor')
        self.rucioUrl = msConfig['rucioUrl']  # aligned with MSCore init
        self.rucioAuthUrl = msConfig['rucioAuthUrl']  # aligned with MSCore init
        dryRun = msConfig.get('dryRun', False)
        self.rucioClient = self.rucio  # set in MSCore init
        self.dataManager = MSPileupData(msConfig)
        self.mgr = MSPileupTasks(self.dataManager, self.logger,
                                 self.rucioAccount, self.rucioClient, dryRun)

    def status(self):
        """
        Provide MSPileupTaskManager status API.

        :return: status dictionary
        """
        summary = dict(PILEUP_REPORT)
        summary.update({'thread_id': current_thread().name})
        report = self.mgr.getReport()
        summary.update({'tasks': report.getDocuments()})
        return summary

    def executeCycle(self):
        """
        execute MSPileupTasks polling cycle
        """
        self.mgr.pileupSizeTask()
        self.mgr.monitoringTask()
        self.mgr.activeTask(marginSpace=self.marginSpace)
        self.mgr.inactiveTask()
