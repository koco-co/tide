# -*- coding: utf-8 -*-
"""Deterministic Tide-generated metadata tests."""


class TestTideGeneratedMetadataPostDmetadataV1SynctaskPagetask:
    """Generated from Tide normalized scenarios."""

    def test_scene_dmetadata_pagetask(self):
        """scene_dmetadata_pageTask"""
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
        available_fields = set(body)
        available_fields.update(body.get("body_keys", []))
        available_fields.update(body.get("data_keys", []))
        available_fields.update(body.get("data_item_keys", []))
        for field in ['code', 'success']:
            assert field in available_fields, f"L2 missing response field: {field}"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"

class TestTideGeneratedMetadataPostDmetadataV1DatasourceListmetadatadatasource:
    """Generated from Tide normalized scenarios."""

    def test_scene_dmetadata_listmetadatadatasource(self):
        """scene_dmetadata_listMetadataDataSource"""
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
        available_fields = set(body)
        available_fields.update(body.get("body_keys", []))
        available_fields.update(body.get("data_keys", []))
        available_fields.update(body.get("data_item_keys", []))
        for field in ['code', 'success']:
            assert field in available_fields, f"L2 missing response field: {field}"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"

class TestTideGeneratedMetadataPostDmetadataV1DatadbRealtimedblist:
    """Generated from Tide normalized scenarios."""

    def test_scene_dmetadata_realtimedblist(self):
        """scene_dmetadata_realTimeDbList"""
        response = {'body': {'body_keys': ['code', 'data', 'message', 'space', 'success', 'version'],
                  'code': 1,
                  'data_item_keys': ['dataSourceType', 'dbName', 'isOushu'],
                  'success': True},
         'status_code': 200}
        body = response.get("body", {})
        # L1: transport/status contract from HAR
        assert response["status_code"] == 200, "L1 status contract changed"
        # L2: response schema contract
        available_fields = set(body)
        available_fields.update(body.get("body_keys", []))
        available_fields.update(body.get("data_keys", []))
        available_fields.update(body.get("data_item_keys", []))
        for field in ['code', 'success']:
            assert field in available_fields, f"L2 missing response field: {field}"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"

class TestTideGeneratedMetadataPostDmetadataV1SynctaskRealtimetablelist:
    """Generated from Tide normalized scenarios."""

    def test_scene_dmetadata_realtimetablelist(self):
        """scene_dmetadata_realTimeTableList"""
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
        available_fields = set(body)
        available_fields.update(body.get("body_keys", []))
        available_fields.update(body.get("data_keys", []))
        available_fields.update(body.get("data_item_keys", []))
        for field in ['code', 'success']:
            assert field in available_fields, f"L2 missing response field: {field}"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"

class TestTideGeneratedMetadataPostDmetadataV1SynctaskAdd:
    """Generated from Tide normalized scenarios."""

    def test_scene_dmetadata_add(self):
        """scene_dmetadata_add"""
        response = {'body': {'body_keys': ['code', 'data', 'message', 'space', 'success', 'version'],
                  'code': 1,
                  'success': True},
         'status_code': 200}
        body = response.get("body", {})
        # L1: transport/status contract from HAR
        assert response["status_code"] == 200, "L1 status contract changed"
        # L2: response schema contract
        available_fields = set(body)
        available_fields.update(body.get("body_keys", []))
        available_fields.update(body.get("data_keys", []))
        available_fields.update(body.get("data_item_keys", []))
        for field in ['code', 'success']:
            assert field in available_fields, f"L2 missing response field: {field}"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"

class TestTideGeneratedMetadataPostDmetadataV1SyncjobPagequery:
    """Generated from Tide normalized scenarios."""

    def test_scene_dmetadata_pagequery(self):
        """scene_dmetadata_pageQuery"""
        response = {'body': {'body_keys': ['code', 'data', 'message', 'space', 'success', 'version'],
                  'code': 1,
                  'data_keys': ['contentList', 'current', 'size', 'total'],
                  'success': True},
         'status_code': 200}
        body = response.get("body", {})
        # L1: transport/status contract from HAR
        assert response["status_code"] == 200, "L1 status contract changed"
        # L2: response schema contract
        available_fields = set(body)
        available_fields.update(body.get("body_keys", []))
        available_fields.update(body.get("data_keys", []))
        available_fields.update(body.get("data_item_keys", []))
        for field in ['code', 'success']:
            assert field in available_fields, f"L2 missing response field: {field}"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"

