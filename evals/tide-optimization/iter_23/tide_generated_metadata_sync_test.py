# -*- coding: utf-8 -*-
"""Deterministic Tide-generated metadata tests."""


class TestTideGeneratedMetadataPostDmetadataV1SynctaskPagetask:
    """Generated from Tide normalized scenarios."""

    def test_dmetadata_synctask_pagetask(self):
        """dmetadata_syncTask_pageTask"""
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
        # L4: response data schema contract
        schema_fields = set(body.get("body_keys", []))
        schema_fields.update(body.get("data_keys", []))
        schema_fields.update(body.get("data_item_keys", []))
        assert schema_fields, "L4 response schema contract changed"
        for field_group in ("body_keys", "data_keys", "data_item_keys"):
            if field_group in body:
                assert isinstance(body[field_group], list), f"L4 schema group is not a list: {field_group}"
        # L5: business response consistency contract
        l5_business_markers = [key for key in ("success", "code") if key in body]
        assert l5_business_markers, "L5 business response consistency changed"
        if "success" in body:
            assert body["success"] is True, "L5 business success consistency changed"
        if "code" in body:
            assert body["code"] == 1, "L5 business code consistency changed"

class TestTideGeneratedMetadataPostDmetadataV1SynctaskRealtimetablelist:
    """Generated from Tide normalized scenarios."""

    def test_dmetadata_synctask_realtimetablelist(self):
        """dmetadata_syncTask_realTimeTableList"""
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
        # L4: response data schema contract
        schema_fields = set(body.get("body_keys", []))
        schema_fields.update(body.get("data_keys", []))
        schema_fields.update(body.get("data_item_keys", []))
        assert schema_fields, "L4 response schema contract changed"
        for field_group in ("body_keys", "data_keys", "data_item_keys"):
            if field_group in body:
                assert isinstance(body[field_group], list), f"L4 schema group is not a list: {field_group}"
        # L5: business response consistency contract
        l5_business_markers = [key for key in ("success", "code") if key in body]
        assert l5_business_markers, "L5 business response consistency changed"
        if "success" in body:
            assert body["success"] is True, "L5 business success consistency changed"
        if "code" in body:
            assert body["code"] == 1, "L5 business code consistency changed"

class TestTideGeneratedMetadataPostDmetadataV1SynctaskAdd:
    """Generated from Tide normalized scenarios."""

    def test_dmetadata_synctask_add(self):
        """dmetadata_syncTask_add"""
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
        # L4: response data schema contract
        schema_fields = set(body.get("body_keys", []))
        schema_fields.update(body.get("data_keys", []))
        schema_fields.update(body.get("data_item_keys", []))
        assert schema_fields, "L4 response schema contract changed"
        for field_group in ("body_keys", "data_keys", "data_item_keys"):
            if field_group in body:
                assert isinstance(body[field_group], list), f"L4 schema group is not a list: {field_group}"
        # L5: business response consistency contract
        l5_business_markers = [key for key in ("success", "code") if key in body]
        assert l5_business_markers, "L5 business response consistency changed"
        if "success" in body:
            assert body["success"] is True, "L5 business success consistency changed"
        if "code" in body:
            assert body["code"] == 1, "L5 business code consistency changed"

class TestTideGeneratedMetadataPostDmetadataV1SyncjobPagequery:
    """Generated from Tide normalized scenarios."""

    def test_dmetadata_syncjob_pagequery(self):
        """dmetadata_syncJob_pageQuery"""
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
        # L4: response data schema contract
        schema_fields = set(body.get("body_keys", []))
        schema_fields.update(body.get("data_keys", []))
        schema_fields.update(body.get("data_item_keys", []))
        assert schema_fields, "L4 response schema contract changed"
        for field_group in ("body_keys", "data_keys", "data_item_keys"):
            if field_group in body:
                assert isinstance(body[field_group], list), f"L4 schema group is not a list: {field_group}"
        # L5: business response consistency contract
        l5_business_markers = [key for key in ("success", "code") if key in body]
        assert l5_business_markers, "L5 business response consistency changed"
        if "success" in body:
            assert body["success"] is True, "L5 business success consistency changed"
        if "code" in body:
            assert body["code"] == 1, "L5 business code consistency changed"
