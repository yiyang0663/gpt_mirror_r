<template>
  <div class="ops-page usage-page">
    <admin-page-intro
      eyebrow="Observability"
      title="用量账本"
      description="从请求数、模型消耗、活跃用户和上游账号四个维度查看当前站点的实际消耗。"
    />

    <t-card class="toolbar-card">
      <div class="ops-surface__head">
        <div>
          <h3>账本筛选</h3>
          <p>按用户、上游账号、模型、状态码和日期窗口定位消耗异常。</p>
        </div>
        <span class="ops-surface__badge">概览、排行和明细会跟随当前筛选</span>
      </div>

      <div class="ops-filter-bar" style="margin-bottom: 0">
        <div class="ops-filter-grid">
          <t-input v-model="filters.username" clearable placeholder="筛选用户名" style="width: 180px" />
          <t-input v-model="filters.chatgpt_username" clearable placeholder="筛选上游账号" style="width: 200px" />
          <t-input v-model="filters.model_name" clearable placeholder="筛选模型" style="width: 180px" />
          <t-input v-model="filters.status_code" clearable placeholder="状态码，例如 200 / 429" style="width: 170px" />
          <t-date-picker v-model="filters.date_from" clearable format="YYYY-MM-DD" placeholder="开始日期" />
          <t-date-picker v-model="filters.date_to" clearable format="YYYY-MM-DD" placeholder="结束日期" />
        </div>

        <div class="ops-filter-actions">
          <t-button theme="primary" @click="handleSearch">查询</t-button>
          <t-button theme="default" variant="outline" @click="handleReset">重置</t-button>
        </div>
      </div>
    </t-card>

    <admin-metric-grid :items="metricCards" />

    <t-row :gutter="[16, 16]" style="margin-top: 16px">
      <t-col :xs="12" :lg="4">
        <t-card title="热门模型">
          <div v-if="summary.top_models.length" class="rank-list">
            <div v-for="item in summary.top_models" :key="item.model_name" class="rank-item">
              <span>{{ item.model_name }}</span>
              <span>{{ item.request_count }} 次 / {{ item.total_tokens }} tokens</span>
            </div>
          </div>
          <div v-else class="empty-copy">暂无数据</div>
        </t-card>
      </t-col>

      <t-col :xs="12" :lg="4">
        <t-card title="高频用户">
          <div v-if="summary.top_users.length" class="rank-list">
            <div v-for="item in summary.top_users" :key="item.user__username" class="rank-item">
              <span>{{ item.user__username }}</span>
              <span>{{ item.request_count }} 次 / {{ item.total_tokens }} tokens</span>
            </div>
          </div>
          <div v-else class="empty-copy">暂无数据</div>
        </t-card>
      </t-col>

      <t-col :xs="12" :lg="4">
        <t-card title="高频账号">
          <div v-if="summary.top_accounts.length" class="rank-list">
            <div v-for="item in summary.top_accounts" :key="item.account__chatgpt_username" class="rank-item">
              <span>{{ item.account__chatgpt_username }}</span>
              <span>{{ item.request_count }} 次 / {{ item.total_tokens }} tokens</span>
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
        <template #status_code="{ row }">
          <t-tag v-if="row.status_code >= 200 && row.status_code < 400" theme="success" variant="light">
            {{ row.status_code }}
          </t-tag>
          <t-tag v-else theme="danger" variant="light">{{ row.status_code || '-' }}</t-tag>
        </template>

        <template #created_at="{ row }">
          {{ TimestampToDate(row.created_at * 1000) }}
        </template>
      </t-table>
    </t-card>
  </div>
</template>

<script setup lang="ts">
import { ChartIcon, DataDisplayIcon, MoneyIcon, UsergroupIcon } from 'tdesign-icons-vue-next';
import { TableProps } from 'tdesign-vue-next';
import { computed, onMounted, reactive, ref } from 'vue';

import RequestApi from '@/api/request';
import AdminMetricGrid from '@/components/admin/AdminMetricGrid.vue';
import AdminPageIntro from '@/components/admin/AdminPageIntro.vue';
import { TimestampToDate } from '@/utils/date';

interface SummaryLine {
  request_count: number;
  total_tokens: number;
  model_name?: string;
  user__username?: string;
  account__chatgpt_username?: string;
}

interface UsageSummary {
  total_requests: number;
  success_requests: number;
  failed_requests: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  estimated_cost: number;
  unique_users: number;
  unique_accounts: number;
  top_models: SummaryLine[];
  top_users: SummaryLine[];
  top_accounts: SummaryLine[];
}

interface TableData {
  username: string;
  chatgpt_username: string;
  model_name: string;
  request_type: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  estimated_cost: number;
  status_code: number;
  error_code: string;
  created_at: number;
}

