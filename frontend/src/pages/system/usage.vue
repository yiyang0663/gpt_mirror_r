<template>
  <div class="usage-page">
    <t-row :gutter="[16, 16]">
      <t-col v-for="item in summaryCards" :key="item.label" :xs="12" :sm="6" :lg="3">
        <t-card class="summary-card">
          <p class="summary-label">{{ item.label }}</p>
          <p class="summary-value">{{ item.value }}</p>
        </t-card>
      </t-col>
    </t-row>

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
import { TableProps } from 'tdesign-vue-next';
import { computed, onMounted, ref } from 'vue';

import RequestApi from '@/api/request';
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

const summaryCards = computed(() => [
  { label: '总请求数', value: summary.value.total_requests },
  { label: '成功请求', value: summary.value.success_requests },
  { label: '失败请求', value: summary.value.failed_requests },
  { label: '总 Tokens', value: summary.value.total_tokens },
  { label: '输入 Tokens', value: summary.value.prompt_tokens },
  { label: '输出 Tokens', value: summary.value.completion_tokens },
  { label: '活跃用户', value: summary.value.unique_users },
  { label: '活跃账号', value: summary.value.unique_accounts },
]);

const rehandlePageChange = (curr: any) => {
  pagination.defaultCurrent = curr.current;
  pagination.defaultPageSize = curr.pageSize;
  getUsageDetail();
};

const getUsageSummary = async () => {
  const response = await RequestApi(UsageSummaryUri);
  const data = await response.json();
  summary.value = data;
};

const getUsageDetail = async () => {
  tableLoading.value = true;
  const params: any = {
    page: pagination.defaultCurrent,
    page_size: pagination.defaultPageSize,
  };

  const queryString = new URLSearchParams(params).toString();
  const response = await RequestApi(`${UsageDetailUri}?${queryString}`);
  const data = await response.json();
  pagination.total = data.count;
  tableData.value = data.results;
  tableLoading.value = false;
};

onMounted(async () => {
  await getUsageSummary();
  await getUsageDetail();
});
</script>

<style scoped lang="less">
.usage-page {
  display: flex;
  flex-direction: column;
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