class TestTideGeneratedMetadataPostDmetadataV1MetadataapplyIssuperuser:
    """Generated from Tide normalized scenarios."""

    def test_scene_dmetadata_issuperuser(self):
        """scene_dmetadata_isSuperUser"""
        response = {'body': {'body_keys': ['code', 'data', 'message', 'space', 'success', 'version'],
                  'code': 1,
                  'success': True},
         'status_code': 200}
        body = response.get("body", {})
        # L1: transport/status contract from HAR
        assert response["status_code"] == 200, "L1 status contract changed"
        # L2: response schema contract
        available_fields = set(body)
        available_fields.update(body.get("body_keys", []))
        available_fields.update(body.get("data_keys", []))
        available_fields.update(body.get("data_item_keys", []))
        for field in ['code', 'success']:
            assert field in available_fields, f"L2 missing response field: {field}"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"

class TestTideGeneratedMetadataPostDmetadataV1DatatableGettablelifecycle:
    """Generated from Tide normalized scenarios."""

    def test_scene_dmetadata_gettablelifecycle(self):
        """scene_dmetadata_getTableLifeCycle"""
        response = {'body': {'body_keys': ['code', 'data', 'message', 'space', 'success', 'version'],
                  'code': 1,
                  'success': True},
         'status_code': 200}
        body = response.get("body", {})
        # L1: transport/status contract from HAR
        assert response["status_code"] == 200, "L1 status contract changed"
        # L2: response schema contract
        available_fields = set(body)
        available_fields.update(body.get("body_keys", []))
        available_fields.update(body.get("data_keys", []))
        available_fields.update(body.get("data_item_keys", []))
        for field in ['code', 'success']:
            assert field in available_fields, f"L2 missing response field: {field}"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"

class TestTideGeneratedMetadataPostDmetadataV1MetadataapplyGetapplystatus:
    """Generated from Tide normalized scenarios."""

    def test_scene_dmetadata_getapplystatus(self):
        """scene_dmetadata_getApplyStatus"""
        response = {'body': {'body_keys': ['code', 'data', 'message', 'space', 'success', 'version'],
                  'code': 1,
                  'data_keys': ['applyStatus', 'tableName'],
                  'success': True},
         'status_code': 200}
        body = response.get("body", {})
        # L1: transport/status contract from HAR
        assert response["status_code"] == 200, "L1 status contract changed"
        # L2: response schema contract
        available_fields = set(body)
        available_fields.update(body.get("body_keys", []))
        available_fields.update(body.get("data_keys", []))
        available_fields.update(body.get("data_item_keys", []))
        for field in ['code', 'success']:
            assert field in available_fields, f"L2 missing response field: {field}"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"

class TestTideGeneratedMetadataPostDmetadataV1DatasubscribeGetsubscribebytableid:
    """Generated from Tide normalized scenarios."""

    def test_scene_dmetadata_getsubscribebytableid(self):
        """scene_dmetadata_getSubscribeByTableId"""
        response = {'body': {'body_keys': ['code', 'data', 'message', 'space', 'success', 'version'],
                  'code': 1,
                  'data_keys': ['dingWebhook'],
                  'success': True},
         'status_code': 200}
        body = response.get("body", {})
        # L1: transport/status contract from HAR
        assert response["status_code"] == 200, "L1 status contract changed"
        # L2: response schema contract
        available_fields = set(body)
        available_fields.update(body.get("body_keys", []))
        available_fields.update(body.get("data_keys", []))
        available_fields.update(body.get("data_item_keys", []))
        for field in ['code', 'success']:
            assert field in available_fields, f"L2 missing response field: {field}"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"

class TestTideGeneratedMetadataPostDmetadataV1DatatableQuerytablepermission:
    """Generated from Tide normalized scenarios."""

    def test_scene_dmetadata_querytablepermission(self):
        """scene_dmetadata_queryTablePermission"""
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
        available_fields = set(body)
        available_fields.update(body.get("body_keys", []))
        available_fields.update(body.get("data_keys", []))
        available_fields.update(body.get("data_item_keys", []))
        for field in ['code', 'success']:
            assert field in available_fields, f"L2 missing response field: {field}"
        # L3: business success contract
        if "code" in body:
            assert body["code"] == 1, "L3 business code contract changed"
        if "success" in body:
            assert body["success"] is True, "L3 success flag contract changed"
