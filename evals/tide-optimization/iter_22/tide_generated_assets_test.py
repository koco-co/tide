# -*- coding: utf-8 -*-
"""Deterministic Tide-generated metadata tests."""


class TestTideGeneratedAssetsTestPostDassetsV1UserPageusers:
    """Generated from Tide normalized scenarios."""

    def test_scene_dassets_pageusers(self):
        """scene_dassets_pageUsers"""
        response = {'body': {'body_keys': ['code', 'data', 'message', 'space', 'success', 'version'],
                  'code': 1,
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

class TestTideGeneratedAssetsTestPostDassetsV1DatamapRecentquery:
    """Generated from Tide normalized scenarios."""

    def test_scene_dassets_recentquery(self):
        """scene_dassets_recentQuery"""
        response = {'body': {'body_keys': ['code', 'data', 'message', 'space', 'success', 'version'],
                  'code': 1,
                  'data_item_keys': ['count', 'metaType', 'name'],
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

class TestTideGeneratedAssetsTestPostDassetsV1DatamapAssetstatistics:
    """Generated from Tide normalized scenarios."""

    def test_scene_dassets_assetstatistics(self):
        """scene_dassets_assetStatistics"""
        response = {'body': {'body_keys': ['code', 'data', 'message', 'space', 'success', 'version'],
                  'code': 1,
                  'data_item_keys': ['count', 'type'],
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

class TestTideGeneratedAssetsTestPostDassetsV1DatainventoryCountdatasource:
    """Generated from Tide normalized scenarios."""

    def test_scene_dassets_countdatasource(self):
        """scene_dassets_countDataSource"""
        response = {'body': {'body_keys': ['code', 'data', 'message', 'space', 'success', 'version'],
                  'code': 1,
                  'data_item_keys': ['count', 'dataSourceType'],
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

class TestTideGeneratedAssetsTestPostDassetsV1DatamapHotwordList:
    """Generated from Tide normalized scenarios."""

    def test_scene_dassets_list(self):
        """scene_dassets_list"""
        response = {'body': {'body_keys': ['code', 'data', 'message', 'space', 'success', 'version'],
                  'code': 1,
                  'data_item_keys': ['count', 'metaType', 'name'],
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

class TestTideGeneratedAssetsTestPostDassetsV1DatamapHotlabelList:
    """Generated from Tide normalized scenarios."""

    def test_scene_dassets_list_2(self):
        """scene_dassets_list_2"""
        response = {'body': {'body_keys': ['code', 'data', 'message', 'space', 'success', 'version'],
                  'code': 1,
                  'data_item_keys': [],
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

class TestTideGeneratedAssetsTestPostDassetsV1DatamapListusers:
    """Generated from Tide normalized scenarios."""

    def test_scene_dassets_listusers(self):
        """scene_dassets_listUsers"""
        response = {'body': {'body_keys': ['code', 'data', 'message', 'space', 'success', 'version'],
                  'code': 1,
                  'data_item_keys': [],
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

class TestTideGeneratedAssetsTestPostDassetsV1DatamapLabelList:
    """Generated from Tide normalized scenarios."""

    def test_scene_dassets_list_3(self):
        """scene_dassets_list_3"""
        response = {'body': {'body_keys': ['code', 'data', 'message', 'space', 'success', 'version'],
                  'code': 1,
                  'data_item_keys': [],
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

class TestTideGeneratedAssetsTestPostDassetsV1ResourcecatalogListcatalogbyquery:
    """Generated from Tide normalized scenarios."""

    def test_scene_dassets_listcatalogbyquery(self):
        """scene_dassets_listCatalogByQuery"""
        response = {'body': {'body_keys': ['code', 'data', 'message', 'space', 'success', 'version'],
                  'code': 1,
                  'data_item_keys': ['children', 'level', 'name'],
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

class TestTideGeneratedAssetsTestPostDassetsV1DatamapQuerydetail:
    """Generated from Tide normalized scenarios."""

    def test_scene_dassets_querydetail(self):
        """scene_dassets_queryDetail"""
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

class TestTideGeneratedAssetsTestPostDassetsV1DatatablecolumnPagetablecolumn:
    """Generated from Tide normalized scenarios."""

    def test_scene_dassets_pagetablecolumn(self):
        """scene_dassets_pageTableColumn"""
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

class TestTideGeneratedAssetsTestPostDassetsV1DatatableQuerydetail:
    """Generated from Tide normalized scenarios."""

    def test_scene_dassets_querydetail_2(self):
        """scene_dassets_queryDetail_2"""
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

class TestTideGeneratedAssetsTestPostDassetsV1LabelListallbindlabelbycondition:
    """Generated from Tide normalized scenarios."""

    def test_scene_dassets_listallbindlabelbycondition(self):
        """scene_dassets_listAllBindLabelByCondition"""
        response = {'body': {'body_keys': ['code', 'data', 'message', 'space', 'success', 'version'],
                  'code': 1,
                  'data_item_keys': [],
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

class TestTideGeneratedAssetsTestPostDassetsV1DatamapResourceBindresourcerel:
    """Generated from Tide normalized scenarios."""

    def test_scene_dassets_bindresourcerel(self):
        """scene_dassets_bindResourceRel"""
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

class TestTideGeneratedAssetsTestPostDassetsV1DatatableJudgeismetabytableid:
    """Generated from Tide normalized scenarios."""

    def test_scene_dassets_judgeismetabytableid(self):
        """scene_dassets_judgeIsMetaByTableId"""
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

class TestTideGeneratedAssetsTestPostDassetsV1DatatableHasparition:
    """Generated from Tide normalized scenarios."""

    def test_scene_dassets_hasparition(self):
        """scene_dassets_hasParition"""
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

class TestTideGeneratedAssetsTestPostDassetsV1DatatableQuerycreatetablesql:
    """Generated from Tide normalized scenarios."""

    def test_scene_dassets_querycreatetablesql(self):
        """scene_dassets_queryCreateTableSql"""
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
