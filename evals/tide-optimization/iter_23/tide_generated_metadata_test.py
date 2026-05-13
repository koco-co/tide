# -*- coding: utf-8 -*-
"""Deterministic Tide-generated metadata tests."""


class TestTideGeneratedMetadataPostDmetadataV1DatasourceListmetadatadatasource:
    """Generated from Tide normalized scenarios."""

    def test_dmetadata_datasource_listmetadatadatasource(self):
        """dmetadata_dataSource_listMetadataDataSource"""
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

class TestTideGeneratedMetadataPostDmetadataV1DatadbRealtimedblist:
    """Generated from Tide normalized scenarios."""

    def test_dmetadata_datadb_realtimedblist(self):
        """dmetadata_dataDb_realTimeDbList"""
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

class TestTideGeneratedMetadataPostDmetadataV1MetadataapplyIssuperuser:
    """Generated from Tide normalized scenarios."""

    def test_dmetadata_metadataapply_issuperuser(self):
        """dmetadata_metadataApply_isSuperUser"""
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

class TestTideGeneratedMetadataPostDmetadataV1MetadataapplyGetapplystatus:
    """Generated from Tide normalized scenarios."""

    def test_dmetadata_metadataapply_getapplystatus(self):
        """dmetadata_metadataApply_getApplyStatus"""
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

class TestTideGeneratedMetadataPostDmetadataV1DatasubscribeGetsubscribebytableid:
    """Generated from Tide normalized scenarios."""

    def test_dmetadata_datasubscribe_getsubscribebytableid(self):
        """dmetadata_dataSubscribe_getSubscribeByTableId"""
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
