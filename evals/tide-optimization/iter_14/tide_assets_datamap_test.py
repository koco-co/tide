# -*- coding: utf-8 -*-
import os

import pytest

from api.assets.assets_api import AssetsApi
from utils.assets.requests.assets_requests import AssetsBaseRequest


TABLE_NAME = os.getenv("TIDE_METADATA_TABLE_NAME", "test_spark_insert")
TABLE_ID = os.getenv("TIDE_METADATA_TABLE_ID", "")


def _assert_success(result, scenario):
    assert result["code"] == 1, "{} code should be 1: {}".format(scenario, result)
    assert result["success"] is True, "{} success should be true: {}".format(scenario, result)
    assert "data" in result, "{} response should contain data".format(scenario)


def _post(client, api, payload, desc):
    return client.post(url=api.value, desc=desc, json=payload)


def _extract_items(data):
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    for key in ("data", "records", "rows", "list", "items"):
        value = data.get(key)
        if isinstance(value, list):
            return value
        nested = _extract_items(value)
        if nested:
            return nested
    return []


def _first_table_id(result):
    for item in _extract_items(result.get("data")):
        if not isinstance(item, dict):
            continue
        name = str(item.get("tableName") or item.get("name") or "")
        item_id = item.get("tableId") or item.get("id")
        if TABLE_NAME in name and item_id:
            return str(item_id)
    if TABLE_ID:
        return TABLE_ID
    return ""


class TestTideAssetsDatamap:
    """数据地图 test_spark_insert 查询与表详情 HAR 链路测试。"""

    def setup_class(self):
        self.client = AssetsBaseRequest()
        self.table_id = TABLE_ID

    def test_datamap_overview_widgets(self):
        """dassets_datamap_overview_har_direct"""
        for api, desc in (
            (AssetsApi.datamap_recent_query, "数据地图最近查询"),
            (AssetsApi.datamap_asset_statistics, "数据地图资产统计"),
            (AssetsApi.datamap_hotword_list, "数据地图热词列表"),
            (AssetsApi.datamap_hotlabel_list, "数据地图热门标签"),
        ):
            result = _post(self.client, api, {}, desc)
            _assert_success(result, "dassets_datamap_overview_har_direct")

    def test_datamap_lookup_users_labels_and_catalogs(self):
        """dassets_datamap_lookup_har_direct"""
        list_users = _post(
            self.client,
            AssetsApi.datamap_list_users,
            {"metaType": 1},
            "查询数据地图用户筛选项",
        )
        _assert_success(list_users, "dassets_datamap_lookup_har_direct")

        label_list = _post(
            self.client,
            AssetsApi.datamap_lable_list,
            {"metaType": 1},
            "查询数据地图标签筛选项",
        )
        _assert_success(label_list, "dassets_datamap_lookup_har_direct")

        catalog_list = _post(
            self.client,
            AssetsApi.resourceCatalog_list_catalog_by_query,
            {},
            "查询资源目录筛选项",
        )
        _assert_success(catalog_list, "dassets_datamap_lookup_har_direct")

    def test_search_test_spark_insert_table(self):
        """dassets_datamap_query_detail_har_direct"""
        result = _post(
            self.client,
            AssetsApi.datamap_query_detail,
            {"current": 1, "size": 10, "metaType": 1, "search": TABLE_NAME, "field": "hot", "asc": False},
            "数据地图搜索 SparkThrift 测试表",
        )
        _assert_success(result, "dassets_datamap_query_detail_har_direct")
        type(self).table_id = _first_table_id(result)
        if not type(self).table_id:
            pytest.skip("当前环境数据地图未返回 test_spark_insert 表，跳过表详情链路")

    def test_table_column_lifecycle_and_detail(self):
        """dassets_table_detail_har_direct"""
        if not type(self).table_id:
            pytest.skip("当前环境缺少 test_spark_insert 表 ID，跳过表详情链路")

        page_column = _post(
            self.client,
            AssetsApi.dataTableColumn_page_table_column,
            {"pageNow": 1, "pageSize": 10, "tableId": type(self).table_id},
            "查询表字段列表",
        )
        _assert_success(page_column, "dassets_table_detail_har_direct")

        lifecycle = _post(
            self.client,
            AssetsApi.get_table_life_cycle,
            {"tableId": type(self).table_id},
            "查询表生命周期",
        )
        _assert_success(lifecycle, "dassets_table_detail_har_direct")

        detail = _post(
            self.client,
            AssetsApi.dataTable_query_detail,
            {"tableId": type(self).table_id},
            "查询资产表详情",
        )
        _assert_success(detail, "dassets_table_detail_har_direct")

    def test_table_labels_resources_partition_and_sql(self):
        """dassets_table_relation_partition_sql_har_direct"""
        if not type(self).table_id:
            pytest.skip("当前环境缺少 test_spark_insert 表 ID，跳过表关系链路")

        labels = _post(
            self.client,
            AssetsApi.label_list_all_bind_label_by_condition,
            {"metaType": 1, "labelType": 1, "metaId": type(self).table_id},
            "查询表绑定标签",
        )
        _assert_success(labels, "dassets_table_relation_partition_sql_har_direct")

        resource = _post(
            self.client,
            AssetsApi.resource_bind_resource_rel,
            {"metaType": 1, "metaId": type(self).table_id},
            "查询表绑定资源",
        )
        _assert_success(resource, "dassets_table_relation_partition_sql_har_direct")

        is_meta = _post(
            self.client,
            AssetsApi.judge_is_meta_by_table_id,
            {"tableId": type(self).table_id},
            "判断表是否为元数据中心数据",
        )
        _assert_success(is_meta, "dassets_table_relation_partition_sql_har_direct")

        partition = _post(
            self.client,
            AssetsApi.has_partition,
            {"tableId": type(self).table_id},
            "判断表是否有分区",
        )
        _assert_success(partition, "dassets_table_relation_partition_sql_har_direct")

        create_sql = _post(
            self.client,
            AssetsApi.dataTable_query_create_table_sql,
            {"tableId": type(self).table_id},
            "查询建表 SQL",
        )
        _assert_success(create_sql, "dassets_table_relation_partition_sql_har_direct")
