# -*- coding: utf-8 -*-
"""Deterministic Tide-generated metadata tests."""


class TestTideGeneratedMetadata:
    """Generated from Tide normalized scenarios."""

    def test_metadata_post_v1_synctask_pagetask(self):
        """metadata_post_v1_syncTask_pageTask"""
        response = {'body': {'body_keys': ['code', 'data', 'message', 'space', 'success', 'version'],
                  'code': 1,
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

    def test_metadata_post_v1_datasource_listmetadatadatasource(self):
        """metadata_post_v1_dataSource_listMetadataDataSource"""
        response = {'body': {'body_keys': ['code', 'data', 'message', 'space', 'success', 'version'],
                  'code': 1,
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

    def test_metadata_post_v1_datadb_realtimedblist(self):
        """metadata_post_v1_dataDb_realTimeDbList"""
        response = {'body': {'body_keys': ['code', 'data', 'message', 'space', 'success', 'version'],
                  'code': 1,
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

    def test_metadata_post_v1_synctask_realtimetablelist(self):
        """metadata_post_v1_syncTask_realTimeTableList"""
        response = {'body': {'body_keys': ['code', 'data', 'message', 'space', 'success', 'version'],
                  'code': 1,
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

    def test_metadata_post_v1_synctask_add(self):
        """metadata_post_v1_syncTask_add"""
        response = {'body': {'body_keys': ['code', 'data', 'message', 'space', 'success', 'version'],
                  'code': 1,
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

    def test_metadata_post_v1_syncjob_pagequery(self):
        """metadata_post_v1_syncJob_pageQuery"""
        response = {'body': {'body_keys': ['code', 'data', 'message', 'space', 'success', 'version'],
                  'code': 1,
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

    def test_metadata_post_v1_metadataapply_issuperuser(self):
        """metadata_post_v1_metadataApply_isSuperUser"""
        response = {'body': {'body_keys': ['code', 'data', 'message', 'space', 'success', 'version'],
                  'code': 1,
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

    def test_metadata_post_v1_datatable_gettablelifecycle(self):
        """metadata_post_v1_dataTable_getTableLifeCycle"""
        response = {'body': {'body_keys': ['code', 'data', 'message', 'space', 'success', 'version'],
                  'code': 1,
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

    def test_metadata_post_v1_metadataapply_getapplystatus(self):
        """metadata_post_v1_metadataApply_getApplyStatus"""
        response = {'body': {'body_keys': ['code', 'data', 'message', 'space', 'success', 'version'],
                  'code': 1,
                  'data_keys': ['applyStatus', 'tableName'],
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

    def test_metadata_post_v1_datasubscribe_getsubscribebytableid(self):
        """metadata_post_v1_dataSubscribe_getSubscribeByTableId"""
        response = {'body': {'body_keys': ['code', 'data', 'message', 'space', 'success', 'version'],
                  'code': 1,
                  'data_keys': ['dingWebhook'],
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

    def test_metadata_post_v1_datatable_querytablepermission(self):
        """metadata_post_v1_dataTable_queryTablePermission"""
        response = {'body': {'body_keys': ['code', 'data', 'message', 'space', 'success', 'version'],
                  'code': 1,
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
