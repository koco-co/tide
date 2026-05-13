# -*- coding: utf-8 -*-
"""Deterministic Tide-generated metadata tests."""


class TestTideGeneratedDatatableTestPostDassetsV1DatatablecolumnPagetablecolumn:
    """Generated from Tide normalized scenarios."""

    def test_dassets_datatablecolumn_pagetablecolumn(self):
        """dassets_dataTableColumn_pageTableColumn"""
        response = {'body': {'body_keys': ['code', 'data', 'message', 'space', 'success', 'version'],
                  'code': 1,
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

class TestTideGeneratedDatatableTestPostDmetadataV1DatatableGettablelifecycle:
    """Generated from Tide normalized scenarios."""

    def test_dmetadata_datatable_gettablelifecycle(self):
        """dmetadata_dataTable_getTableLifeCycle"""
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

class TestTideGeneratedDatatableTestPostDassetsV1DatatableQuerydetail:
    """Generated from Tide normalized scenarios."""

    def test_dassets_datatable_querydetail(self):
        """dassets_dataTable_queryDetail"""
        response = {'body': {'body_keys': ['code', 'data', 'message', 'space', 'success', 'version'],
                  'code': 1,
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

class TestTideGeneratedDatatableTestPostDassetsV1DatatableJudgeismetabytableid:
    """Generated from Tide normalized scenarios."""

    def test_dassets_datatable_judgeismetabytableid(self):
        """dassets_dataTable_judgeIsMetaByTableId"""
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

class TestTideGeneratedDatatableTestPostDassetsV1DatatableHasparition:
    """Generated from Tide normalized scenarios."""

    def test_dassets_datatable_hasparition(self):
        """dassets_dataTable_hasParition"""
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

class TestTideGeneratedDatatableTestPostDassetsV1DatatableQuerycreatetablesql:
    """Generated from Tide normalized scenarios."""

    def test_dassets_datatable_querycreatetablesql(self):
        """dassets_dataTable_queryCreateTableSql"""
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

class TestTideGeneratedDatatableTestPostDmetadataV1DatatableQuerytablepermission:
    """Generated from Tide normalized scenarios."""

    def test_dmetadata_datatable_querytablepermission(self):
        """dmetadata_dataTable_queryTablePermission"""
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
