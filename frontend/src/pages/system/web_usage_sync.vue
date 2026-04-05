<template>
  <div class="web-usage-sync-page">
    <t-card class="toolbar-card">
      <t-row justify="space-between" align="middle" :gutter="[12, 12]">
        <t-space wrap>
          <t-button :loading="syncLoading" @click="handleSync">手动同步</t-button>
          <t-input v-model="filters.username" clearable placeholder="筛选用户名" style="width: 180px" />
          <t-select v-model="filters.sync_status" clearable placeholder="同步状态" style="width: 160px">
            <t-option label="已同步" value="synced" />
            <t-option label="未同步/滞后" value="stale" />
          </t-select>
          <t-button theme="default" variant="outline" @click="handleSearch">查询</t-button>
          <t-button theme="default" variant="text" @click="handleReset">重置</t-button>
        </t-space>

        <div class="sync-meta">
          <p>统计日期：{{ summary.today || '-' }}</p>
          <p>最近同步：{{ summary.latest_sync_at ? TimestampToDate(summary.latest_sync_at * 1000) : '暂无' }}</p>
        </div>
      </t-row>
    </t-card>

    <t-row :gutter="[16, 16]" style="margin-top: 16px">
      <t-col v-for="item in summaryCards" :key="item.label" :xs="12" :sm="6" :lg="3">
        <t-card class="summary-card">
          <p class="summary-label">{{ item.label }}</p>
          <p class="summary-value">{{ item.value }}</p>
        </t-card>
      </t-col>
    </t-row>

    <t-row :gutter="[16, 16]" style="margin-top: 16px">
      <t-col :xs="12" :lg="6">
        <t-card title="今日网页请求 Top 用户">
          <div v-if="summary.top_users_today.length" class="rank-list">
            <div v-for="item in summary.top_users_today" :key="item.user__username" class="rank-item">
              <span>{{ item.user__username }}</span>
              <span>{{ item.request_count }} 次</span>
            </div>
          </div>
          <div v-else class="empty-copy">暂无数据</div>
        </t-card>
      </t-col>

      <t-col :xs="12" :lg="6">
        <t-card title="本月网页请求 Top 用户">
          <div v-if="summary.top_users_month.length" class="rank-list">
            <div v-for="item in summary.top_users_month" :key="item.user__username" class="rank-item">
              <span>{{ item.user__username }}</span>
              <span>{{ item.request_count }} 次</span>
            </div>
          </div>
          <div v-else class="empty-copy">暂无数据</div>
        </t-card>
      </t-col>
    </t-row>

    <t-card class="list-card-container" style="margin-top: 16px">
      <t-table
        :data="tableData"
        :columns="columns"
        row-key="id"
        :loading="tableLoading"
        bordered
        hover
        :pagination="pagination"
        @page-change="rehandlePageChange"
      >
        <template #pool_mode="{ row }">
          {{ row.pool_mode === 'specific_pools' ? '指定号池' : '公共账号池' }}
        </template>

        <template #sync_status="{ row }">
          <t-tag v-if="row.sync_status === 'synced'" theme="success" variant="light">已同步</t-tag>
          <t-tag v-else-if="row.sync_status === 'stale'" theme="warning" variant="light">滞后</t-tag>
          <t-tag v-else theme="default" variant="light">待同步</t-tag>
        </template>

        <template #today_synced_at="{ row }">
          {{ row.today_synced_at ? TimestampToDate(row.today_synced_at * 1000) : '-' }}
        </template>

        <template #last_synced_at="{ row }">
          {{ row.last_synced_at ? TimestampToDate(row.last_synced_at * 1000) : '-' }}
        </template>
      </t-table>
    </t-card>
  </div>
</template>

<script setup lang="ts">
import { MessagePlugin, TableProps } from 'tdesign-vue-next';
import { computed, onMounted, reactive, ref } from 'vue';

import RequestApi from '@/api/request';
import { TimestampToDate } from '@/utils/date';

interface RankLine {
  user__username: string;
  request_count: number;
}

interface SummaryData {
  today: string;
  month_start: string;
  active_user_count: number;
  synced_user_count: number;
  stale_user_count: number;
  sync_ratio: number;
  latest_sync_at: number;
  today_total_requests: number;
  month_total_requests: number;
  month_snapshot_rows: number;
  month_snapshot_days: number;
  top_users_today: RankLine[];
  top_users_month: RankLine[];
}

interface TableRow {
  id: number;
  username: string;
  email: string;
  status: string;
  plan_name: string;
  pool_mode: string;
  today_request_count: number;
  month_request_count: number;
  snapshot_days: number;
  today_synced_at: number;
  last_snapshot_date: string;
  last_synced_at: number;
  sync_status: string;
}

