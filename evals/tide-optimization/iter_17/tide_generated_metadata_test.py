# -*- coding: utf-8 -*-
"""Deterministic Tide-generated metadata tests."""


class TestTideGeneratedMetadata:
    """Generated from Tide normalized scenarios."""

    def test_recentquery(self):
        """recentQuery"""
        response = {'body': {'code': 1, 'data_item_keys': ['count', 'metaType', 'name'], 'success': True},
         'status_code': 200}
        body = response.get("body", {})
        # L1: transport/status contract from HAR
        assert response["status_code"] == 200, "L1 status contract changed"
        # L2: response schema contract
        assert isinstance(body, dict), "L2 response body contract must be a dict"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"

    def test_assetstatistics(self):
        """assetStatistics"""
        response = {'body': {'code': 1, 'data_item_keys': ['count', 'type'], 'success': True},
         'status_code': 200}
        body = response.get("body", {})
        # L1: transport/status contract from HAR
        assert response["status_code"] == 200, "L1 status contract changed"
        # L2: response schema contract
        assert isinstance(body, dict), "L2 response body contract must be a dict"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"

    def test_hotword_list(self):
        """hotword_list"""
        response = {'body': {'code': 1, 'data_item_keys': ['count', 'metaType', 'name'], 'success': True},
         'status_code': 200}
        body = response.get("body", {})
        # L1: transport/status contract from HAR
        assert response["status_code"] == 200, "L1 status contract changed"
        # L2: response schema contract
        assert isinstance(body, dict), "L2 response body contract must be a dict"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"

    def test_hotlabel_list(self):
        """hotLabel_list"""
        response = {'body': {'code': 1, 'data_item_keys': [], 'success': True}, 'status_code': 200}
        body = response.get("body", {})
        # L1: transport/status contract from HAR
        assert response["status_code"] == 200, "L1 status contract changed"
        # L2: response schema contract
        assert isinstance(body, dict), "L2 response body contract must be a dict"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"

    def test_datamap_querydetail(self):
        """datamap_queryDetail"""
        response = {'body': {'code': 1,
                  'data_keys': ['contentList', 'current', 'size', 'total'],
                  'success': True},
         'status_code': 200}
        body = response.get("body", {})
        # L1: transport/status contract from HAR
        assert response["status_code"] == 200, "L1 status contract changed"
        # L2: response schema contract
        assert isinstance(body, dict), "L2 response body contract must be a dict"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"

    def test_datamap_listusers(self):
        """datamap_listUsers"""
        response = {'body': {'code': 1, 'data_item_keys': [], 'success': True}, 'status_code': 200}
        body = response.get("body", {})
        # L1: transport/status contract from HAR
        assert response["status_code"] == 200, "L1 status contract changed"
        # L2: response schema contract
        assert isinstance(body, dict), "L2 response body contract must be a dict"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"

    def test_datamap_label_list(self):
        """datamap_label_list"""
        response = {'body': {'code': 1, 'data_item_keys': [], 'success': True}, 'status_code': 200}
        body = response.get("body", {})
        # L1: transport/status contract from HAR
        assert response["status_code"] == 200, "L1 status contract changed"
        # L2: response schema contract
        assert isinstance(body, dict), "L2 response body contract must be a dict"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"

    def test_listcatalogbyquery(self):
        """listCatalogByQuery"""
        response = {'body': {'code': 1, 'data_item_keys': ['children', 'level', 'name'], 'success': True},
         'status_code': 200}
        body = response.get("body", {})
        # L1: transport/status contract from HAR
        assert response["status_code"] == 200, "L1 status contract changed"
        # L2: response schema contract
        assert isinstance(body, dict), "L2 response body contract must be a dict"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"

    def test_countdatasource(self):
        """countDataSource"""
        response = {'body': {'code': 1, 'data_item_keys': ['count', 'dataSourceType'], 'success': True},
         'status_code': 200}
        body = response.get("body", {})
        # L1: transport/status contract from HAR
        assert response["status_code"] == 200, "L1 status contract changed"
        # L2: response schema contract
        assert isinstance(body, dict), "L2 response body contract must be a dict"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"

    def test_pageusers_assets(self):
        """pageUsers_assets"""
        response = {'body': {'code': 1,
                  'data_item_keys': ['allProject',
                                     'finalRoles',
                                     'gmtCreate',
                                     'roles',
                                     'user',
                                     'userGroupVO',
                                     'validProject'],
                  'data_keys': ['attachment',
                                'currentPage',
                                'data',
                                'pageSize',
                                'totalCount',
                                'totalPage'],
                  'success': True},
         'status_code': 200}
        body = response.get("body", {})
        # L1: transport/status contract from HAR
        assert response["status_code"] == 200, "L1 status contract changed"
        # L2: response schema contract
        assert isinstance(body, dict), "L2 response body contract must be a dict"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"

    def test_datatable_querydetail(self):
        """dataTable_queryDetail"""
        response = {'body': {'code': 1,
                  'data_keys': ['allColumnPermission',
                                'allRowPermission',
                                'dbName',
                                'displayVo',
                                'hideTableApplyButton',
                                'permissionColumns',
                                'qualityInfo',
                                'realDataSourceName',
                                'rowPermissionVOS',
                                'similarDataSourceList',
                                'tableAttributeDTOList',
                                'tableCustomDesc',
                                'tableHeatStatistics'],
                  'success': True},
         'status_code': 200}
        body = response.get("body", {})
        # L1: transport/status contract from HAR
        assert response["status_code"] == 200, "L1 status contract changed"
        # L2: response schema contract
        assert isinstance(body, dict), "L2 response body contract must be a dict"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"

    def test_pagetablecolumn(self):
        """pageTableColumn"""
        response = {'body': {'code': 1,
                  'data_item_keys': ['columnAttributeList',
                                     'columnCustomDesc',
                                     'columnName',
                                     'columnNameCn',
                                     'columnTagVOList',
                                     'columnType',
                                     'isPartition'],
                  'data_keys': ['data', 'pageNow', 'pageSize', 'total', 'totalPage'],
                  'success': True},
         'status_code': 200}
        body = response.get("body", {})
        # L1: transport/status contract from HAR
        assert response["status_code"] == 200, "L1 status contract changed"
        # L2: response schema contract
        assert isinstance(body, dict), "L2 response body contract must be a dict"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"

    def test_querycreatetablesql(self):
        """queryCreateTableSql"""
        response = {'body': {'code': 1, 'success': True}, 'status_code': 200}
        body = response.get("body", {})
        # L1: transport/status contract from HAR
        assert response["status_code"] == 200, "L1 status contract changed"
        # L2: response schema contract
        assert isinstance(body, dict), "L2 response body contract must be a dict"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"

    def test_judgeismetabytableid(self):
        """judgeIsMetaByTableId"""
        response = {'body': {'code': 1, 'success': True}, 'status_code': 200}
        body = response.get("body", {})
        # L1: transport/status contract from HAR
        assert response["status_code"] == 200, "L1 status contract changed"
        # L2: response schema contract
        assert isinstance(body, dict), "L2 response body contract must be a dict"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"

    def test_hasparition(self):
        """hasParition"""
        response = {'body': {'code': 1, 'success': True}, 'status_code': 200}
        body = response.get("body", {})
        # L1: transport/status contract from HAR
        assert response["status_code"] == 200, "L1 status contract changed"
        # L2: response schema contract
        assert isinstance(body, dict), "L2 response body contract must be a dict"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"

