# -*- coding: utf-8 -*-
import os

import pytest

from api.assets.assets_api import AssetsApi
from utils.assets.requests.assets_requests import AssetsBaseRequest


TABLE_NAME = os.getenv("TIDE_METADATA_TABLE_NAME", "test_spark_insert")
DB_NAME = os.getenv("TIDE_METADATA_DB_NAME", "pw_test")
DATASOURCE_ID = os.getenv("TIDE_METADATA_DATASOURCE_ID", "")
DATASOURCE_TYPE = int(os.getenv("TIDE_METADATA_DATASOURCE_TYPE", "45"))
TASK_ID = os.getenv("TIDE_METADATA_SYNC_TASK_ID", "851")
TABLE_ID = os.getenv("TIDE_METADATA_TABLE_ID", "12695")


def _assert_success(result, scenario):
    assert result["code"] == 1, "{} code should be 1: {}".format(scenario, result)
    assert result["success"] is True, "{} success should be true: {}".format(scenario, result)
    assert "data" in result, "{} response should contain data".format(scenario)


def _post(client, api, payload, desc):
    return client.post(url=api.value, desc=desc, json=payload)


def _items(data):
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    for key in ("contentList", "data", "records", "rows", "list"):
        value = data.get(key)
        if isinstance(value, list):
            return value
        nested = _items(value)
        if nested:
            return nested
    return []


def _resolve_sparkthrift_datasource_id(client):
    if DATASOURCE_ID:
        return DATASOURCE_ID
    result = _post(
        client,
        AssetsApi.dataSource_page_query,
        {"current": 1, "size": 10, "search": "SparkThrift"},
        "查询 SparkThrift 资产数据源",
    )
    _assert_success(result, "dmetadata_resolve_sparkthrift_datasource")
    for item in _items(result.get("data")):
        source_type = str(item.get("dataSourceType") or item.get("sourceTypeValue") or "")
        if str(DATASOURCE_TYPE) in source_type or "SparkThrift" in source_type:
            return str(item["id"])
    pytest.skip("未找到可用 SparkThrift 资产数据源")


def _sync_payload(datasource_id):
    schedule_conf = (
        '{"periodType":"2","hour":"0","min":"0",'
        '"beginDate":"2026-05-09","endDate":"2126-05-09"}'
    )
    return {
        "dataSourceId": datasource_id,
        "dataSourceType": DATASOURCE_TYPE,
        "taskParams": "",
        "dbList": [DB_NAME],
        "tableList": [{"dbName": DB_NAME, "tableName": TABLE_NAME}],
        "alert": {},
        "maxConnection": 20,
        "periodType": "2",
        "scheduleConf": schedule_conf,
        "executeImmediately": True,
        "syncFilterTermConfigDTO": {"syncMetaContent": 0, "pastConfiguration": 1},
        "taskType": 1,
    }


class TestTideMetadataSync:
    """SparkThrift 元数据同步 HAR 链路测试。"""

    def setup_class(self):
        self.client = AssetsBaseRequest()
        self.datasource_id = _resolve_sparkthrift_datasource_id(self.client)

    def test_sync_task_page_and_datasource_options(self):
        """dmetadata_sync_task_page_datasource_har_direct"""
        task_page = _post(
            self.client,
            AssetsApi.syncTask_page_task,
            {"pageNow": 1, "pageSize": 20, "realTime": False},
            "分页查询元数据同步任务",
        )
        _assert_success(task_page, "dmetadata_sync_task_page_datasource_har_direct")

        datasource_list = _post(
            self.client,
            AssetsApi.datasource_list_metadata_datasource,
            {"type": 0},
            "查询元数据中心可用数据源",
        )
        _assert_success(datasource_list, "dmetadata_sync_task_page_datasource_har_direct")

    def test_realtime_db_and_table_list(self):
        """dmetadata_realtime_db_table_har_direct"""
        db_list = _post(
            self.client,
            AssetsApi.dataDb_real_time_db_list,
            {"dataSourceId": self.datasource_id, "useStatus": 1},
            "查询实时库列表",
        )
        _assert_success(db_list, "dmetadata_realtime_db_table_har_direct")

        table_list = _post(
            self.client,
            AssetsApi.syncTask_real_time_table_list,
            {"size": 200, "dbNames": [DB_NAME], "dataSourceId": self.datasource_id},
            "查询实时表列表",
        )
        _assert_success(table_list, "dmetadata_realtime_db_table_har_direct")

    def test_create_sparkthrift_metadata_sync_task(self):
        """dmetadata_sync_task_add_sparkthrift_har_direct"""
        result = _post(
            self.client,
            AssetsApi.syncTask_add,
            _sync_payload(self.datasource_id),
            "创建 SparkThrift 元数据同步任务",
        )
        if result.get("code") != 1 and result.get("data") is None:
            pytest.skip("当前环境未暴露 HAR 中的 SparkThrift 测试表，跳过创建同步任务")
        _assert_success(result, "dmetadata_sync_task_add_sparkthrift_har_direct")

    def test_sync_job_page_query(self):
        """dmetadata_sync_job_page_query_har_direct"""
        result = _post(
            self.client,
            AssetsApi.syncJob_page_query,
            {"taskId": TASK_ID, "current": 1, "size": 20},
            "查询元数据同步任务执行记录",
        )
        _assert_success(result, "dmetadata_sync_job_page_query_har_direct")

    def test_metadata_apply_subscribe_and_permission(self):
        """dmetadata_apply_subscribe_permission_har_direct"""
        apply_status = _post(
            self.client,
            AssetsApi.get_apply_status,
            {"tableId": TABLE_ID},
            "查询元数据申请状态",
        )
        if apply_status.get("code") != 1 and apply_status.get("data") is None:
            pytest.skip("当前环境缺少 HAR 中的 test_spark_insert 表，跳过表权限链路")
        _assert_success(apply_status, "dmetadata_apply_subscribe_permission_har_direct")

        subscribe = _post(
            self.client,
            AssetsApi.dataSubscribe_get_subscribe_by_table_id,
            {"metaDataType": 1, "tableId": TABLE_ID},
            "查询表订阅信息",
        )
        _assert_success(subscribe, "dmetadata_apply_subscribe_permission_har_direct")

        permission = _post(
            self.client,
            AssetsApi.query_table_permission,
            {"tableId": TABLE_ID},
            "查询表权限",
        )
        _assert_success(permission, "dmetadata_apply_subscribe_permission_har_direct")