const SummaryUri = '/0x/system/web-usage-sync-summary';
const DetailUri = '/0x/system/web-usage-sync-detail';
const SyncUri = '/0x/system/web-usage-sync';

const summary = ref<SummaryData>({
  today: '',
  month_start: '',
  active_user_count: 0,
  synced_user_count: 0,
  stale_user_count: 0,
  sync_ratio: 0,
  latest_sync_at: 0,
  today_total_requests: 0,
  month_total_requests: 0,
  month_snapshot_rows: 0,
  month_snapshot_days: 0,
  top_users_today: [],
  top_users_month: [],
});
const filters = reactive({
  username: '',
  sync_status: '',
});
const syncLoading = ref(false);
const tableLoading = ref(false);
const tableData = ref<TableRow[]>([]);

const pagination = {
  defaultPageSize: 20,
  total: 0,
  defaultCurrent: 1,
};

const columns: TableProps['columns'] = [
  { colKey: 'username', title: '用户名', width: 140, fixed: 'left' },
  { colKey: 'email', title: '邮箱', width: 220 },
  { colKey: 'plan_name', title: '套餐', width: 140 },
  { colKey: 'pool_mode', title: '账号池', width: 120 },
  { colKey: 'today_request_count', title: '今日网页请求', width: 120 },
  { colKey: 'month_request_count', title: '本月网页请求', width: 120 },
  { colKey: 'snapshot_days', title: '本月快照天数', width: 120 },
  { colKey: 'sync_status', title: '同步状态', width: 120 },
  { colKey: 'today_synced_at', title: '今日同步时间', width: 170 },
  { colKey: 'last_snapshot_date', title: '最后快照日期', width: 120 },
  { colKey: 'last_synced_at', title: '最后同步时间', width: 170 },
];

const summaryCards = computed(() => [
  { label: '活跃用户', value: summary.value.active_user_count },
  { label: '今日已同步', value: summary.value.synced_user_count },
  { label: '今日滞后', value: summary.value.stale_user_count },
  { label: '同步覆盖率', value: `${summary.value.sync_ratio}%` },
  { label: '今日网页请求', value: summary.value.today_total_requests },
  { label: '本月网页请求', value: summary.value.month_total_requests },
  { label: '本月快照行数', value: summary.value.month_snapshot_rows },
  { label: '本月快照天数', value: summary.value.month_snapshot_days },
]);

const buildQueryString = () => {
  const params: Record<string, any> = {
    page: pagination.defaultCurrent,
    page_size: pagination.defaultPageSize,
  };
  if (filters.username) params.username = filters.username;
  if (filters.sync_status) params.sync_status = filters.sync_status;
  return new URLSearchParams(params).toString();
};

const getSummary = async () => {
  const response = await RequestApi(SummaryUri);
  if (!response.ok) return;
  summary.value = await response.json();
};

const getDetail = async () => {
  tableLoading.value = true;
  const response = await RequestApi(`${DetailUri}?${buildQueryString()}`);
  if (response.ok) {
    const data = await response.json();
    tableData.value = data.results;
    pagination.total = data.count;
  }
  tableLoading.value = false;
};

const handleSync = async () => {
  syncLoading.value = true;
  const response = await RequestApi(SyncUri, 'POST');
  if (response.ok) {
    const data = await response.json();
    MessagePlugin.success(`同步完成：${data.synced_user_count}/${data.active_user_count}`);
    await Promise.all([getSummary(), getDetail()]);
  }
  syncLoading.value = false;
};

const handleSearch = async () => {
  pagination.defaultCurrent = 1;
  await getDetail();
};

const handleReset = async () => {
  filters.username = '';
  filters.sync_status = '';
  pagination.defaultCurrent = 1;
  await getDetail();
};

const rehandlePageChange = (curr: any) => {
  pagination.defaultCurrent = curr.current;
  pagination.defaultPageSize = curr.pageSize;
  getDetail();
};

onMounted(async () => {
  await Promise.all([getSummary(), getDetail()]);
});
</script>

<style scoped lang="less">
.web-usage-sync-page {
  display: flex;
  flex-direction: column;
}

.toolbar-card {
  overflow: visible;
}

.sync-meta {
  text-align: right;
  color: #666;
  font-size: 13px;
  line-height: 1.7;
}

.sync-meta p {
  margin: 0;
}

.summary-card {
  min-height: 118px;
}

.summary-label {
  margin: 0 0 10px;
  color: #666;
  font-size: 13px;
}

.summary-value {
  margin: 0;
  color: #111;
  font-size: 28px;
  font-weight: 700;
  line-height: 1.15;
}

.rank-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.rank-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: #333;
  font-size: 13px;
  line-height: 1.5;
}

.empty-copy {
  color: #888;
  font-size: 13px;
}
</style>