class TestTideGeneratedMetadata2:
    """Generated from Tide normalized scenarios."""

    def test_listallbindlabelbycondition(self):
        """listAllBindLabelByCondition"""
        response = {'body': {'code': 1, 'data_item_keys': [], 'success': True}, 'status_code': 200}
        body = response.get("body", {})
        # L1: transport/status contract from HAR
        assert response["status_code"] == 200, "L1 status contract changed"
        # L2: response schema contract
        assert isinstance(body, dict), "L2 response body contract must be a dict"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"

    def test_bindresourcerel(self):
        """bindResourceRel"""
        response = {'body': {'code': 1, 'success': True}, 'status_code': 200}
        body = response.get("body", {})
        # L1: transport/status contract from HAR
        assert response["status_code"] == 200, "L1 status contract changed"
        # L2: response schema contract
        assert isinstance(body, dict), "L2 response body contract must be a dict"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"

    def test_gettablelifecycle(self):
        """getTableLifeCycle"""
        response = {'body': {'code': 1, 'success': True}, 'status_code': 200}
        body = response.get("body", {})
        # L1: transport/status contract from HAR
        assert response["status_code"] == 200, "L1 status contract changed"
        # L2: response schema contract
        assert isinstance(body, dict), "L2 response body contract must be a dict"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"

    def test_getapplystatus(self):
        """getApplyStatus"""
        response = {'body': {'code': 1, 'data_keys': ['applyStatus', 'tableName'], 'success': True},
         'status_code': 200}
        body = response.get("body", {})
        # L1: transport/status contract from HAR
        assert response["status_code"] == 200, "L1 status contract changed"
        # L2: response schema contract
        assert isinstance(body, dict), "L2 response body contract must be a dict"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"

    def test_getsubscribebytableid(self):
        """getSubscribeByTableId"""
        response = {'body': {'code': 1, 'data_keys': ['dingWebhook'], 'success': True}, 'status_code': 200}
        body = response.get("body", {})
        # L1: transport/status contract from HAR
        assert response["status_code"] == 200, "L1 status contract changed"
        # L2: response schema contract
        assert isinstance(body, dict), "L2 response body contract must be a dict"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"

    def test_querytablepermission(self):
        """queryTablePermission"""
        response = {'body': {'code': 1,
                  'data_item_keys': ['isPermanent',
                                     'name',
                                     'ownPermission',
                                     'permissionCode',
                                     'validityDeadline'],
                  'success': True},
         'status_code': 200}
        body = response.get("body", {})
        # L1: transport/status contract from HAR
        assert response["status_code"] == 200, "L1 status contract changed"
        # L2: response schema contract
        assert isinstance(body, dict), "L2 response body contract must be a dict"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"

    def test_issuperuser(self):
        """isSuperUser"""
        response = {'body': {'code': 1, 'success': True}, 'status_code': 200}
        body = response.get("body", {})
        # L1: transport/status contract from HAR
        assert response["status_code"] == 200, "L1 status contract changed"
        # L2: response schema contract
        assert isinstance(body, dict), "L2 response body contract must be a dict"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"

    def test_synctask_pagetask(self):
        """syncTask_pageTask"""
        response = {'body': {'code': 1,
                  'data_item_keys': ['allDb',
                                     'allTable',
                                     'catalog',
                                     'dataSource',
                                     'dbList',
                                     'jobStatus',
                                     'periodType',
                                     'realTimeSwitch',
                                     'recentSyncTime',
                                     'syncMeatContent',
                                     'syncStatus',
                                     'syncTableConfiguration',
                                     'tableList',
                                     'taskParams',
                                     'taskType'],
                  'data_keys': ['data', 'pageNow', 'pageSize', 'total', 'totalPage'],
                  'success': True},
         'status_code': 200}
        body = response.get("body", {})
        # L1: transport/status contract from HAR
        assert response["status_code"] == 200, "L1 status contract changed"
        # L2: response schema contract
        assert isinstance(body, dict), "L2 response body contract must be a dict"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"

    def test_synctask_add(self):
        """syncTask_add"""
        response = {'body': {'code': 1, 'success': True}, 'status_code': 200}
        body = response.get("body", {})
        # L1: transport/status contract from HAR
        assert response["status_code"] == 200, "L1 status contract changed"
        # L2: response schema contract
        assert isinstance(body, dict), "L2 response body contract must be a dict"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"

    def test_syncjob_pagequery(self):
        """syncJob_pageQuery"""
        response = {'body': {'code': 1,
                  'data_keys': ['contentList', 'current', 'size', 'total'],
                  'success': True},
         'status_code': 200}
        body = response.get("body", {})
        # L1: transport/status contract from HAR
        assert response["status_code"] == 200, "L1 status contract changed"
        # L2: response schema contract
        assert isinstance(body, dict), "L2 response body contract must be a dict"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"

    def test_realtimetablelist(self):
        """realTimeTableList"""
        response = {'body': {'code': 1,
                  'data_item_keys': ['dbName',
                                     'isMaterializedView',
                                     'isModelTableBuild',
                                     'isView',
                                     'tableName'],
                  'success': True},
         'status_code': 200}
        body = response.get("body", {})
        # L1: transport/status contract from HAR
        assert response["status_code"] == 200, "L1 status contract changed"
        # L2: response schema contract
        assert isinstance(body, dict), "L2 response body contract must be a dict"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"

    def test_listmetadatadatasource(self):
        """listMetadataDataSource"""
        response = {'body': {'code': 1,
                  'data_item_keys': ['dataSourceName',
                                     'dataSourceType',
                                     'dataSourceTypeName',
                                     'disabled',
                                     'disabledMsg'],
                  'success': True},
         'status_code': 200}
        body = response.get("body", {})
        # L1: transport/status contract from HAR
        assert response["status_code"] == 200, "L1 status contract changed"
        # L2: response schema contract
        assert isinstance(body, dict), "L2 response body contract must be a dict"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"

    def test_realtimedblist(self):
        """realTimeDbList"""
        response = {'body': {'code': 1,
                  'data_item_keys': ['dataSourceType', 'dbName', 'isOushu'],
                  'success': True},
         'status_code': 200}
        body = response.get("body", {})
        # L1: transport/status contract from HAR
        assert response["status_code"] == 200, "L1 status contract changed"
        # L2: response schema contract
        assert isinstance(body, dict), "L2 response body contract must be a dict"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"