const UsageSummaryUri = '/0x/system/usage-summary';
const UsageDetailUri = '/0x/system/usage-detail';

const summary = ref<UsageSummary>({
  total_requests: 0,
  success_requests: 0,
  failed_requests: 0,
  prompt_tokens: 0,
  completion_tokens: 0,
  total_tokens: 0,
  estimated_cost: 0,
  unique_users: 0,
  unique_accounts: 0,
  top_models: [],
  top_users: [],
  top_accounts: [],
});

const filters = reactive({
  username: '',
  chatgpt_username: '',
  model_name: '',
  status_code: '',
  date_from: '',
  date_to: '',
});
const tableLoading = ref(false);
const tableData = ref<TableData[]>([]);

const pagination = {
  defaultPageSize: 20,
  total: 0,
  defaultCurrent: 1,
};

const columns: TableProps['columns'] = [
  { colKey: 'username', title: '用户', width: 120 },
  { colKey: 'chatgpt_username', title: '上游账号', width: 180 },
  { colKey: 'model_name', title: '模型', width: 140 },
  { colKey: 'request_type', title: '请求类型', width: 120 },
  { colKey: 'prompt_tokens', title: '输入', width: 80 },
  { colKey: 'completion_tokens', title: '输出', width: 80 },
  { colKey: 'total_tokens', title: '总量', width: 90 },
  { colKey: 'estimated_cost', title: '成本', width: 90 },
  { colKey: 'status_code', title: '状态码', width: 100 },
  { colKey: 'error_code', title: '错误码', width: 120 },
  { colKey: 'created_at', title: '时间', width: 180 },
];

const metricCards = computed(() => [
  {
    label: '总请求数',
    value: summary.value.total_requests,
    meta: `${summary.value.success_requests} 成功 / ${summary.value.failed_requests} 失败`,
    icon: ChartIcon,
    color: '#1d4ed8',
  },
  {
    label: '总 Tokens',
    value: summary.value.total_tokens,
    meta: `${summary.value.prompt_tokens} 输入 / ${summary.value.completion_tokens} 输出`,
    icon: DataDisplayIcon,
    color: '#7c3aed',
  },
  {
    label: '预估成本',
    value: `$${Number(summary.value.estimated_cost || 0).toFixed(4)}`,
    meta: '按账本累计预估',
    icon: MoneyIcon,
    color: '#c2410c',
  },
  {
    label: '活跃用户',
    value: summary.value.unique_users,
    meta: `${summary.value.unique_accounts} 个活跃上游账号`,
    icon: UsergroupIcon,
    color: '#0f766e',
  },
]);

const rehandlePageChange = (curr: any) => {
  pagination.defaultCurrent = curr.current;
  pagination.defaultPageSize = curr.pageSize;
  getUsageDetail();
};

const buildQueryString = (includePagination = true) => {
  const params: Record<string, any> = {};
  if (includePagination) {
    params.page = pagination.defaultCurrent;
    params.page_size = pagination.defaultPageSize;
  }
  if (filters.username) params.username = filters.username;
  if (filters.chatgpt_username) params.chatgpt_username = filters.chatgpt_username;
  if (filters.model_name) params.model_name = filters.model_name;
  if (filters.status_code) params.status_code = filters.status_code;
  if (filters.date_from) params.date_from = filters.date_from;
  if (filters.date_to) params.date_to = filters.date_to;
  return new URLSearchParams(params).toString();
};

const getUsageSummary = async () => {
  const queryString = buildQueryString(false);
  const response = await RequestApi(queryString ? `${UsageSummaryUri}?${queryString}` : UsageSummaryUri);
  const data = await response.json();
  summary.value = data;
};

const getUsageDetail = async () => {
  tableLoading.value = true;
  const queryString = buildQueryString();
  const response = await RequestApi(`${UsageDetailUri}?${queryString}`);
  const data = await response.json();
  pagination.total = data.count;
  tableData.value = data.results;
  tableLoading.value = false;
};

const handleSearch = async () => {
  pagination.defaultCurrent = 1;
  await Promise.all([getUsageSummary(), getUsageDetail()]);
};

const handleReset = async () => {
  filters.username = '';
  filters.chatgpt_username = '';
  filters.model_name = '';
  filters.status_code = '';
  filters.date_from = '';
  filters.date_to = '';
  pagination.defaultCurrent = 1;
  await Promise.all([getUsageSummary(), getUsageDetail()]);
};

onMounted(async () => {
  await Promise.all([getUsageSummary(), getUsageDetail()]);
});
</script>

<style scoped lang="less">
.usage-page {
  display: flex;
  flex-direction: column;
}

.toolbar-card {
  overflow: visible;
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
