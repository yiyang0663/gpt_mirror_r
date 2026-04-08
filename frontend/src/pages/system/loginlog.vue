<template>
  <div class="ops-page">
    <admin-page-intro
      eyebrow="Audit"
      title="登录日志"
      description="查看最近的后台和用户登录行为，结合 IP、设备和时间定位异常访问。"
    />

    <admin-metric-grid :items="metricCards" />

    <t-card class="list-card-container">
      <div class="ops-surface__head">
        <div>
          <h3>访问记录</h3>
          <p>按时间回看用户名、来源 IP 和设备环境。</p>
        </div>
        <span class="ops-surface__badge">共 {{ pagination.total }} 条</span>
      </div>

      <div class="ops-filter-bar">
        <div class="ops-filter-grid">
          <t-input v-model="filters.search" clearable placeholder="搜索用户名、IP 或上游账号" style="width: 240px" />
          <t-select v-model="filters.log_type" clearable placeholder="操作类型" style="width: 160px">
            <t-option label="登录" value="login" />
            <t-option label="切换账号" value="choose-gpt" />
          </t-select>
          <span class="ops-filter-note">定位登录行为和前台切换上游账号的访问痕迹。</span>
        </div>

        <div class="ops-filter-actions">
          <t-button theme="primary" @click="handleSearch">查询</t-button>
          <t-button theme="default" variant="outline" @click="handleReset">重置</t-button>
        </div>
      </div>

      <t-table
        :data="tableData"
        :columns="columns"
        row-key="id"
        :loading="tableLoading"
        :pagination="pagination"
        @page-change="rehandlePageChange"
      >
        <template #created_at="{ row }">
          {{ TimestampToDate(row.created_at * 1000) }}
        </template>
        <template #chatgpt_username="{ row }">
          {{ row.chatgpt_username || '-' }}
        </template>
        <template #log_type="{ row }">
          <t-tag v-if="row.log_type === 'login'" theme="success" variant="light">登录</t-tag>
          <t-tag v-else-if="row.log_type === 'choose-gpt'" theme="warning" variant="light">切换账号</t-tag>
          <t-tag v-else variant="light">{{ formatLogType(row.log_type) }}</t-tag>
        </template>
        <template #user_agent="{ row }">
          {{ parseUserAgent(row.user_agent) }}
        </template>
      </t-table>
    </t-card>
  </div>
</template>

<script setup lang="ts">
// eslint-disable-next-line import/no-duplicates

import { AnalyticsIcon, DataDisplayIcon, TimeIcon, UsergroupIcon } from 'tdesign-icons-vue-next';
import { TableProps } from 'tdesign-vue-next';
import UAParser from 'ua-parser-js';
import { computed, onMounted, reactive, ref } from 'vue';

import RequestApi from '@/api/request';
import AdminMetricGrid from '@/components/admin/AdminMetricGrid.vue';
import AdminPageIntro from '@/components/admin/AdminPageIntro.vue';
import { TimestampToDate } from '@/utils/date';

interface TableData {
  id: number;
  username: string;
  chatgpt_username: string;
  ip: string;
  country: string;
  log_type: string;
  created_at: number;
  user_agent: string;
}
const filters = reactive({
  search: '',
  log_type: '',
});
const pagination = {
  defaultPageSize: 20,
  total: 0,
  defaultCurrent: 1,
};

const tableLoading = ref(false);
const tableData = ref<TableData[]>([]);
const columns: TableProps['columns'] = [
  { colKey: 'username', title: '用户名', width: 200 },
  { colKey: 'chatgpt_username', title: 'ChatGPT', width: 200 },
  { colKey: 'ip', title: 'IP', width: 200 },
  // { colKey: 'country', title: '国家/地区', width: 100 },
  { colKey: 'log_type', title: '操作类型', width: 200 },
  { colKey: 'created_at', title: '操作时间', width: 200 },
  { colKey: 'user_agent', title: '操作设备', width: 250 },
];
const VisitLogUri = '/0x/user/visit-log';

const metricCards = computed(() => {
  const loginCount = tableData.value.filter((item) => item.log_type === 'login').length;
  const chooseCount = tableData.value.filter((item) => item.log_type === 'choose-gpt').length;
  const uniqueIps = new Set(tableData.value.map((item) => item.ip).filter(Boolean)).size;
  return [
    {
      label: '日志总数',
      value: pagination.total,
      meta: '当前筛选条件下的记录总量',
      icon: AnalyticsIcon,
      color: '#1d4ed8',
    },
    {
      label: '当前页登录',
      value: loginCount,
      meta: `${chooseCount} 条切换账号记录`,
      icon: UsergroupIcon,
      color: '#0f766e',
    },
    {
      label: '当前页 IP',
      value: uniqueIps,
      meta: '本页涉及的访问来源',
      icon: DataDisplayIcon,
      color: '#7c3aed',
    },
    {
      label: '最新活动',
      value: tableData.value[0]?.created_at ? TimestampToDate(tableData.value[0].created_at * 1000) : '暂无',
      meta: '按时间倒序展示',
      icon: TimeIcon,
      color: '#c2410c',
    },
  ];
});

onMounted(async () => {
  await getVisitList();
});

const formatLogType = (logType: string) => {
  if (logType === 'login') return '登录';
  if (logType === 'choose-gpt') return '切换账号';
  return logType || '-';
};

const parseUserAgent = (userAgent: string) => {
  const parser = new UAParser();
  parser.setUA(userAgent || '');
  const u: any = parser.getResult();

  const browserName = u.browser?.name || 'Unknown';
  const osName = (u.os?.name || 'Unknown').replace(/\s+/g, '');
  const osVersion = u.os?.version || '';
  const deviceInfo = `${browserName} ${osName} ${osVersion}`.trim();

  return deviceInfo;
};

const rehandlePageChange = (curr: any) => {
  pagination.defaultCurrent = curr.current;
  pagination.defaultPageSize = curr.pageSize;
  getVisitList();
};

const buildQueryString = () => {
  const params: Record<string, any> = {
    page: pagination.defaultCurrent,
    page_size: pagination.defaultPageSize,
  };
  if (filters.search) params.search = filters.search;
  if (filters.log_type) params.log_type = filters.log_type;
  return new URLSearchParams(params).toString();
};

const getVisitList = async () => {
  tableLoading.value = true;
  const queryString = buildQueryString();
  const response = await RequestApi(`${VisitLogUri}?${queryString}`);

  const data = await response.json();
  pagination.total = data.count;
  tableData.value = data.results;
  tableLoading.value = false;
};

const handleSearch = async () => {
  pagination.defaultCurrent = 1;
  await getVisitList();
};

const handleReset = async () => {
  filters.search = '';
  filters.log_type = '';
  pagination.defaultCurrent = 1;
  await getVisitList();
};
</script>
<style scoped lang="less">
.ops-page {
  display: flex;
  flex-direction: column;
}
</style>
